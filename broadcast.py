import logging
import re
import uuid
import asyncio
import time
import html
from typing import Optional, Tuple, List, Dict, Any

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    MessageEntity,
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

    if user.username:
        clean_user = user.username.lower().lstrip("@")
        admin_cleans = [u.lower().lstrip("@") for u in ADMIN_USERNAMES if u]
        if clean_user in admin_cleans:
            return True

    if user.id in ADMIN_USER_IDS:
        return True

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


def clean_caption_and_entities(
    raw_caption: Optional[str],
    raw_entities: Optional[List[MessageEntity]]
) -> Tuple[Optional[str], Optional[List[MessageEntity]], bool]:
    """
    Completely removes /ad, /broadcast commands, tags, mentions, and shifts formatting entities.
    Returns: (cleaned_caption, cleaned_entities, is_immediate)
    """
    if not raw_caption:
        return None, None, False

    # Check for leading /ad or /broadcast command with optional flags
    lead_pattern = r"^(?:@[a-zA-Z0-9_]+\s+)?/(?:ad|broadcast)(?:@[a-zA-Z0-9_]+)?(?:\s+(?:now|send))?[:\s-]*"
    match = re.match(lead_pattern, raw_caption, flags=re.IGNORECASE)
    
    is_immediate = False
    cleaned = raw_caption
    prefix_len = 0

    if match:
        matched_str = match.group(0)
        prefix_len = len(matched_str)
        if re.search(r"\b(now|send)\b", matched_str, flags=re.IGNORECASE):
            is_immediate = True
        cleaned = raw_caption[prefix_len:]

    # Also clean any leftover /ad or /broadcast tags from anywhere in the text
    cleaned_final = re.sub(r"(?i)(?:^|\s)/(?:ad|broadcast)(?:@[a-zA-Z0-9_]+)?(?:\s|$)", " ", cleaned).strip()

    if not cleaned_final:
        return None, None, is_immediate

    # Adjust formatting entities so bold/italic/links/mentions stay accurate
    cleaned_entities = []
    if raw_entities:
        for ent in raw_entities:
            # Drop the bot_command entity for /ad or /broadcast
            if ent.type == "bot_command":
                cmd_word = raw_caption[ent.offset:ent.offset + ent.length].lower()
                if "/ad" in cmd_word or "/broadcast" in cmd_word:
                    continue

            # Drop entities inside the stripped prefix
            if ent.offset + ent.length <= prefix_len:
                continue

            new_offset = max(0, ent.offset - prefix_len)
            new_length = ent.length - max(0, prefix_len - ent.offset)

            if new_length > 0:
                cleaned_entities.append(MessageEntity(
                    type=ent.type,
                    offset=new_offset,
                    length=new_length,
                    url=ent.url,
                    user=ent.user,
                    language=ent.language,
                    custom_emoji_id=ent.custom_emoji_id
                ))

    return cleaned_final, (cleaned_entities if cleaned_entities else None), is_immediate


def extract_ad_payload(message: Message) -> Tuple[Message, str, Optional[str], Optional[List[MessageEntity]], bool]:
    """
    Analyzes message and extracts:
    - source_message: message to broadcast (handles replies)
    - media_type: 'photo', 'video', 'animation', 'document', 'audio', 'voice', or 'text'
    - custom_caption: cleaned caption/text with all /ad and /broadcast tags removed
    - custom_entities: cleaned formatting entities
    - is_immediate: True if 'now' flag passed
    """
    is_reply = message.reply_to_message is not None
    source_message = message.reply_to_message if is_reply else message

    cmd_raw = message.caption if message.caption else (message.text or "")
    raw_entities = list(message.caption_entities if message.caption else (message.entities or []))

    # Determine media type of source message
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

    if is_reply:
        cleaned_cmd, _, is_immediate = clean_caption_and_entities(cmd_raw, raw_entities)
        if cleaned_cmd:
            custom_caption = cleaned_cmd
            custom_entities = None
        else:
            # Clean source message caption/text to ensure no /ad or /broadcast tag exists
            src_raw = source_message.caption if source_message.caption else source_message.text
            src_ents = list(source_message.caption_entities if source_message.caption else (source_message.entities or []))
            custom_caption, custom_entities, _ = clean_caption_and_entities(src_raw, src_ents)
    else:
        custom_caption, custom_entities, is_immediate = clean_caption_and_entities(cmd_raw, raw_entities)

    return source_message, media_type, custom_caption, custom_entities, is_immediate


