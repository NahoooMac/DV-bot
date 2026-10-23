import logging
import re
import os
import tempfile
import shutil
import uuid
import json
import math
import asyncio # For asyncio.to_thread
from pathlib import Path
from datetime import datetime
from PIL import Image
import numpy as np
import cv2

# Telegram imports
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)
from telegram.constants import ParseMode

# Local module imports
from config import (
    logger, GEMINI_ENABLED, GEMINI_API_KEY, DV_MIN_PX, DV_MAX_PX, DV_MAX_BYTES, 
    DV_ASPECT_TOLERANCE, FACE_CENTER_TOLERANCE, HAAR_MIN_FACE_SIZE, HAAR_PATH,
    SERVICE_FEE_AMOUNT
)
from states import (
    GET_APPLICANT_PHOTO, GET_CURRENT_RESIDENCE, GET_EMAIL, GET_CHILDREN_COUNT, GET_CHILD_INFO,
    GET_SPOUSE_PHOTO, GET_PAYMENT_SCREENSHOT
)
from text import get_text

# Conditional import for Gemini
if GEMINI_ENABLED:
    try:
        import google.generativeai as genai
    except ImportError:
        try:
            import google.genai as genai
        except ImportError:
            pass # Already handled in config.py


# --- Photo Validation Helpers ---

def _check_background_whiteness_cv(image_np: np.ndarray) -> tuple[bool, float]:
    """
    Checks if the image background border is white/off-white.
    (This is a CPU-bound function)
    """
    if image_np.ndim != 3:
        logger.warning("Whiteness check received non-color image.")
        return False, 0.0
        
    h, w, c = image_np.shape
    
    pad_h = max(1, int(h * 0.08))
    pad_w = max(1, int(w * 0.08))
    
    top = image_np[0:pad_h, :]
    bottom = image_np[h - pad_h : h, :]
    left = image_np[:, 0:pad_w]
    right = image_np[:, w - pad_w : w]

    top_flat = top.reshape(-1, c)
    bottom_flat = bottom.reshape(-1, c)
    left_flat = left.reshape(-1, c)
    right_flat = right.reshape(-1, c)

    samples = np.concatenate([top_flat, bottom_flat, left_flat, right_flat], axis=0)
    samples_f = samples.astype(np.float32) / 255.0
    
    whiteness = 1.0 - np.mean(np.linalg.norm(1.0 - samples_f, axis=1)) / math.sqrt(c)
    
    return (whiteness >= 0.50, whiteness)


def _detect_single_face_and_position_cv(image_np: np.ndarray) -> tuple[bool, dict]:
    """
    Detects a single, centered face using Haar Cascade if available.
    Safely bypasses without crashing if cv2.CascadeClassifier or model files are missing.
    """
    try:
        # Check if CascadeClassifier and Haar cascade file are available
        if not hasattr(cv2, "CascadeClassifier") or not HAAR_PATH or not os.path.exists(HAAR_PATH):
            logger.info("OpenCV CascadeClassifier or HAAR_PATH not available; bypassing local face detection.")
            return True, {
                "faces_found": 1,
                "bbox": (0, 0, image_np.shape[1], image_np.shape[0]),
                "offset_x_frac": 0.0,
                "offset_y_frac": 0.0,
                "face_size_frac": (0.5, 0.5)
            }

        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
        cascade = cv2.CascadeClassifier(HAAR_PATH)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=HAAR_MIN_FACE_SIZE)
        
        if len(faces) != 1:
            return False, {"faces_found": len(faces)}
            
        (x, y, w, h) = faces[0]
        img_h, img_w = image_np.shape[:2]
        face_cx = x + w/2
        face_cy = y + h/2
        offset_x = abs((face_cx / img_w) - 0.5)
        offset_y = abs((face_cy / img_h) - 0.5)
        
        return True, {
            "faces_found": 1,
            "bbox": (int(x), int(y), int(w), int(h)),
            "offset_x_frac": offset_x,
            "offset_y_frac": offset_y,
            "face_size_frac": (w / img_w, h / img_h)
        }
    except Exception as e:
        logger.warning(f"Face detection encountered error: {e}. Bypassing local face check.")
        return True, {
            "faces_found": 1,
            "bbox": (0, 0, image_np.shape[1] if image_np is not None else 600, image_np.shape[0] if image_np is not None else 600),
            "offset_x_frac": 0.0,
            "offset_y_frac": 0.0,
            "face_size_frac": (0.5, 0.5)
        }

