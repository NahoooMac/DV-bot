import logging
import re
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    DictPersistence,
    PicklePersistence,
    CallbackQueryHandler,
    TypeHandler,
)

# --- NEW Imports for Analytics Job ---
from datetime import time
import pytz
from analytics import daily_analytics_job
# -----------------------------------

# --- Local Imports ---
from config import TOKEN, logger, ADMIN_CHAT_ID
from states import * # Import all states
from text import translations, build_regex_pattern
from telegram.constants import ParseMode

# Import all handler functions
from handlers import (
    start, start_reset, language_select, start_main_menu,
    show_help, show_support, show_my_data, clear_data_command,
    cancel, handle_soft_cancel, start_new_form,
    get_gender, get_surname, get_given_name, get_middle_name,
    get_dob, get_birth_city, get_birth_country,
    get_eligibility_confirm, get_eligibility_country,
    get_passport_confirm, get_passport_number, get_passport_issuance, get_passport_expiration,
    get_applicant_photo, get_current_residence, get_email, get_phone, get_education,
    get_marital_status, get_spouse_surname, get_spouse_given_name,
    get_spouse_middle_name, get_spouse_gender, get_spouse_dob, get_spouse_birth_city,
    get_spouse_birth_country, get_spouse_photo, get_children_count, get_child_info,
    get_final_confirm, get_payment_screenshot,
    invalid_text_handler, invalid_photo_handler, handle_top_level_photo,
    handle_chapa_callback
)
from admin_handlers import (
    handle_admin_reply, admin_action_handler, init_db
)
from photo_validator import (
    handle_ai_check_callback
)
from broadcast import (
    handle_ad_broadcast,
    handle_ad_callback,
    handle_broadcast_message_input
)


async def log_incoming_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Logs incoming updates for monitoring."""
    user = update.effective_user
    uid = user.id if user else "Unknown"
    uname = f"@{user.username}" if user and user.username else (user.first_name if user else "")
    if update.message:
        m = update.message
        if m.photo:
            logger.info(f"[Update] User {uid} ({uname}) sent PHOTO ({len(m.photo)} sizes, caption={m.caption!r})")
        elif m.document:
            logger.info(f"[Update] User {uid} ({uname}) sent DOCUMENT ({m.document.file_name}, mime={m.document.mime_type})")
        elif m.text:
            logger.info(f"[Update] User {uid} ({uname}) sent TEXT: {m.text[:60]!r}")
        else:
            logger.info(f"[Update] User {uid} ({uname}) sent MEDIA/OTHER")
    elif update.callback_query:
        logger.info(f"[Update] User {uid} ({uname}) sent CALLBACK: {update.callback_query.data!r}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates and notify the user (in private chats only)."""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat and update.effective_chat.type == "private":
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Sorry, I'm having trouble connecting right now. Please try again in a moment."
            )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")

# --- Main Function ---

