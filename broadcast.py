import logging
import re
import uuid
import asyncio
import time
from typing import Optional, Tuple, List, Dict, Any

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
    error,
)
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import logger, ADMIN_CHAT_ID, ADMIN_USERNAMES, ADMIN_USER_IDS
from admin_handlers import get_db_connection


def is_admin_authorized(user: Optional[User], chat_id: Optional[int] = None) -> bool:
    """
    Checks if a user is authorized to trigger broadcasts.
    Authorized if:
    1. Username is in ADMIN_USERNAMES
    2. User ID is in ADMIN_USER_IDS
    3. The message is sent inside the designated ADMIN_CHAT_ID
    """
    if not user:
        return False

    # Check username
    if user.username:
        clean_user = user.username.lower().lstrip("@")
        admin_cleans = [u.lower().lstrip("@") for u in ADMIN_USERNAMES if u]
        if clean_user in admin_cleans:
            return True

    # Check user ID
    if user.id in ADMIN_USER_IDS:
        return True

    # Check admin chat ID
    if chat_id and str(chat_id) == str(ADMIN_CHAT_ID):
        return True

    return False


def get_broadcast_recipients() -> List[int]:
    """
    Retrieves all unique user IDs from PostgreSQL (users and submissions).
    """
    query = """
    SELECT DISTINCT user_id FROM (
        SELECT user_id::bigint AS user_id FROM users WHERE user_id IS NOT NULL AND user_id > 0
        UNION
        SELECT CASE 
            WHEN user_id ~ '^[0-9]+' THEN SPLIT_PART(user_id, '-', 1)::bigint 
            ELSE NULL 
        END AS user_id 
        FROM submissions
        WHERE user_id ~ '^[0-9]+'
    ) sub
    WHERE user_id IS NOT NULL AND user_id > 0;
    """
    user_ids: List[int] = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                user_ids = [r[0] for r in rows if r[0]]
        logger.info(f"Fetched {len(user_ids)} broadcast recipients from database.")
    except Exception as e:
        logger.error(f"Error fetching broadcast recipients from database: {e}", exc_info=True)
    return user_ids


def extract_ad_payload(message: Message) -> Tuple[Message, str, Optional[str], bool]:
    """
    Analyzes the message and extracts:
    - source_message: The message containing media/text to broadcast (handles replies)
    - media_type: 'photo', 'video', 'animation', 'document', 'audio', 'voice', or 'text'
    - content_text: The cleaned text or caption (stripped of /ad command and bot mentions)
    - is_immediate: True if the admin passed 'now' or 'send' flag
    """
    is_reply = message.reply_to_message is not None
    source_message = message.reply_to_message if is_reply else message

    cmd_raw = message.caption if message.caption else (message.text or "")

    # Strip leading @bot mention, /ad command, and optional secondary mention
    cleaned_after_cmd = re.sub(
        r"(?i)^(@[a-zA-Z0-9_]+\s+)?/ad(@[a-zA-Z0-9_]+)?(\s+@[a-zA-Z0-9_]+)?(\s+|$)",
        "",
        cmd_raw
    ).strip()

    # Check for immediate broadcast flag: e.g., "/ad now ..." or "/ad send ..."
    is_immediate = False
    if cleaned_after_cmd.lower().startswith("now ") or cleaned_after_cmd.lower() == "now":
        is_immediate = True
        cleaned_after_cmd = re.sub(r"(?i)^now(\s+|$)", "", cleaned_after_cmd).strip()
    elif cleaned_after_cmd.lower().startswith("send ") or cleaned_after_cmd.lower() == "send":
        is_immediate = True
        cleaned_after_cmd = re.sub(r"(?i)^send(\s+|$)", "", cleaned_after_cmd).strip()

    # Determine media type of the source message
    if source_message.photo:
        media_type = "photo"
    elif source_message.video:
        media_type = "video"
    elif source_message.animation:
        media_type = "animation"
    elif source_message.document:
        media_type = "document"
    elif source_message.audio:
        media_type = "audio"
    elif source_message.voice:
        media_type = "voice"
    else:
        media_type = "text"

    # Determine the final caption / text
    if is_reply:
        if cleaned_after_cmd:
            content_text = cleaned_after_cmd
        else:
            content_text = source_message.caption if source_message.caption else source_message.text
    else:
        content_text = cleaned_after_cmd if cleaned_after_cmd else None

    return source_message, media_type, content_text, is_immediate


