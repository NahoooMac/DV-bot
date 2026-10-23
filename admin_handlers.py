import logging
import re
import os
import uuid
import json
import psycopg2 
import asyncio 
from datetime import datetime
from typing import List, Dict, Any, Optional

# Telegram imports
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import (
    ContextTypes,
)
from telegram.constants import ParseMode

# Local module imports
from config import (
    logger, ADMIN_CHAT_ID, ADMIN_USERNAMES, 
    DATABASE_URL, DATABASE_URL_UNPOOLED,
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
)
from text import get_text, format_summary

def get_db_connection(unpooled: bool = False):
    """
    Establishes a connection to the PostgreSQL database.
    Supports Neon DATABASE_URL (pooled for app queries, direct/unpooled for migrations/DDL)
    or standard PG host/port/db credentials.
    """
    target_url = DATABASE_URL_UNPOOLED if unpooled else DATABASE_URL
    if target_url:
        return psycopg2.connect(target_url)
    if DB_HOST:
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
    raise ConnectionError("No database configuration found. Please set DATABASE_URL or DB_* variables in .env.")

def init_db():
    """
    Initializes the PostgreSQL database.
    Creates both the 'submissions' and 'users' tables.
    Uses unpooled/direct connection for DDL migrations.
    """
    submissions_table_query = """
        CREATE TABLE IF NOT EXISTS submissions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            username TEXT,
            full_name TEXT,
            data JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            status TEXT NOT NULL,
            admin_username TEXT
        )
    """
    
    users_table_query = """
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        username TEXT,
        language_code TEXT,
        first_seen TIMESTAMPTZ NOT NULL,
        last_seen TIMESTAMPTZ NOT NULL
    )
    """
    
    try:
        with get_db_connection(unpooled=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(submissions_table_query)
                cursor.execute(users_table_query)
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL database: {e}", exc_info=True)
        raise e

def make_submission_id(user_id: int) -> str:
    """Creates a unique ID for a submission."""
    return f"{user_id}-{int(datetime.utcnow().timestamp())}-{uuid.uuid4().hex[:6]}"

def _save_submission_to_pg(submission_id: str, user_id: str, user: Dict[str, Any], user_data: Dict[str, Any]):
    """
    Synchronously saves the submission data to PostgreSQL.
    This function is designed to be run in a separate thread.
    """
    data_json = json.dumps(user_data.copy(), default=str)
    created_at = datetime.utcnow()
    
    insert_query = """
        INSERT INTO submissions 
        (id, user_id, username, full_name, data, created_at, status, admin_username)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    insert_query,
                    (
                        submission_id,
                        user_id,
                        user.get('username', 'N/A'),
                        user.get('full_name', 'N/A'),
                        data_json,
                        created_at,
                        'pending',
                        '' 
                    )
                )
            conn.commit()
        logger.info(f"Submission {submission_id} saved to PostgreSQL.")
    except Exception as e:
        logger.error(f"Failed to save submission {submission_id} to PostgreSQL: {e}", exc_info=True)
        raise e


async def forward_to_admin(context: ContextTypes.DEFAULT_TYPE):
    """
    Formats and sends all data to the admin chat with approval buttons.
    Saves submission to PG using asyncio.to_thread to avoid blocking.
    """
    user_data = context.user_data
    user = user_data.get('user_object', {})
    
    if not ADMIN_CHAT_ID:
        logger.warning("ADMIN_CHAT_ID is not set. Cannot forward message.")
        return
        
    if not ADMIN_USERNAMES:
        logger.warning("ADMIN_USERNAMES list is empty. Cannot assign admin.")
        assignee_line = "Assignee: *Not Configured* (ADMIN_USERNAMES list is empty)\n\n"
    else:
        counter = context.bot_data.get('admin_counter', 0)
        assignee_username = ADMIN_USERNAMES[counter % len(ADMIN_USERNAMES)]
        context.bot_data['admin_counter'] = counter + 1
        assignee_line = f"Assignee: {assignee_username}\n\n"
    
    user_id_for_reply = "NOT_FOUND"
    if user and user.get('id'):
        user_id_for_reply = str(user.get('id'))
    else:
        user_id_for_reply = user_data.get('user_id_fallback', 'ERROR')
        user_data['user_id_fallback'] = user_id_for_reply
        
    submission_id = make_submission_id(user_id_for_reply)
    
    try:
        await asyncio.to_thread(
            _save_submission_to_pg,
            submission_id,
            user_id_for_reply,
            user,
            user_data
        )
    except Exception as e:
        logger.error(f"Failed to save submission {submission_id} to database: {e}", exc_info=True)
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🚨 CRITICAL ERROR 🚨\nFailed to save submission {submission_id} to the database. Error: {e}"
            )
        except Exception:
            pass
        return 

    try:
        # 1. Format the FULL text summary
        summary = f"🎉 *New DV Submission* 🎉\n\n"
        summary += assignee_line
        
        if user and user.get('id'):
            summary += f"From: {user.get('full_name', 'N/A')}\n"
            summary += f"Username: @{user.get('username', 'N/A')}\n"
            summary += f"User ID: `{user_id_for_reply}`\n\n"
        else:
            summary += "User Info: *Could not be loaded*\n"
            summary += f"User ID: `{user_id_for_reply}`\n\n"

        summary += format_summary(user_data)
        
        # --- MESSAGE 1: Send the full summary ---
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=summary,
            parse_mode=ParseMode.MARKDOWN
        )

        # --- THIS IS THE CHANGE: Build media group with clear captions ---
        media_group: List[InputMediaPhoto] = []
        
        # Helper to create a full name
        def get_full_name(given, middle, last):
            parts = [given, middle, last]
            return " ".join(part for part in parts if part and part.lower() != 'none')

        # 1. Applicant Photo
        if user_data.get('applicant_photo_id'):
            applicant_name = get_full_name(user_data.get('given_name'), user_data.get('middle_name'), user_data.get('surname'))
            media_group.append(InputMediaPhoto(
                media=user_data['applicant_photo_id'], 
                caption=f"👤 APPLICANT: {applicant_name.strip()}"
            ))
        
        # 2. Spouse Photo
        if user_data.get('spouse_photo_id'):
            spouse_name = get_full_name(user_data.get('spouse_given_name'), user_data.get('spouse_middle_name'), user_data.get('spouse_surname'))
            media_group.append(InputMediaPhoto(
                media=user_data['spouse_photo_id'], 
                caption=f"👩‍❤️‍👨 SPOUSE: {spouse_name.strip()}"
            ))
            
        # 3. Children Photos
        children = user_data.get('children', [])
        for i, child in enumerate(children, 1):
            if child.get('photo_id'):
                child_name = get_full_name(child.get('given_name'), child.get('middle_name'), child.get('surname'))
                media_group.append(InputMediaPhoto(
                    media=child['photo_id'], 
                    caption=f"👶 CHILD {i}: {child_name.strip()}"
                ))
        # --- End of Media Group Building ---

        # --- MESSAGE 2: Send photos of PEOPLE as an album (if any) ---
        if media_group:
            for i in range(0, len(media_group), 10):
                chunk = media_group[i:i+10]
                await context.bot.send_media_group(
                    chat_id=ADMIN_CHAT_ID,
                    media=chunk
                )
        
        # --- MESSAGE 3: Send PAYMENT photo / verification info ---
        if user_data.get('payment_screenshot_id'):
            await context.bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=user_data['payment_screenshot_id'],
                caption="PAYMENT SCREENSHOT"
            )
        elif user_data.get('payment_method') == 'chapa':
            tx_ref = user_data.get('payment_tx_ref', 'N/A')
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"💳 <b>PAYMENT STATUS:</b> ✅ <b>VERIFIED VIA CHAPA</b>\n<b>Amount:</b> 350 ETB\n<b>Tx Ref:</b> <code>{tx_ref}</code>",
                parse_mode=ParseMode.HTML
            )

        # --- MESSAGE 4: Send the action buttons ---
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve", callback_data=f"admin:approve:{submission_id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"admin:reject:{submission_id}")],
            [InlineKeyboardButton("📄 View JSON", callback_data=f"admin:view:{submission_id}")],
        ])
        
        button_text = (
            f"Submission ID: `{submission_id}`\n"
            f"User ID: `{user_id_for_reply}` (Reply to *this* message with PDF)\n"
            f"Please review the submission above and take action."
        )
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=button_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
                
    except Exception as e:
        logger.error(f"Failed to forward submission {submission_id} to admin (but it *is* saved in DB): {e}", exc_info=True)
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"Failed to format submission {submission_id} for admin. It *is* saved in the DB. Error: {e}"
            )
        except Exception:
            pass

# --- (No changes to _get_submission_data_pg, _update_submission_status_pg, 
# admin_action_handler, or handle_admin_reply) ---

def _get_submission_data_pg(sub_id: str) -> Optional[dict]:
    """Gets a pending submission's user_id and data from PG."""
    select_query = "SELECT user_id, data FROM submissions WHERE id = %s AND status = 'pending'"
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(select_query, (sub_id,))
                row = cursor.fetchone()
                if row:
                    return {"user_id": row[0], "data_json": row[1]}
    except Exception as e:
        logger.error(f"Failed to get submission {sub_id} from PG: {e}", exc_info=True)
    return None

def _update_submission_status_pg(sub_id: str, new_status: str, admin_username: str) -> bool:
    """Updates a submission's status in PG."""
    update_query = "UPDATE submissions SET status = %s, admin_username = %s WHERE id = %s"
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(update_query, (new_status, admin_username, sub_id))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to update status for {sub_id} in PG: {e}", exc_info=True)
        return False

async def admin_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
Signature:
    admin_action_handler(
        update: 'Update',
        context: 'ContextTypes.DEFAULT_TYPE',
    ) -> 'None'
Docstring:
    Handles admin button presses (Approve/Reject/View).
    Uses non-blocking PG functions.
    """
    query = update.callback_query
    await query.answer("Processing action...")
    
    try:
        action, sub_id = query.data.split(":")[1:3]
    except Exception as e:
        logger.error(f"Invalid admin callback data: {query.data} - {e}")
        await query.edit_message_text(text=f"{query.message.text}\n\n❌ Error: Invalid callback data.")
        return

    admin_username = query.from_user.username or query.from_user.full_name
    
    try:
        submission = await asyncio.to_thread(_get_submission_data_pg, sub_id)
        
        if not submission:
            await query.edit_message_text(text=f"{query.message.text}\n\n❌ Error: Submission `{sub_id}` not found or already processed.", parse_mode=ParseMode.MARKDOWN)
            return

        user_id = submission["user_id"]
        submission_data_json = submission["data_json"]
        
        if action == "approve":
            new_status = 'approved'
            success = await asyncio.to_thread(_update_submission_status_pg, sub_id, new_status, admin_username)
            if success:
                if user_id and user_id != "NOT_FOUND":
                    await context.bot.send_message(chat_id=user_id, text="🎉 Your DV application submission has been *approved* by the admin team. You will receive your PDF document shortly.", parse_mode=ParseMode.MARKDOWN)
                await query.edit_message_text(
                    text=f"{query.message.text}\n\n*✅ Approved by @{admin_username}*",
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"Submission {sub_id} for user {user_id} approved by {admin_username}")
            else:
                raise ConnectionError("Failed to update database.")

        elif action == "reject":
            new_status = 'rejected'
            success = await asyncio.to_thread(_update_submission_status_pg, sub_id, new_status, admin_username)
            if success:
                if user_id and user_id != "NOT_FOUND":
                    await context.bot.send_message(chat_id=user_id, text="❌ Your DV application submission has been *rejected* by the admin team. Please contact support or restart the form with /start.", parse_mode=ParseMode.MARKDOWN)
                await query.edit_message_text(
                    text=f"{query.message.text}\n\n*❌ Rejected by @{admin_username}*",
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"Submission {sub_id} for user {user_id} rejected by {admin_username}")
            else:
                raise ConnectionError("Failed to update database.")
                
        elif action == "view":
            await query.answer("Sending full data as JSON...", show_alert=True)
            try:
                # We can load the JSON from the string
                data_obj = json.loads(submission_data_json)
                data_str = json.dumps(data_obj, indent=2, default=str)
                # Send as a new message, which is better for large JSON
                await query.message.reply_text(f"```json\n{data_str}\n```", parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                await query.message.reply_text(f"Could not serialize data: {e}")
            return # Don't edit the original button message
                
    except Exception as e:
        logger.error(f"Error processing admin action {action} for {sub_id}: {e}", exc_info=True)
        await query.edit_message_text(text=f"{query.message.text}\n\n❌ Error: A database error occurred: {e}")
        return

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles when an admin replies with a PDF to the button message.
    """
    message = update.message
    if not message:
        logger.warning("handle_admin_reply triggered but no message data found.")
        return

    if str(message.chat_id) != str(ADMIN_CHAT_ID):
        return

    logger.info("Admin PDF reply detected. Processing.")

    try:
        original_message_text = message.reply_to_message.text
        if not original_message_text:
            await message.reply_text("❌ Error: Reply to the *button message* (the one with the User ID), not the photos.")
            return
            
        match = re.search(r"User ID: `?([a-zA-Z0-9_-]+)`?", original_message_text)
        if not match:
            await message.reply_text("❌ Error: Could not find `User ID: ...` in the original message.")
            return

        user_id_str = match.group(1)
        pdf_file_id = message.document.file_id
        
        # Guard against the fallback user_id value that means the ID was unknown
        if user_id_str == 'NOT_FOUND' or 'NOT_FOUND' in user_id_str:
            await message.reply_text("❌ Error: The original submission had no resolvable User ID (`NOT_FOUND`). Cannot send PDF.")
            return
        
        user_id_int = int(re.sub(r'[^0-9]', '', user_id_str.split('-')[0]))
        if user_id_int == 0:
            await message.reply_text("❌ Error: Resolved User ID is 0 — that's invalid. Please check the submission.")
            return
        
        # Safely get the user's language to send a localised caption
        try:
            all_user_data = await context.application.persistence.get_user_data()
            user_specific_data = all_user_data.get(user_id_int, {})
            lang = user_specific_data.get('language', 'en')
        except Exception:
            lang = 'en'
        
        from text import get_text as _get_text
        
        class _FakeContext:
            """Minimal context-like object for get_text."""
            class _ud(dict): pass
            user_data = _ud()
        
        fake_ctx = _FakeContext()
        fake_ctx.user_data['language'] = lang
        caption = _get_text("admin_pdf_caption", fake_ctx)
        
        await context.bot.send_document(
            chat_id=user_id_int,
            document=pdf_file_id,
            caption=caption
        )
        
        await message.reply_text(f"✅ PDF successfully sent to User ID `{user_id_str}` (int: {user_id_int}).")

    except Exception as e:
        logger.error(f"Failed to handle admin reply: {e}", exc_info=True)
        try:
            await message.reply_text(f"❌ Error sending PDF: {e}")
        except Exception as e2:
            logger.error(f"Failed to even send error reply to admin: {e2}")

if __name__ == "__main__":
    print("Initializing PostgreSQL database...")
    init_db()
    print("Database initialized successfully.")