def main() -> None:
    """Run the bot."""
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to initialize database on startup: {e}")
        return 

    persistence = PicklePersistence(filepath="dv_bot_persistence.pickle")

    application = (
        Application.builder()
        .token(TOKEN)
        .persistence(persistence)
        .read_timeout(45)
        .write_timeout(45)
        .connect_timeout(45)
        .pool_timeout(45)
        .build()
    )

    # --- Build Regex Filters for Buttons ---
    new_form_filter = build_regex_pattern("new_form_button", prefix="📋 ")
    my_data_filter = build_regex_pattern("my_data_title", prefix="🗂️ ")
    language_filter = filters.Regex(r"^🌍 Language$")
    help_filter = filters.Regex(r"^❓ Help$")
    support_filter = filters.Regex(r"^💬 Support$")
    cleardata_filter = filters.Regex(r"^🗑️ Clear Data$")

    gender_filter = build_regex_pattern("gender_male") | build_regex_pattern("gender_female")
    yes_filter = build_regex_pattern("yes")
    no_filter = build_regex_pattern("no")
    education_filter = (
        build_regex_pattern("edu_primary") |
        build_regex_pattern("edu_high_school_no_diploma") |
        build_regex_pattern("edu_high_school_degree") |
        build_regex_pattern("edu_vocational") |
        build_regex_pattern("edu_some_university") |
        build_regex_pattern("edu_bachelor") |
        build_regex_pattern("edu_master") |
        build_regex_pattern("edu_doctorate")
    )
    marital_status_filter = (
        build_regex_pattern("status_single") |
        build_regex_pattern("status_married_non_us") |
        build_regex_pattern("status_married_us") |
        build_regex_pattern("status_married") |
        build_regex_pattern("status_divorced") |
        build_regex_pattern("status_widowed") |
        build_regex_pattern("status_separated")
    )
    confirm_filter = build_regex_pattern("confirm")
    edit_filter = build_regex_pattern("edit_restart")

    # Flexible photo & document filter (covers compressed photos and raw image files)
    media_photo_filter = filters.PHOTO | (filters.Document.ALL & ~filters.COMMAND)

    # Strictly limit user-facing application flows to direct private chats.
    # This completely prevents any bot application dialogs from appearing in admin groups or supergroups.
    private_chat = filters.ChatType.PRIVATE

    # --- Conversation Handler for the DV Form ---
    dv_form_handler = ConversationHandler(
        entry_points=[
            CommandHandler("newform", start_new_form, filters=private_chat),
            MessageHandler(new_form_filter & private_chat, start_new_form),
        ],
        states={
            GET_GENDER: [MessageHandler(gender_filter & private_chat, get_gender)],
            GET_SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_surname)],
            GET_GIVEN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_given_name)],
            GET_MIDDLE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_middle_name)],
            GET_DOB: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_dob)],
            GET_BIRTH_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_birth_city)],
            GET_BIRTH_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_birth_country)],
            GET_ELIGIBILITY_CONFIRM: [MessageHandler((yes_filter | no_filter) & private_chat, get_eligibility_confirm)],
            GET_ELIGIBILITY_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_eligibility_country)],
            GET_PASSPORT_CONFIRM: [MessageHandler((yes_filter | no_filter) & private_chat, get_passport_confirm)],
            GET_PASSPORT_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_passport_number)],
            GET_PASSPORT_ISSUANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_passport_issuance)],
            GET_PASSPORT_EXPIRATION: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_passport_expiration)],

            GET_APPLICANT_PHOTO: [
                MessageHandler(media_photo_filter & private_chat, get_applicant_photo),
                CallbackQueryHandler(handle_ai_check_callback, pattern="^dv:")
            ],
            GET_CURRENT_RESIDENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_current_residence)],
            GET_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_email)],
            GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_phone)],
            GET_EDUCATION: [MessageHandler(education_filter & private_chat, get_education)],
            GET_MARITAL_STATUS: [MessageHandler(marital_status_filter & private_chat, get_marital_status)],
            GET_SPOUSE_SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_spouse_surname)],
            GET_SPOUSE_GIVEN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_spouse_given_name)],
            GET_SPOUSE_MIDDLE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_spouse_middle_name)],
            GET_SPOUSE_GENDER: [MessageHandler(gender_filter & private_chat, get_spouse_gender)],
            GET_SPOUSE_DOB: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_spouse_dob)],
            GET_SPOUSE_BIRTH_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_spouse_birth_city)],
            GET_SPOUSE_BIRTH_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_spouse_birth_country)],

            GET_SPOUSE_PHOTO: [
                MessageHandler(media_photo_filter & private_chat, get_spouse_photo),
                CallbackQueryHandler(handle_ai_check_callback, pattern="^dv:")
            ],
            GET_CHILDREN_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_children_count)],

            GET_CHILD_INFO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, get_child_info),
                MessageHandler(media_photo_filter & private_chat, get_child_info),
                CallbackQueryHandler(handle_ai_check_callback, pattern="^dv:")
            ],
            GET_FINAL_CONFIRM: [MessageHandler((confirm_filter | edit_filter) & private_chat, get_final_confirm)],
            GET_PAYMENT_SCREENSHOT: [
                MessageHandler(media_photo_filter & private_chat, get_payment_screenshot),
                CallbackQueryHandler(handle_chapa_callback, pattern="^chapa:")
            ],
            CONFIRM_CANCEL_FORM: [CallbackQueryHandler(handle_soft_cancel, pattern="^soft_cancel_")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel, filters=private_chat),
            CommandHandler("start", start_main_menu, filters=private_chat),
            CommandHandler("help", show_help, filters=private_chat),
            MessageHandler(help_filter & private_chat, show_help),
            CommandHandler("mydata", show_my_data, filters=private_chat),
            MessageHandler(my_data_filter & private_chat, show_my_data),
            CommandHandler("support", show_support, filters=private_chat),
            MessageHandler(support_filter & private_chat, show_support),
            CommandHandler("cleardata", clear_data_command, filters=private_chat),
            MessageHandler(cleardata_filter & private_chat, clear_data_command),
            MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, invalid_text_handler),
            MessageHandler((filters.PHOTO | filters.Document.ALL) & private_chat, invalid_photo_handler),
        ],
        name="dv_form_conversation",
        persistent=True
    )

    # --- Top-level Conversation Handler for Language Selection ---
    lang_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start, filters=private_chat),
            CommandHandler("cleardata", start_reset, filters=private_chat),
            MessageHandler(language_filter & private_chat, start_reset),
        ],
        states={
            SELECT_LANGUAGE: [MessageHandler(filters.Regex(r'^(English 🇬🇧|Amharic 🇪🇹|Oromiffa 🇪🇹|Tigrigna 🇪🇹)$') & private_chat, language_select)],
        },
        fallbacks=[CommandHandler("start", start, filters=private_chat)],
        name="language_selection",
        persistent=True,
    )

    # Register the error handler
    application.add_error_handler(error_handler)

    # Logging all updates in real-time
    application.add_handler(TypeHandler(Update, log_incoming_update), group=-1)

    # Chapa callback query handler
    application.add_handler(CallbackQueryHandler(handle_chapa_callback, pattern="^chapa:"))

    application.add_handler(lang_handler)
    application.add_handler(dv_form_handler)

    # --- Top-level photo & document handler (catches photos sent outside active form in private chat) ---
    application.add_handler(MessageHandler(media_photo_filter & private_chat, handle_top_level_photo))

    # --- Add other top-level handlers (Main Menu in private chat only) ---
    application.add_handler(MessageHandler(my_data_filter & private_chat, show_my_data))
    application.add_handler(CommandHandler("mydata", show_my_data, filters=private_chat))

    application.add_handler(MessageHandler(help_filter & private_chat, show_help))
    application.add_handler(CommandHandler("help", show_help, filters=private_chat))

    application.add_handler(MessageHandler(support_filter & private_chat, show_support))
    application.add_handler(CommandHandler("support", show_support, filters=private_chat))

    # Top-level fallback text handler: show main menu instead of dead silence ONLY in private chat
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat, start_main_menu))

    # --- Add Admin Handlers (Admin group only) ---
    admin_chat_filter = filters.Chat(chat_id=int(ADMIN_CHAT_ID)) if ADMIN_CHAT_ID else filters.ChatType.GROUPS
    application.add_handler(MessageHandler(
        admin_chat_filter & filters.REPLY & filters.Document.PDF,
        handle_admin_reply
    ))
    application.add_handler(CallbackQueryHandler(admin_action_handler, pattern="^admin:"))
    
    # --- Add Broadcast Handlers (Admin group & Admin users) ---
    application.add_handler(CommandHandler(["ad", "broadcast"], handle_ad_broadcast))
    application.add_handler(MessageHandler(filters.CaptionRegex(r"(?i)^(@\w+\s+)?/(ad|broadcast)\b"), handle_ad_broadcast))
    application.add_handler(MessageHandler(filters.Regex(r"(?i)^@[a-zA-Z0-9_]+\s+/(ad|broadcast)\b"), handle_ad_broadcast))
    application.add_handler(CallbackQueryHandler(handle_ad_callback, pattern="^ad_broadcast:"))
    # Interactive broadcast listener for admin media and message inputs
    application.add_handler(MessageHandler(
        (filters.ALL & ~filters.COMMAND),
        handle_broadcast_message_input
    ), group=1)
    
    # --- Analytics Job ---
    job_queue = application.job_queue
    eat_tz = pytz.timezone('Africa/Nairobi')
    report_time = time(hour=23, minute=55, tzinfo=eat_tz)
    job_queue.run_daily(
        daily_analytics_job, 
        report_time, 
        days=(0, 1, 2, 3, 4, 5, 6)
    )
    logger.info(f"Scheduled daily analytics job for {report_time} EAT.")
    # -------------------

    # Run the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()