async def run_broadcast_worker(
    bot,
    status_message: Message,
    ad_data: Dict[str, Any],
    user_ids: List[int]
) -> None:
    """
    Executes the broadcast asynchronously with rate limiting and progress updates.
    """
    total = len(user_ids)
    sent = 0
    blocked = 0
    failed = 0
    start_time = time.time()

    media_type = ad_data.get("media_type", "text")
    source_chat_id = ad_data.get("source_chat_id")
    source_message_id = ad_data.get("source_message_id")
    caption = ad_data.get("content_text")

    logger.info(f"Starting broadcast of type '{media_type}' to {total} users.")

    for i, user_id in enumerate(user_ids, 1):
        try:
            if media_type == "text":
                text_to_send = caption or "📢 Announcement"
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=text_to_send,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except error.BadRequest as br:
                    if "can't parse entities" in str(br).lower() or "entity" in str(br).lower():
                        await bot.send_message(chat_id=user_id, text=text_to_send, parse_mode=None)
                    else:
                        raise
            else:
                caption_param = caption if caption is not None else ""
                try:
                    await bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=source_chat_id,
                        message_id=source_message_id,
                        caption=caption_param if caption_param else None,
                        parse_mode=ParseMode.MARKDOWN if caption_param else None
                    )
                except error.BadRequest as br:
                    if "can't parse entities" in str(br).lower() or "entity" in str(br).lower():
                        await bot.copy_message(
                            chat_id=user_id,
                            from_chat_id=source_chat_id,
                            message_id=source_message_id,
                            caption=caption_param if caption_param else None,
                            parse_mode=None
                        )
                    else:
                        raise

            sent += 1

        except error.Forbidden:
            blocked += 1
        except error.BadRequest as br:
            err_msg = str(br).lower()
            if "chat not found" in err_msg or "user is deactivated" in err_msg or "bot can't initiate conversation" in err_msg:
                blocked += 1
            else:
                failed += 1
                logger.warning(f"BadRequest sending ad to {user_id}: {br}")
        except error.RetryAfter as ra:
            logger.warning(f"Flood limit reached during broadcast. Sleeping {ra.retry_after}s...")
            await asyncio.sleep(ra.retry_after + 0.5)
            try:
                if media_type == "text":
                    await bot.send_message(chat_id=user_id, text=caption or "", parse_mode=None)
                else:
                    await bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=source_chat_id,
                        message_id=source_message_id,
                        caption=caption if caption else None,
                        parse_mode=None
                    )
                sent += 1
            except Exception:
                failed += 1
        except Exception as e:
            failed += 1
            logger.error(f"Unexpected error broadcasting to {user_id}: {e}")

        # Throttle delay (~25 msgs/sec)
        await asyncio.sleep(0.04)

        # Update progress every 25 users
        if i % 25 == 0 or i == total:
            try:
                percent = int((i / total) * 100)
                await status_message.edit_text(
                    f"⏳ *Broadcasting Ad in Progress...*\n\n"
                    f"Progress: `{i}/{total}` ({percent}%)\n"
                    f"✅ Delivered: `{sent}`\n"
                    f"🚫 Blocked/Inactive: `{blocked}`\n"
                    f"❌ Failed: `{failed}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass

    elapsed = round(time.time() - start_time, 1)
    logger.info(f"Broadcast finished in {elapsed}s: {sent} sent, {blocked} blocked, {failed} failed.")

    try:
        final_text = (
            f"✅ *Ad Broadcast Completed!*\n\n"
            f"📁 *Type*: {media_type.capitalize()}\n"
            f"👥 *Total Recipients*: `{total}`\n"
            f"📨 *Successfully Delivered*: `{sent}`\n"
            f"🚫 *Blocked / Inactive*: `{blocked}`\n"
            f"❌ *Failed*: `{failed}`\n"
            f"⏱️ *Duration*: `{elapsed}s`"
        )
        await status_message.edit_text(final_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Failed to update final broadcast summary message: {e}")


async def handle_ad_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Triggered when an admin sends /ad in group or private chat, with or without media.
    """
    message = update.effective_message
    if not message:
        return

    user = update.effective_user
    chat = update.effective_chat
    chat_id = chat.id if chat else None

    # Check authorization
    if not is_admin_authorized(user, chat_id):
        logger.warning(f"Unauthorized /ad attempt by user {user.id if user else 'N/A'} in chat {chat_id}")
        await message.reply_text("⛔ You are not authorized to use the broadcast command.")
        return

    # Extract source content
    source_msg, media_type, content_text, is_immediate = extract_ad_payload(message)

    # Check if there is anything to send
    if media_type == "text" and not content_text:
        await message.reply_text(
            "ℹ️ *How to send an Ad / Announcement:*\n\n"
            "1. *Upload Media (Image / GIF / Video)*:\n"
            "   Add caption: `/ad Your announcement text`\n"
            "   *(or mention bot: `@bot /ad Your text`)*\n\n"
            "2. *Reply to any existing message*:\n"
            "   Reply to any photo, video, or message with `/ad`\n\n"
            "3. *Send text message*:\n"
            "   Type `/ad Your announcement text`\n\n"
            "⚡ Add `now` for instant broadcast without confirmation (e.g., `/ad now Special Sale!`)",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Fetch recipients
    user_ids = await asyncio.to_thread(get_broadcast_recipients)

    # Also merge persistence user IDs
    try:
        persist_data = await context.application.persistence.get_user_data()
        user_ids = list(set(user_ids).union([uid for uid in persist_data.keys() if isinstance(uid, int) and uid > 0]))
    except Exception as e:
        logger.warning(f"Could not merge persistence user IDs: {e}")

    if not user_ids:
        await message.reply_text("⚠️ No registered users found in the database to broadcast to.")
        return

    ad_data = {
        "source_chat_id": source_msg.chat_id,
        "source_message_id": source_msg.message_id,
        "media_type": media_type,
        "content_text": content_text,
    }

    if is_immediate:
        status_msg = await message.reply_text(
            f"⏳ *Starting immediate broadcast to {len(user_ids)} users...*",
            parse_mode=ParseMode.MARKDOWN
        )
        asyncio.create_task(run_broadcast_worker(context.bot, status_msg, ad_data, user_ids))
        return

    # Confirmation flow
    ad_id = uuid.uuid4().hex[:8]
    context.bot_data.setdefault("pending_ads", {})[ad_id] = {
        **ad_data,
        "user_ids": user_ids,
        "admin_id": user.id if user else 0,
        "created_at": time.time()
    }

    preview_snippet = content_text if content_text else "*(Media only - no caption)*"
    if len(preview_snippet) > 300:
        preview_snippet = preview_snippet[:300] + "..."

    confirm_text = (
        f"📢 *Ad Broadcast Confirmation*\n\n"
        f"📁 *Content Type*: {media_type.capitalize()}\n"
        f"👥 *Target Audience*: `{len(user_ids)}` users\n"
        f"📝 *Caption / Content*:\n{preview_snippet}\n\n"
        f"⚠️ *Send this broadcast to all {len(user_ids)} bot users?*"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 Send Now", callback_data=f"ad_broadcast:send:{ad_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"ad_broadcast:cancel:{ad_id}")
        ]
    ])
    await message.reply_text(confirm_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


async def handle_ad_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles confirmation callbacks (Send / Cancel) for ad broadcast.
    """
    query = update.callback_query
    if not query:
        return

    user = update.effective_user
    chat = update.effective_chat
    chat_id = chat.id if chat else None

    # Check authorization
    if not is_admin_authorized(user, chat_id):
        await query.answer("⛔ You are not authorized to perform this action.", show_alert=True)
        return

    parts = query.data.split(":")
    if len(parts) < 3:
        await query.answer("Invalid request.")
        return

    action = parts[1]
    ad_id = parts[2]

    pending_ads = context.bot_data.setdefault("pending_ads", {})

    if action == "cancel":
        pending_ads.pop(ad_id, None)
        await query.answer("Broadcast cancelled.")
        await query.edit_message_text("❌ *Broadcast cancelled by admin.*", parse_mode=ParseMode.MARKDOWN)
        return

    if action == "send":
        ad_data = pending_ads.pop(ad_id, None)
        if not ad_data:
            await query.answer("Broadcast draft expired or already sent.", show_alert=True)
            await query.edit_message_text("⚠️ *This broadcast draft has expired or was already sent.*", parse_mode=ParseMode.MARKDOWN)
            return

        user_ids = ad_data.pop("user_ids", [])
        await query.answer("🚀 Launching broadcast!")

        await query.edit_message_text(
            f"⏳ *Broadcasting Ad in Progress...*\n\n"
            f"Progress: `0/{len(user_ids)}` (0%)\n"
            f"Delivering messages in background...",
            parse_mode=ParseMode.MARKDOWN
        )

        asyncio.create_task(run_broadcast_worker(context.bot, query.message, ad_data, user_ids))