async def prepare_ad_broadcast(
    message: Message,
    context: ContextTypes.DEFAULT_TYPE,
    source_msg: Message,
    media_type: str,
    caption: Optional[str],
    entities: Optional[List[MessageEntity]],
    is_immediate: bool = False
) -> None:
    """
    Prepares the broadcast: validates recipients, sends visual preview, and presents confirmation buttons.
    Ensures /ad and /broadcast tags are completely absent from user payloads.
    """
    user = message.from_user

    # Fetch recipients
    user_ids = await asyncio.to_thread(get_broadcast_recipients)
    try:
        persist_data = await context.application.persistence.get_user_data()
        user_ids = list(set(user_ids).union([uid for uid in persist_data.keys() if isinstance(uid, int) and uid > 0]))
    except Exception as e:
        logger.warning(f"Could not merge persistence user IDs: {e}")

    if not user_ids:
        await message.reply_text("⚠️ No registered users found in the database to broadcast to.")
        return

    ad_id = uuid.uuid4().hex[:8]
    clean_cap = caption if caption is not None else ""
    ad_data = {
        "source_chat_id": source_msg.chat_id,
        "source_message_id": source_msg.message_id,
        "media_type": media_type,
        "caption": clean_cap,
        "entities": entities,
        "user_ids": user_ids,
        "admin_id": user.id if user else 0,
        "created_at": time.time()
    }

    if is_immediate:
        status_msg = await message.reply_text(
            f"⏳ <b>Starting immediate broadcast to {len(user_ids)} users...</b>",
            parse_mode=ParseMode.HTML
        )
        asyncio.create_task(run_broadcast_worker(context.bot, status_msg, ad_data, user_ids))
        return

    # Store pending ad
    context.bot_data.setdefault("pending_ads", {})[ad_id] = ad_data

    # Send visual preview to admin
    try:
        await message.reply_text("🔍 <b>Broadcast Preview (as users will see it):</b>", parse_mode=ParseMode.HTML)
        if media_type == "text":
            if entities:
                await context.bot.send_message(
                    chat_id=message.chat_id,
                    text=clean_cap or "📢 Announcement",
                    entities=entities
                )
            else:
                await context.bot.send_message(
                    chat_id=message.chat_id,
                    text=clean_cap or "📢 Announcement",
                    parse_mode=None
                )
        else:
            if entities and clean_cap:
                await context.bot.copy_message(
                    chat_id=message.chat_id,
                    from_chat_id=source_msg.chat_id,
                    message_id=source_msg.message_id,
                    caption=clean_cap,
                    caption_entities=entities
                )
            else:
                await context.bot.copy_message(
                    chat_id=message.chat_id,
                    from_chat_id=source_msg.chat_id,
                    message_id=source_msg.message_id,
                    caption=clean_cap,
                    parse_mode=None
                )
    except Exception as e:
        logger.warning(f"Could not send exact preview: {e}")

    # Confirmation control panel
    confirm_text = (
        f"📢 <b>Confirm Announcement Broadcast</b>\n\n"
        f"👥 <b>Total Target Users:</b> <code>{len(user_ids)}</code>\n"
        f"📁 <b>Media Type:</b> <code>{media_type.capitalize()}</code>\n\n"
        f"<i>Ready to send this broadcast to all users?</i>"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 Send to All Users", callback_data=f"ad_broadcast:send:{ad_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"ad_broadcast:cancel:{ad_id}")
        ]
    ])

    await message.reply_text(confirm_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


async def handle_ad_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Entry point for /ad or /broadcast command or media caption with /ad.
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

    source_msg, media_type, caption, entities, is_immediate = extract_ad_payload(message)

    # If user simply sent /ad with no media and no text, and not a reply
    if media_type == "text" and not caption:
        context.user_data["awaiting_broadcast"] = True
        guide_text = (
            "📢 <b>Broadcast Mode Activated</b>\n\n"
            "Please send or forward whatever you want to broadcast:\n"
            "• 📷 <b>Photo</b> (with or without caption)\n"
            "• 🎥 <b>Video / GIF</b>\n"
            "• 📄 <b>Document / Audio</b>\n"
            "• 💬 <b>Formatted Text Message</b>\n"
            "• 🔄 <b>Or forward any post from a channel</b>\n\n"
            "<i>(All /ad or /broadcast tags are automatically stripped from user copies.)</i>\n"
            "<i>Send /cancel anytime to cancel.</i>"
        )
        await message.reply_text(guide_text, parse_mode=ParseMode.HTML)
        return

    # User provided content directly or replied to a message
    await prepare_ad_broadcast(
        message=message,
        context=context,
        source_msg=source_msg,
        media_type=media_type,
        caption=caption,
        entities=entities,
        is_immediate=is_immediate
    )


async def handle_broadcast_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Catches messages when admin is in interactive broadcast mode.
    """
    if not context.user_data.get("awaiting_broadcast"):
        return

    message = update.effective_message
    if not message:
        return

    user = update.effective_user
    chat = update.effective_chat
    chat_id = chat.id if chat else None

    if not is_admin_authorized(user, chat_id):
        return

    # Check if admin canceled
    text = (message.text or message.caption or "").strip()
    if text.lower() in ["/cancel", "cancel"]:
        context.user_data.pop("awaiting_broadcast", None)
        await message.reply_text("❌ <b>Broadcast cancelled.</b>", parse_mode=ParseMode.HTML)
        return

    # Clear awaiting state
    context.user_data.pop("awaiting_broadcast", None)

    # Determine media type and clean caption/entities
    if message.photo:
        media_type = "photo"
    elif message.video:
        media_type = "video"
    elif message.animation:
        media_type = "animation"
    elif message.document:
        media_type = "document"
    elif message.audio:
        media_type = "audio"
    elif message.voice:
        media_type = "voice"
    else:
        media_type = "text"

    raw_caption = message.caption if message.caption else message.text
    raw_entities = list(message.caption_entities if message.caption else (message.entities or []))

    # Strip any /ad or /broadcast tags from the message
    caption, entities, _ = clean_caption_and_entities(raw_caption, raw_entities)

    await prepare_ad_broadcast(
        message=message,
        context=context,
        source_msg=message,
        media_type=media_type,
        caption=caption,
        entities=entities,
        is_immediate=False
    )


async def handle_ad_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles confirmation callbacks (Send / Cancel / Dismiss) for ad broadcast.
    """
    query = update.callback_query
    if not query:
        return

    user = update.effective_user
    chat = update.effective_chat
    chat_id = chat.id if chat else None

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

    if action == "dismiss":
        try:
            await query.message.delete()
        except Exception:
            await query.edit_message_text("✅ <b>Report closed.</b>", parse_mode=ParseMode.HTML)
        return

    if action == "cancel":
        pending_ads.pop(ad_id, None)
        await query.answer("Broadcast cancelled.")
        await query.edit_message_text("❌ <b>Broadcast cancelled by admin.</b>", parse_mode=ParseMode.HTML)
        return

    if action == "send":
        ad_data = pending_ads.pop(ad_id, None)
        if not ad_data:
            await query.answer("Broadcast draft expired or already sent.", show_alert=True)
            await query.edit_message_text("⚠️ <b>This broadcast draft has expired or was already sent.</b>", parse_mode=ParseMode.HTML)
            return

        user_ids = ad_data.pop("user_ids", [])
        await query.answer("🚀 Launching broadcast!")

        await query.edit_message_text(
            f"⏳ <b>[Admin Only] Broadcasting in Progress...</b>\n\n"
            f"Progress: <code>0/{len(user_ids)}</code> (0%)\n"
            f"Delivering messages to users...",
            parse_mode=ParseMode.HTML
        )

        asyncio.create_task(run_broadcast_worker(context.bot, query.message, ad_data, user_ids))


async def run_broadcast_worker(
    bot,
    status_message: Message,
    ad_data: Dict[str, Any],
    user_ids: List[int]
) -> None:
    """
    Executes the broadcast asynchronously with rate limiting and progress updates.
    Guarantees users only see clean media or text with NO /ad or /broadcast tags.
    """
    total = len(user_ids)
    sent = 0
    blocked = 0
    failed = 0
    start_time = time.time()

    media_type = ad_data.get("media_type", "text")
    source_chat_id = ad_data.get("source_chat_id")
    source_message_id = ad_data.get("source_message_id")
    clean_caption = ad_data.get("caption", "")
    entities = ad_data.get("entities")

    logger.info(f"Starting broadcast of type '{media_type}' to {total} users.")

    for i, user_id in enumerate(user_ids, 1):
        try:
            if media_type == "text":
                text_to_send = clean_caption or "📢 Announcement"
                try:
                    if entities:
                        await bot.send_message(
                            chat_id=user_id,
                            text=text_to_send,
                            entities=entities
                        )
                    else:
                        await bot.send_message(
                            chat_id=user_id,
                            text=text_to_send,
                            parse_mode=None
                        )
                except Exception:
                    await bot.send_message(chat_id=user_id, text=text_to_send, parse_mode=None)
            else:
                # Media (photo, video, animation, document, etc.)
                # Passing clean_caption guarantees /ad and /broadcast are never shown to recipients
                try:
                    if entities and clean_caption:
                        await bot.copy_message(
                            chat_id=user_id,
                            from_chat_id=source_chat_id,
                            message_id=source_message_id,
                            caption=clean_caption,
                            caption_entities=entities
                        )
                    else:
                        await bot.copy_message(
                            chat_id=user_id,
                            from_chat_id=source_chat_id,
                            message_id=source_message_id,
                            caption=clean_caption,
                            parse_mode=None
                        )
                except error.BadRequest:
                    await bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=source_chat_id,
                        message_id=source_message_id,
                        caption=clean_caption,
                        parse_mode=None
                    )

            sent += 1

        except error.Forbidden:
            blocked += 1
        except error.BadRequest as br:
            err_msg = str(br).lower()
            if any(k in err_msg for k in ["chat not found", "deactivated", "can't initiate"]):
                blocked += 1
            else:
                failed += 1
                logger.warning(f"BadRequest broadcasting to {user_id}: {br}")
        except error.RetryAfter as ra:
            logger.warning(f"Flood limit reached during broadcast. Sleeping {ra.retry_after}s...")
            await asyncio.sleep(ra.retry_after + 0.5)
            try:
                if media_type == "text":
                    await bot.send_message(chat_id=user_id, text=clean_caption or "", parse_mode=None)
                else:
                    await bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=source_chat_id,
                        message_id=source_message_id,
                        caption=clean_caption,
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

        # Update progress every 25 users or at end
        if i % 25 == 0 or i == total:
            try:
                percent = int((i / total) * 100)
                await status_message.edit_text(
                    f"⏳ <b>[Admin Only] Broadcasting in Progress...</b>\n\n"
                    f"Progress: <code>{i}/{total}</code> ({percent}%)\n"
                    f"✅ Delivered: <code>{sent}</code>\n"
                    f"🚫 Blocked / Inactive: <code>{blocked}</code>\n"
                    f"❌ Failed: <code>{failed}</code>",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass

    elapsed = round(time.time() - start_time, 1)
    logger.info(f"Broadcast finished in {elapsed}s: {sent} sent, {blocked} blocked, {failed} failed.")

    try:
        final_text = (
            f"🔒 <b>[Admin Only] Broadcast Summary</b>\n"
            f"<i>(Visible only to you as admin. Bot users only received the ad media/text.)</i>\n\n"
            f"✅ <b>Ad Successfully Broadcasted!</b>\n"
            f"📁 <b>Content:</b> <code>{media_type.capitalize()}</code>\n"
            f"👥 <b>Delivered to:</b> <code>{sent}</code> users\n"
            f"🚫 <b>Blocked / Inactive:</b> <code>{blocked}</code>\n"
            f"⏱️ <b>Time Taken:</b> <code>{elapsed}s</code>"
        )
        dismiss_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Clear Admin Report", callback_data="ad_broadcast:dismiss:0")]
        ])
        await status_message.edit_text(final_text, reply_markup=dismiss_kb, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Failed to update final broadcast summary message: {e}")
