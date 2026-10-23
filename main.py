import logging
import re
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,  # <--- Using v13 import
    DictPersistence,
    CallbackQueryHandler,
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
    invalid_text_handler, invalid_photo_handler
)
from admin_handlers import (
    handle_admin_reply, admin_action_handler, init_db
)
from photo_validator import (
    handle_ai_check_callback
)
from broadcast import (
    handle_ad_broadcast,
    handle_ad_callback
)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates and notify the user."""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat:
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

    persistence = DictPersistence()

    # --- THIS IS THE CHANGE ---
    application = (
        Application.builder()
        .token(TOKEN)
        .persistence(persistence)
        .read_timeout(45)  # Wait up to 45 seconds for Telegram to send data
        .connect_timeout(45) # Wait up to 45 seconds to connect
        .build()
    )
    # --------------------------

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

    # --- Conversation Handler for the DV Form ---
    dv_form_handler = ConversationHandler(
        entry_points=[
            CommandHandler("newform", start_new_form),
            MessageHandler(new_form_filter, start_new_form),
        ],
        states={
            GET_GENDER: [MessageHandler(gender_filter, get_gender)],
            GET_SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_surname)],
            GET_GIVEN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_given_name)],
            GET_MIDDLE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_middle_name)],
            GET_DOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_dob)],
            GET_BIRTH_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birth_city)],
            GET_BIRTH_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birth_country)],
            GET_ELIGIBILITY_CONFIRM: [MessageHandler(yes_filter | no_filter, get_eligibility_confirm)],
            GET_ELIGIBILITY_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_eligibility_country)],
            GET_PASSPORT_CONFIRM: [MessageHandler(yes_filter | no_filter, get_passport_confirm)],
            GET_PASSPORT_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_passport_number)],
            GET_PASSPORT_ISSUANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_passport_issuance)],
            GET_PASSPORT_EXPIRATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_passport_expiration)],

            GET_APPLICANT_PHOTO: [
                MessageHandler(filters.PHOTO, get_applicant_photo),
                CallbackQueryHandler(handle_ai_check_callback, pattern="^dv:")
            ],
            GET_CURRENT_RESIDENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_current_residence)],
            GET_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            GET_EDUCATION: [MessageHandler(education_filter, get_education)],
            GET_MARITAL_STATUS: [MessageHandler(marital_status_filter, get_marital_status)],
            GET_SPOUSE_SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_spouse_surname)],
            GET_SPOUSE_GIVEN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_spouse_given_name)],
            GET_SPOUSE_MIDDLE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_spouse_middle_name)],
            GET_SPOUSE_GENDER: [MessageHandler(gender_filter, get_spouse_gender)],
            GET_SPOUSE_DOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_spouse_dob)],
            GET_SPOUSE_BIRTH_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_spouse_birth_city)],
            GET_SPOUSE_BIRTH_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_spouse_birth_country)],

            GET_SPOUSE_PHOTO: [
                MessageHandler(filters.PHOTO, get_spouse_photo),
                CallbackQueryHandler(handle_ai_check_callback, pattern="^dv:")
            ],
            GET_CHILDREN_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_children_count)],

            GET_CHILD_INFO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_child_info),
                MessageHandler(filters.PHOTO, get_child_info),
                CallbackQueryHandler(handle_ai_check_callback, pattern="^dv:")
            ],
            GET_FINAL_CONFIRM: [MessageHandler(confirm_filter | edit_filter, get_final_confirm)],
            GET_PAYMENT_SCREENSHOT: [MessageHandler(filters.PHOTO, get_payment_screenshot)],
            CONFIRM_CANCEL_FORM: [CallbackQueryHandler(handle_soft_cancel, pattern="^soft_cancel_")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start_main_menu),
            CommandHandler("help", show_help),
            MessageHandler(help_filter, show_help),
            CommandHandler("mydata", show_my_data),
            MessageHandler(my_data_filter, show_my_data),
            CommandHandler("support", show_support),
            MessageHandler(support_filter, show_support),
            CommandHandler("cleardata", clear_data_command),
            MessageHandler(cleardata_filter, clear_data_command),
            MessageHandler(filters.TEXT & ~filters.COMMAND, invalid_text_handler),
            MessageHandler(filters.PHOTO, invalid_photo_handler),
        ],
        name="dv_form_conversation",
        persistent=True
    )

    # --- Top-level Conversation Handler for Language Selection ---
    lang_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("cleardata", start_reset),
            MessageHandler(language_filter, start_reset),
        ],
        states={
            SELECT_LANGUAGE: [MessageHandler(filters.Regex(r'^(English 🇬🇧|Amharic 🇪🇹|Oromiffa 🇪🇹|Tigrigna 🇪🇹)$'), language_select)],
        },
        fallbacks=[CommandHandler("start", start)],
        name="language_selection",
        persistent=True,
    )

    # Register the error handler
    application.add_error_handler(error_handler)

    # --- Ad Broadcast Handlers (Group & Direct Admin Broadcasting) ---
    application.add_handler(CommandHandler("ad", handle_ad_broadcast))
    ad_caption_filter = filters.CaptionRegex(r"(?i)^(@[a-zA-Z0-9_]+\s+)?/ad(@[a-zA-Z0-9_]+)?(\s+@[a-zA-Z0-9_]+)?(\s+|$)")
    application.add_handler(MessageHandler(ad_caption_filter, handle_ad_broadcast))
    ad_mention_text_filter = filters.Regex(r"(?i)^@[a-zA-Z0-9_]+\s+/ad(@[a-zA-Z0-9_]+)?(\s+|$)")
    application.add_handler(MessageHandler(ad_mention_text_filter, handle_ad_broadcast))
    application.add_handler(CallbackQueryHandler(handle_ad_callback, pattern="^ad_broadcast:"))

    application.add_handler(lang_handler)
    application.add_handler(dv_form_handler)

    # --- Add other top-level handlers (Main Menu) ---
    application.add_handler(MessageHandler(my_data_filter, show_my_data))
    application.add_handler(CommandHandler("mydata", show_my_data))

    application.add_handler(MessageHandler(help_filter, show_help))
    application.add_handler(CommandHandler("help", show_help))

    application.add_handler(MessageHandler(support_filter, show_support))
    application.add_handler(CommandHandler("support", show_support))

    # --- Add Admin Handlers ---
    application.add_handler(MessageHandler(
        filters.Chat(chat_id=int(ADMIN_CHAT_ID)) & filters.REPLY & filters.Document.PDF,
        handle_admin_reply
    ))
    application.add_handler(CallbackQueryHandler(admin_action_handler, pattern="^admin:"))
    
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