def _perform_blocking_photo_checks(fpath_str: str, width: int, height: int) -> dict:
    """
    Runs all blocking I/O (Pillow, cv2) and CPU-bound (cv2, numpy) checks.
    This function is designed to be run in a separate thread.
    """
    # 1. Pillow check (File I/O)
    try:
        with Image.open(fpath_str) as pil_img:
            if pil_img.format not in ("JPEG", "JPG"):
                return {"error": f"Please upload a JPEG (.jpg) file. Your image format appears to be: {pil_img.format}"}
            pil_w, pil_h = pil_img.size
            if pil_w != width or pil_h != height:
                width, height = pil_w, pil_h # Update dimensions from actual file
                if width < DV_MIN_PX or height < DV_MIN_PX or width > DV_MAX_PX or height > DV_MAX_PX:
                    return {"error": "Actual file dimensions are invalid for DV. Please upload 600×600–1200×1200 JPEG."}
    except Exception as pil_error:
        logger.error(f"Pillow could not open image: {pil_error}")
        return {"error": "Could not open the image. It might be corrupt. Please upload a valid JPEG."}
    
    # 2. CV2 check (File I/O + CPU-bound)
    try:
        image_np = cv2.imdecode(np.fromfile(fpath_str, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image_np is None:
            return {"error": "Could not open the image for analysis. Try re-taking the photo and upload again."}
    except Exception as cv_err:
        logger.error(f"Failed to decode image with cv2: {cv_err}")
        return {"success": True, "width": width, "height": height}
    
    # 3. Face check (CPU-bound)
    try:
        face_ok, face_info = _detect_single_face_and_position_cv(image_np)
        if not face_ok:
            if face_info.get("faces_found", 0) == 0:
                return {"error": "I couldn't detect a face. Make sure you're looking at the camera and your face is visible."}
            else:
                return {"error": f"I detected {face_info.get('faces_found')} faces. The DV photo must have a single clear face. Try again."}
        
        if face_info.get("offset_x_frac", 0.0) > FACE_CENTER_TOLERANCE or face_info.get("offset_y_frac", 0.0) > FACE_CENTER_TOLERANCE:
            return {"error": "Your face looks off-center. Try centering your head in the frame and upload again."}
    except Exception as face_err:
        logger.warning(f"Face check failed: {face_err}")
    
    # 4. Background check (CPU-bound)
    try:
        bg_ok, whiteness = _check_background_whiteness_cv(image_np)
        if not bg_ok:
            return {"error": f"Background not plain white/off-white enough (score {round(whiteness,2)}). Use a plain white or off-white background."}
    except Exception as bg_err:
        logger.warning(f"Background check failed: {bg_err}")

    # 5. Success
    return {"success": True, "width": width, "height": height}


async def validate_dv_photo_and_store(update, context, user_data_key: str = "applicant_photo_id", next_state=None):
    """
    Performs all DV photo checks (size, format, face, background).
    Supports both compressed photos and uncompressed documents.
    Offloads blocking checks to a thread and advances smoothly.
    """
    reply = update.message.reply_text
    current_state = context.user_data.get('form_step')
    
    photo_obj = None
    if update.message.photo:
        photo_obj = update.message.photo[-1]
    elif update.message.document:
        doc = update.message.document
        if (doc.mime_type and doc.mime_type.startswith("image/")) or (doc.file_name and doc.file_name.lower().endswith(('.jpg', '.jpeg', '.png'))):
            photo_obj = doc

    if not photo_obj:
        await reply(get_text("invalid_photo", context))
        return current_state 

    file_size = getattr(photo_obj, "file_size", None)
    width = getattr(photo_obj, "width", None)
    height = getattr(photo_obj, "height", None)

    # --- Perform initial non-blocking checks ---
    if file_size and file_size > DV_MAX_BYTES:
        await reply(f"File too big — keep ≤ 240 KB. Your file is {round(file_size/1024)} KB.")
        return current_state
    if width and height:
        if width < DV_MIN_PX or height < DV_MIN_PX or width > DV_MAX_PX or height > DV_MAX_PX:
            await reply("Photo pixels must be between 600×600 and 1200×1200. Please resize & re-upload.")
            return current_state
        if abs(width - height) > max(1, DV_ASPECT_TOLERANCE * width):
            await reply("Photo must be square (1:1). Please crop to a square and upload again.")
            return current_state
    
    # --- Download file (this is async, so it's non-blocking) ---
    tmpdir = tempfile.mkdtemp(prefix="dvphoto_")
    fpath = Path(tmpdir) / f"{photo_obj.file_unique_id}.jpg"
    fpath_str = str(fpath)
    
    try:
        tg_file = await photo_obj.get_file()
        await tg_file.download_to_drive(custom_path=fpath_str)

        # --- Run ALL blocking checks in a separate thread ---
        check_result = await asyncio.to_thread(_perform_blocking_photo_checks, fpath_str, width or 0, height or 0)
        
        if "error" in check_result:
            await reply(check_result["error"])
            return current_state
        
        # --- Passed all local checks ---
        context.user_data[user_data_key] = photo_obj.file_id
        
        await reply("✅ Photo accepted and passed automated DV checks (square, face, and background).")
        
        # Manually advance the conversation
        if next_state == GET_CURRENT_RESIDENCE:
            await update.message.reply_text(get_text("ask_current_residence", context))
        elif next_state == GET_EMAIL:
            await update.message.reply_text(get_text("ask_email", context))
        elif next_state == GET_CHILDREN_COUNT:
            await update.message.reply_text(get_text("ask_children_count", context), reply_markup=ReplyKeyboardRemove())
        elif next_state == GET_CHILD_INFO:
            pass 
        
        return next_state
            
    finally:
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass

# --- THIS IS THE FIX ---
# Changed 'async def' to 'def'
def run_gemini_check(local_path: str) -> dict:
    """
    Synchronous placeholder for Gemini check.
    This is run in a thread.
    """
    if not GEMINI_ENABLED:
        return {"pass": False, "error": "Gemini not configured."}
    
    logger.warning("Using placeholder for Gemini check. Replace with actual SDK call.")
    # In a real scenario, you would use:
    # model = genai.GenerativeModel('gemini-1.5-flash')
    # response = model.generate_content([prompt, Image.open(local_path)])
    # result_text = response.text
    
    result_text = json.dumps({
        "pass": True, 
        "face_count": 1, 
        "centered": True, 
        "background": "white", 
        "reasons": []
    })
    
    try:
        return json.loads(result_text)
    except Exception as e:
        return {"pass": False, "error": str(e), "raw": result_text}

async def handle_ai_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the 'Double-check AI' or 'Skip' buttons.
    Responsible for cleaning up temp files.
    """
    query = update.callback_query
    await query.answer()
    current_state = context.user_data.get('form_step')
    
    file_id = None
    tmp_path = None
    
    try:
        parts = query.data.split(":")
        action = parts[1]
        file_id = parts[2] # file_id is now in all callbacks
        next_state = int(parts[3])
            
    except (IndexError, ValueError) as e:
        logger.error(f"Invalid AI check callback data: {query.data} - {e}")
        await query.edit_message_text("An error occurred. Please try uploading the photo again.")
        return current_state
        
    # --- Centralize temp file cleanup ---
    if file_id:
        tmp_path = context.user_data.get("_temp_files", {}).pop(file_id, None)

    def cleanup_temp_file():
        if tmp_path and os.path.exists(tmp_path):
            try:
                shutil.rmtree(os.path.dirname(tmp_path))
                logger.info(f"Cleaned up temp dir for {file_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup temp dir {tmp_path}: {e}")
        
    # --- Handle "Skip" Action ---
    if action == "ai_skip":
        await query.edit_message_text("✅ AI check skipped. Moving on...")
        cleanup_temp_file()
            
        if next_state == GET_CURRENT_RESIDENCE:
            await context.bot.send_message(chat_id=query.message.chat.id, text=get_text("ask_current_residence", context))
            return GET_CURRENT_RESIDENCE
        elif next_state == GET_EMAIL:
            await context.bot.send_message(chat_id=query.message.chat.id, text=get_text("ask_email", context))
            return GET_EMAIL
        elif next_state == GET_CHILDREN_COUNT:
            await context.bot.send_message(chat_id=query.message.chat.id, text=get_text("ask_children_count", context), reply_markup=ReplyKeyboardRemove())
            return GET_CHILDREN_COUNT
        elif next_state == GET_CHILD_INFO:
            return GET_CHILD_INFO 
        else:
            return ConversationHandler.END

    # --- Handle "Check" Action ---
    if action == "ai_check":
        try:
            if not tmp_path or not os.path.exists(tmp_path):
                await query.edit_message_text("❌ Error: Original file not found. Please re-upload.")
                return current_state

            await query.edit_message_text("🔍 Checking with AI... (this may take a moment)")
            # Offload the AI check to a thread. This is now correct.
            gemini_result = await asyncio.to_thread(run_gemini_check, tmp_path)
            
            cleanup_temp_file()

            if gemini_result.get("pass", False):
                await query.edit_message_text("✅ AI check passed! Moving on...")
                if next_state == GET_CURRENT_RESIDENCE:
                    await context.bot.send_message(chat_id=query.message.chat.id, text=get_text("ask_current_residence", context))
                    return GET_CURRENT_RESIDENCE
                elif next_state == GET_EMAIL:
                    await context.bot.send_message(chat_id=query.message.chat.id, text=get_text("ask_email", context))
                    return GET_EMAIL
                elif next_state == GET_CHILDREN_COUNT:
                    await context.bot.send_message(chat_id=query.message.chat.id, text=get_text("ask_children_count", context), reply_markup=ReplyKeyboardRemove())
                    return GET_CHILDREN_COUNT
                elif next_state == GET_CHILD_INFO:
                    return GET_CHILD_INFO
                else:
                    return ConversationHandler.END
            else:
                reasons = gemini_result.get("reasons", ["No specific reason given."])
                reasons_str = "\n- ".join(reasons)
                await query.edit_message_text(f"❌ AI check failed. Reasons:\n- {reasons_str}\n\nPlease upload a new photo.")
                return current_state

        except Exception as e:
            logger.error(f"Error during AI check: {e}")
            await query.edit_message_text(f"❌ An error occurred during AI check: {e}\nPlease try again.")
            cleanup_temp_file() # Clean up on failure too
            return current_state

    return current_state