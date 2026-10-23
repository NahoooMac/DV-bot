
import logging
import re
from typing import Dict, Any, List
import asyncio  # <-- Import asyncio
import psycopg2 # <-- Import psycopg2
from telegram import User # <-- Import User type

# Telegram imports
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)
from telegram.constants import ParseMode

# Local module imports
from config import (
    logger, converter, IMAGE_ENHANCER_BOT_URL, KEYS_TO_PRESERVE_AFTER_FORM,
    DV_MAX_BYTES, DV_MIN_PX, DV_MAX_PX, DV_ASPECT_TOLERANCE,
    CHAPA_ENABLED, DV_SERVICE_FEE
)
from states import * # Import all states
from text import get_text, format_summary
from admin_handlers import forward_to_admin, get_db_connection # <-- Import get_db_connection
from photo_validator import validate_dv_photo_and_store # Import validator
from chapa_client import initialize_chapa_transaction, verify_chapa_transaction

# --- Helper Functions (for this file) ---

def get_main_menu_keyboard(context: ContextTypes.DEFAULT_TYPE) -> ReplyKeyboardMarkup:
    """Returns the main menu keyboard in the user's language."""
    keyboard = [
        [KeyboardButton(f"📋 {get_text('new_form_button', context)}")],
        [KeyboardButton(f"🗂️ {get_text('my_data_title', context)}")],
        [
            KeyboardButton("🌍 Language"),
            KeyboardButton("❓ Help"),
        ],
        [
            KeyboardButton("💬 Support"),
            KeyboardButton("🗑️ Clear Data")
        ],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_photo_enhancer_markup(context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    """Returns an inline keyboard with the photo enhancer link."""
    keyboard = [
        [
            InlineKeyboardButton(
                get_text('photo_enhance_button', context),
                url=IMAGE_ENHANCER_BOT_URL
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def is_valid_email(email: str) -> bool:
    """Basic email format check."""
    return re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email) is not None

def is_valid_phone(phone: str) -> bool:
    """Basic phone format check (must start with +)."""
    return re.match(r"^\+\d{10,15}$", phone) is not None

# --- NEW: Helper function to save user data ---
def _upsert_user_pg(user: User):
    """
    Saves new user to DB or updates last_seen on existing user.
    This is a synchronous function to be run in a thread.
    """
    query = """
    INSERT INTO users (user_id, first_name, last_name, username, language_code, first_seen, last_seen)
    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
    ON CONFLICT (user_id) DO UPDATE SET
        last_name = EXCLUDED.last_name,
        first_name = EXCLUDED.first_name,
        username = EXCLUDED.username,
        language_code = EXCLUDED.language_code,
        last_seen = NOW();
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (
                    user.id,
                    user.first_name,
                    user.last_name,
                    user.username,
                    user.language_code
                ))
            conn.commit()
        logger.info(f"Upserted user {user.id} in DB.")
    except Exception as e:
        logger.error(f"Failed to upsert user {user.id}: {e}", exc_info=True)


# --- Top-Level Commands ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Smarter /start command.
    Shows main menu if user exists, otherwise starts language selection.
    """
    if update.effective_chat and update.effective_chat.type != "private":
        return ConversationHandler.END

    # --- ADD THIS: Log the user every time they /start ---
    user = update.effective_user
    if user:
        try:
            await asyncio.to_thread(_upsert_user_pg, user)
        except Exception as e:
            logger.error(f"Failed to upsert user {user.id} in start: {e}")
    # ---------------------------------------------------
    
    if "language" in context.user_data:
        return await start_main_menu(update, context)
    else:
        return await start_reset(update, context)

async def start_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Clears all user data and restarts from language selection. (Used for /cleardata)"""
    if update.effective_chat and update.effective_chat.type != "private":
        return ConversationHandler.END
    user = update.effective_user
    
    # --- ADD THIS: Log the user every time they reset ---
    if user:
        try:
            await asyncio.to_thread(_upsert_user_pg, user)
        except Exception as e:
            logger.error(f"Failed to upsert user {user.id} in start_reset: {e}")
    # ---------------------------------------------------

    if context.user_data:
        context.user_data.clear()
        
    logger.info(f"User {user.id} started/cleared the bot.")

    keyboard = [
        [KeyboardButton("English 🇬🇧"), KeyboardButton("Amharic 🇪🇹")],
        [KeyboardButton("Oromiffa 🇪🇹"), KeyboardButton("Tigrigna 🇪🇹")],
    ]
    await update.message.reply_text(
        get_text("welcome", context), # 'welcome' is language-agnostic here
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return SELECT_LANGUAGE

# --- (The rest of your handlers.py file is unchanged) ---

async def language_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected language and moves to the main menu."""
    text = update.message.text
    lang = "en" # default
    if "English" in text:
        lang = "en"
    elif "Amharic" in text:
        lang = "am"
    elif "Oromiffa" in text:
        lang = "om"
    elif "Tigrigna" in text:
        lang = "ti"
    
    context.user_data["language"] = lang
    
    await update.message.reply_text(get_text("lang_selected_pre", context))
    await update.message.reply_text(get_text("lang_selected", context))
    await update.message.reply_text(
        get_text("start_new_form", context),
        reply_markup=get_main_menu_keyboard(context)
    )
    return ConversationHandler.END

async def start_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Shows the main menu."""
    if update.effective_chat and update.effective_chat.type != "private":
        return ConversationHandler.END

    if "language" not in context.user_data:
        return await start_reset(update, context)
        
    await update.message.reply_text(
        get_text("main_menu_prompt", context),
        reply_markup=get_main_menu_keyboard(context)
    )
    return ConversationHandler.END

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Displays the multi-part help message."""
    if update.effective_chat and update.effective_chat.type != "private":
        return ConversationHandler.END

    if "language" not in context.user_data:
        return await start_reset(update, context)
    
    if context.user_data.get('form_step') is not None:
        context.user_data['pending_action'] = 'show_help'
        keyboard = [
            [InlineKeyboardButton(get_text("confirm_cancel_yes", context), callback_data="soft_cancel_yes")],
            [InlineKeyboardButton(get_text("confirm_cancel_no", context), callback_data="soft_cancel_no")]
        ]
        await update.message.reply_text(
            get_text("warning_mid_form", context),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CONFIRM_CANCEL_FORM
        
    await update.message.reply_text(get_text("help_title", context))
    await update.message.reply_text(get_text("help_1", context))
    await update.message.reply_text(get_text("help_2", context))
    await update.message.reply_text(get_text("help_3", context))
    await update.message.reply_text(get_text("help_4", context))
    await update.message.reply_text(get_text("help_5", context))
    await update.message.reply_text(get_text("help_6", context))
    await update.message.reply_text(get_text("help_7", context))
    return ConversationHandler.END

async def show_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Displays the support message."""
    if update.effective_chat and update.effective_chat.type != "private":
        return ConversationHandler.END

    if "language" not in context.user_data:
        return await start_reset(update, context)
        
    if context.user_data.get('form_step') is not None:
        context.user_data['pending_action'] = 'show_support'
        keyboard = [
            [InlineKeyboardButton(get_text("confirm_cancel_yes", context), callback_data="soft_cancel_yes")],
            [InlineKeyboardButton(get_text("confirm_cancel_no", context), callback_data="soft_cancel_no")]
        ]
        await update.message.reply_text(
            get_text("warning_mid_form", context),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CONFIRM_CANCEL_FORM
        
    await update.message.reply_text(get_text("support_text", context))
    return ConversationHandler.END

async def show_my_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Displays a summary of the user's submitted data."""
    if update.effective_chat and update.effective_chat.type != "private":
        return ConversationHandler.END

    if "language" not in context.user_data:
        return await start_reset(update, context)
        
    if context.user_data.get('form_step') is not None:
        context.user_data['pending_action'] = 'show_my_data'
        keyboard = [
            [InlineKeyboardButton(get_text("confirm_cancel_yes", context), callback_data="soft_cancel_yes")],
            [InlineKeyboardButton(get_text("confirm_cancel_no", context), callback_data="soft_cancel_no")]
        ]
        await update.message.reply_text(
            get_text("warning_mid_form", context),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CONFIRM_CANCEL_FORM
        
    if "surname" not in context.user_data:
        await update.message.reply_text(get_text("my_data_none", context))
        return ConversationHandler.END

    try:
        summary = format_summary(context.user_data)
        await update.message.reply_text(get_text("my_data_title", context))
        await update.message.reply_text(summary, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Failed to generate summary for /mydata: {e}", exc_info=True)
        await update.message.reply_text("Error generating summary. Please contact /support.")
        
    return ConversationHandler.END

async def clear_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles /cleardata command. 
    Clears all form data and restarts the form from the first question,
    but keeps the user's language.
    """
    if update.effective_chat and update.effective_chat.type != "private":
        return ConversationHandler.END
    lang = context.user_data.get("language")
    user_obj = context.user_data.get("user_object")
    
    context.user_data.clear()
    
    if lang:
        context.user_data["language"] = lang
    else:
        await update.message.reply_text(get_text("data_cleared", context))
        return await start_reset(update, context)
        
    if user_obj:
        context.user_data["user_object"] = user_obj
        
    logger.info(f"User {update.effective_user.id} cleared data mid-form, restarting form.")
    
    await update.message.reply_text(get_text("form_restarted", context))
    
    keyboard = [
        [KeyboardButton(get_text("gender_male", context))],
        [KeyboardButton(get_text("gender_female", context))],
    ]
    await update.message.reply_text(
        get_text("ask_gender", context),
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    
    context.user_data['form_step'] = GET_GENDER
    return GET_GENDER

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    logger.info(f"User {update.effective_user.id} cancelled the conversation.")
    temp_keys = ['form_step', 'children_total', 'children_collected', 'current_child', 'pending_action']
    for key in temp_keys:
        context.user_data.pop(key, None)

    await update.message.reply_text(
        get_text("form_cancelled", context),
        reply_markup=get_main_menu_keyboard(context)
    )
    return ConversationHandler.END

async def handle_soft_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the 'Yes/No' inline buttons for soft cancel."""
    query = update.callback_query
    await query.answer()
    
    pending_action = context.user_data.pop('pending_action', None)
    
    if query.data == "soft_cancel_no":
        await query.edit_message_text(text=get_text("continuing_form", context))
        return context.user_data.get('form_step')

    # User clicked "Yes, cancel" — clear form state
    await query.edit_message_text(text=get_text("form_cancelled", context))
    
    temp_keys = ['form_step', 'children_total', 'children_collected', 'current_child']
    for key in temp_keys:
        context.user_data.pop(key, None)
    
    # After cancelling, send a follow-up based on what the user originally wanted.
    # We send via the bot since we can't re-use Message-only handlers with a callback query.
    chat_id = query.message.chat_id
    if pending_action == 'show_help':
        await context.bot.send_message(chat_id=chat_id, text=get_text("help_title", context))
        await context.bot.send_message(chat_id=chat_id, text=get_text("help_1", context))
        await context.bot.send_message(chat_id=chat_id, text=get_text("help_2", context))
        await context.bot.send_message(chat_id=chat_id, text=get_text("help_3", context))
        await context.bot.send_message(chat_id=chat_id, text=get_text("help_4", context))
        await context.bot.send_message(chat_id=chat_id, text=get_text("help_5", context))
        await context.bot.send_message(chat_id=chat_id, text=get_text("help_6", context))
        await context.bot.send_message(chat_id=chat_id, text=get_text("help_7", context))
    elif pending_action == 'show_my_data':
        if "surname" not in context.user_data:
            await context.bot.send_message(chat_id=chat_id, text=get_text("my_data_none", context))
        else:
            try:
                from text import format_summary
                summary = format_summary(context.user_data)
                await context.bot.send_message(chat_id=chat_id, text=get_text("my_data_title", context))
                await context.bot.send_message(chat_id=chat_id, text=summary, parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                logger.error(f"Failed to generate summary in soft cancel: {e}", exc_info=True)
                await context.bot.send_message(chat_id=chat_id, text="Error generating summary. Please contact /support.")
    elif pending_action == 'show_support':
        await context.bot.send_message(chat_id=chat_id, text=get_text("support_text", context))
    else:
        from handlers import get_main_menu_keyboard
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_text("main_menu_prompt", context),
            reply_markup=get_main_menu_keyboard(context)
        )
    return ConversationHandler.END

# --- DV Form Conversation Handlers ---

async def start_new_form(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the DV form. Clears old data and asks for Gender."""
    if update.effective_chat and update.effective_chat.type != "private":
        return ConversationHandler.END

    if "language" not in context.user_data:
        return await start_reset(update, context)
        
    user = update.effective_user
    if user:
        try:
            await asyncio.to_thread(_upsert_user_pg, user)
        except Exception as e:
            logger.error(f"Failed to upsert user {user.id} in start_new_form: {e}")
    
    temp_keys = ['form_step', 'children_total', 'children_collected', 'current_child', 'pending_action']
    for key in temp_keys:
        context.user_data.pop(key, None)
    
    context.user_data["user_object"] = user.to_dict() if user else {}
    
    await update.message.reply_text(get_text("form_restarted", context))
    
    keyboard = [
        [KeyboardButton(get_text("gender_male", context))],
        [KeyboardButton(get_text("gender_female", context))],
    ]
    await update.message.reply_text(
        get_text("ask_gender", context),
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    context.user_data['form_step'] = GET_GENDER
    return GET_GENDER

# --- Step 1-2: Gender & Name ---
async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == get_text("gender_female", context):
        context.user_data["gender"] = "Female"
    else:
        context.user_data["gender"] = "Male"
        
    await update.message.reply_text(
        get_text("ask_surname", context),
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data['form_step'] = GET_SURNAME
    return GET_SURNAME

async def get_surname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["surname"] = update.message.text.upper()
    await update.message.reply_text(
        get_text("ask_given_name", context),
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data['form_step'] = GET_GIVEN_NAME
    return GET_GIVEN_NAME

async def get_given_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["given_name"] = update.message.text.upper()
    await update.message.reply_text(
        get_text("ask_middle_name", context),
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data['form_step'] = GET_MIDDLE_NAME
    return GET_MIDDLE_NAME

async def get_middle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text.lower() == 'none':
        context.user_data["middle_name"] = "None"
    else:
        context.user_data["middle_name"] = text.upper()
        
    if converter is None:
        await update.message.reply_text("Date converter is not installed. Skipping date steps.")
        context.user_data['dob_ec'] = 'N/A'
        context.user_data['dob_gc'] = 'N/A'
        await update.message.reply_text(get_text("ask_birth_city", context))
        context.user_data['form_step'] = GET_BIRTH_CITY
        return GET_BIRTH_CITY
        
    await update.message.reply_text(get_text("ask_dob", context))
    context.user_data['form_step'] = GET_DOB
    return GET_DOB

# --- Step 3-4: DOB & Birthplace ---
async def get_dob(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        date_str = update.message.text.strip()
        dd, mm, yyyy = map(int, date_str.split('/'))
        gc_date = converter.to_gregorian(yyyy, mm, dd)
        
        context.user_data['dob_ec'] = date_str
        context.user_data['dob_gc'] = gc_date.strftime('%d/%m/%Y')
        
        await update.message.reply_text(get_text("ask_birth_city", context))
        context.user_data['form_step'] = GET_BIRTH_CITY
        return GET_BIRTH_CITY
        
    except (ValueError, TypeError, AttributeError) as e:
        logger.warning(f"Invalid date input for GET_DOB: {update.message.text} - Error: {e}")
        await update.message.reply_text(get_text("invalid_date", context))
        return GET_DOB

async def get_birth_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["birth_city"] = update.message.text.upper()
    await update.message.reply_text(get_text("ask_birth_country", context))
    context.user_data['form_step'] = GET_BIRTH_COUNTRY
    return GET_BIRTH_COUNTRY

async def get_birth_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["birth_country"] = update.message.text.upper()
    
    keyboard = [
        [KeyboardButton(get_text("yes", context))],
        [KeyboardButton(get_text("no", context))],
    ]
    await update.message.reply_text(
        get_text("ask_eligibility_confirm", context),
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    context.user_data['form_step'] = GET_ELIGIBILITY_CONFIRM
    return GET_ELIGIBILITY_CONFIRM

# --- Step 5: Eligibility ---
async def get_eligibility_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == get_text("yes", context):
        context.user_data["eligibility_country"] = context.user_data["birth_country"].upper()
        
        keyboard = [
            [KeyboardButton(get_text("yes", context))],
            [KeyboardButton(get_text("no", context))],
        ]
        await update.message.reply_text(
            get_text("ask_passport_confirm", context),
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        context.user_data['form_step'] = GET_PASSPORT_CONFIRM
        return GET_PASSPORT_CONFIRM
    else:
        await update.message.reply_text(
            get_text("ask_eligibility_country", context),
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data['form_step'] = GET_ELIGIBILITY_COUNTRY
        return GET_ELIGIBILITY_COUNTRY

async def get_eligibility_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["eligibility_country"] = update.message.text.upper()
    
    keyboard = [
        [KeyboardButton(get_text("yes", context))],
        [KeyboardButton(get_text("no", context))],
    ]
    await update.message.reply_text(
        get_text("ask_passport_confirm", context),
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    context.user_data['form_step'] = GET_PASSPORT_CONFIRM
    return GET_PASSPORT_CONFIRM

# --- Step 6: Passport ---
async def get_passport_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == get_text("yes", context):
        await update.message.reply_text(
            get_text("ask_passport_number", context),
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data['form_step'] = GET_PASSPORT_NUMBER
        return GET_PASSPORT_NUMBER
    else:
        await update.message.reply_text(
            get_text("ask_applicant_photo", context),
            reply_markup=get_photo_enhancer_markup(context)
        )
        context.user_data['form_step'] = GET_APPLICANT_PHOTO
        return GET_APPLICANT_PHOTO

async def get_passport_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["passport_number"] = update.message.text.upper()
    await update.message.reply_text(get_text("ask_passport_issuance", context))
    context.user_data['form_step'] = GET_PASSPORT_ISSUANCE
    return GET_PASSPORT_ISSUANCE

async def get_passport_issuance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["passport_issuance"] = update.message.text.upper()
    if converter is None:
        await update.message.reply_text("Date converter not installed. Skipping date steps.")
        context.user_data['passport_expiration_ec'] = 'N/A'
        context.user_data['passport_expiration_gc'] = 'N/A'
        await update.message.reply_text(
            get_text("ask_applicant_photo", context),
            reply_markup=get_photo_enhancer_markup(context)
        )
        context.user_data['form_step'] = GET_APPLICANT_PHOTO
        return GET_APPLICANT_PHOTO
        
    await update.message.reply_text(get_text("ask_passport_expiration", context))
    context.user_data['form_step'] = GET_PASSPORT_EXPIRATION
    return GET_PASSPORT_EXPIRATION

async def get_passport_expiration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        date_str = update.message.text.strip()
        dd, mm, yyyy = map(int, date_str.split('/'))
        gc_date = converter.to_gregorian(yyyy, mm, dd)
        
        context.user_data['passport_expiration_ec'] = date_str
        context.user_data['passport_expiration_gc'] = gc_date.strftime('%d/%m/%Y')
        
        await update.message.reply_text(
            get_text("ask_applicant_photo", context),
            reply_markup=get_photo_enhancer_markup(context)
        )
        context.user_data['form_step'] = GET_APPLICANT_PHOTO
        return GET_APPLICANT_PHOTO
        
    except (ValueError, TypeError, AttributeError) as e:
        logger.warning(f"Invalid date input for GET_PASSPORT_EXPIRATION: {update.message.text} - Error: {e}")
        await update.message.reply_text(get_text("invalid_date", context))
        return GET_PASSPORT_EXPIRATION

# --- Step 7-8: Photo & Contact ---

async def get_applicant_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the applicant's photo by passing it to the advanced validator.
    """
    return await validate_dv_photo_and_store(
        update, 
        context, 
        user_data_key="applicant_photo_id", 
        next_state=GET_CURRENT_RESIDENCE
    )

async def get_current_residence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["current_residence"] = update.message.text.upper()
    await update.message.reply_text(get_text("ask_email", context))
    context.user_data['form_step'] = GET_EMAIL
    return GET_EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = update.message.text.strip()
    if not is_valid_email(email):
        await update.message.reply_text(get_text("invalid_email", context))
        context.user_data['form_step'] = GET_EMAIL
        return GET_EMAIL
        
    context.user_data["email"] = email
    await update.message.reply_text(get_text("ask_phone", context))
    context.user_data['form_step'] = GET_PHONE
    return GET_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.text.strip()
    if not is_valid_phone(phone):
        await update.message.reply_text(get_text("invalid_phone", context))
        return GET_PHONE
        
    context.user_data["phone"] = phone
    
    keyboard = [
        [KeyboardButton(get_text("edu_primary", context))],
        [KeyboardButton(get_text("edu_high_school_no_diploma", context))],
        [KeyboardButton(get_text("edu_high_school_degree", context))],
        [KeyboardButton(get_text("edu_vocational", context))],
        [KeyboardButton(get_text("edu_some_university", context))],
        [KeyboardButton(get_text("edu_bachelor", context))],
        [KeyboardButton(get_text("edu_master", context))],
        [KeyboardButton(get_text("edu_doctorate", context))],
    ]
    await update.message.reply_text(
        get_text("ask_education", context),
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    context.user_data['form_step'] = GET_EDUCATION
    return GET_EDUCATION

# --- Step 9-10: Education & Marital Status ---
async def get_education(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["education"] = update.message.text
    
    keyboard = [
        [KeyboardButton(get_text("status_single", context))],
        [KeyboardButton(get_text("status_married_non_us", context))],
        [KeyboardButton(get_text("status_married_us", context))],
        [KeyboardButton(get_text("status_divorced", context))],
        [KeyboardButton(get_text("status_widowed", context))],
        [KeyboardButton(get_text("status_separated", context))],
    ]
    await update.message.reply_text(
        get_text("ask_marital_status", context),
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    context.user_data['form_step'] = GET_MARITAL_STATUS
    return GET_MARITAL_STATUS

async def get_marital_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    context.user_data["marital_status"] = text
    
    if text in [get_text("status_married_non_us", context), get_text("status_married", context)]:
        await update.message.reply_text(
            get_text("ask_spouse_surname", context),
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['form_step'] = GET_SPOUSE_SURNAME
        return GET_SPOUSE_SURNAME
    elif text == get_text("status_married_us", context):
        await update.message.reply_text(
            get_text("spouse_is_us_citizen_note", context),
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            get_text("ask_children_count", context),
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data['form_step'] = GET_CHILDREN_COUNT
        return GET_CHILDREN_COUNT
    else:
        await update.message.reply_text(
            get_text("ask_children_count", context),
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data['form_step'] = GET_CHILDREN_COUNT
        return GET_CHILDREN_COUNT

# --- Step 11: Spouse Details ---
async def get_spouse_surname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["spouse_surname"] = update.message.text.upper()
    await update.message.reply_text(
        get_text("ask_spouse_given_name", context),
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data['form_step'] = GET_SPOUSE_GIVEN_NAME
    return GET_SPOUSE_GIVEN_NAME

async def get_spouse_given_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["spouse_given_name"] = update.message.text.upper()
    await update.message.reply_text(
        get_text("ask_spouse_middle_name", context),
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data['form_step'] = GET_SPOUSE_MIDDLE_NAME
    return GET_SPOUSE_MIDDLE_NAME

async def get_spouse_middle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text.lower() == 'none':
        context.user_data["spouse_middle_name"] = "None"
    else:
        context.user_data["spouse_middle_name"] = text.upper()
        
    keyboard = [
        [KeyboardButton(get_text("gender_male", context))],
        [KeyboardButton(get_text("gender_female", context))],
    ]
    await update.message.reply_text(
        get_text("ask_spouse_gender", context),
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    context.user_data['form_step'] = GET_SPOUSE_GENDER
    return GET_SPOUSE_GENDER

async def get_spouse_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == get_text("gender_female", context):
        context.user_data["spouse_gender"] = "Female"
    else:
        context.user_data["spouse_gender"] = "Male"
        
    if converter is None:
        await update.message.reply_text("Date converter not installed. Skipping date steps.")
        context.user_data['spouse_dob_ec'] = 'N/A'
        context.user_data['spouse_dob_gc'] = 'N/A'
        await update.message.reply_text(
            get_text("ask_spouse_birth_city", context),
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data['form_step'] = GET_SPOUSE_BIRTH_CITY
        return GET_SPOUSE_BIRTH_CITY

    await update.message.reply_text(
        get_text("ask_spouse_dob", context),
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data['form_step'] = GET_SPOUSE_DOB
    return GET_SPOUSE_DOB

async def get_spouse_dob(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        date_str = update.message.text.strip()
        dd, mm, yyyy = map(int, date_str.split('/'))
        gc_date = converter.to_gregorian(yyyy, mm, dd)
        
        context.user_data['spouse_dob_ec'] = date_str
        context.user_data['spouse_dob_gc'] = gc_date.strftime('%d/%m/%Y')
        
        await update.message.reply_text(get_text("ask_spouse_birth_city", context))
        context.user_data['form_step'] = GET_SPOUSE_BIRTH_CITY
        return GET_SPOUSE_BIRTH_CITY
        
    except (ValueError, TypeError, AttributeError) as e:
        logger.warning(f"Invalid date input for GET_SPOUSE_DOB: {update.message.text} - Error: {e}")
        await update.message.reply_text(get_text("invalid_date", context))
        return GET_SPOUSE_DOB

async def get_spouse_birth_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["spouse_birth_city"] = update.message.text.upper()
    await update.message.reply_text(get_text("ask_spouse_birth_country", context))
    context.user_data['form_step'] = GET_SPOUSE_BIRTH_COUNTRY
    return GET_SPOUSE_BIRTH_COUNTRY

async def get_spouse_birth_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["spouse_birth_country"] = update.message.text.upper()
    await update.message.reply_text(
        get_text("ask_spouse_photo", context),
        reply_markup=get_photo_enhancer_markup(context)
    )
    context.user_data['form_step'] = GET_SPOUSE_PHOTO
    return GET_SPOUSE_PHOTO

async def get_spouse_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the spouse's photo by passing it to the advanced validator.
    """
    return await validate_dv_photo_and_store(
        update, 
        context, 
        user_data_key="spouse_photo_id", 
        next_state=GET_CHILDREN_COUNT
    )

# --- Step 12: Children ---
async def get_children_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        count = int(update.message.text.strip())
        if count < 0:
            raise ValueError("Count cannot be negative")
            
        context.user_data['children_total'] = count
        context.user_data['children_collected'] = 0
        context.user_data['children'] = []
        context.user_data['current_child'] = {}
        
        if count == 0:
            context.user_data['form_step'] = GET_FINAL_CONFIRM
            summary = format_summary(context.user_data)
            await update.message.reply_text(get_text('final_summary_title', context))
            await update.message.reply_text(summary, parse_mode=ParseMode.MARKDOWN)
            
            keyboard = [
                [KeyboardButton(get_text('confirm', context))],
                [KeyboardButton(get_text('edit_restart', context))],
            ]
            await update.message.reply_text(
                get_text('final_summary_confirm', context),
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            )
            return GET_FINAL_CONFIRM
        else:
            await update.message.reply_text(
                get_text('ask_child_surname', context).format(num=1),
                reply_markup=ReplyKeyboardRemove()
            )
            context.user_data['form_step'] = GET_CHILD_INFO
            return GET_CHILD_INFO

    except (ValueError, TypeError):
        await update.message.reply_text(f"{get_text('invalid_text', context)} Please enter a number (e.g., 0, 1, 2).")
        return GET_CHILDREN_COUNT

async def get_child_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """This single function handles all steps of child info collection."""
    current_child = context.user_data.get('current_child', {})
    collected_count = context.user_data.get('children_collected', 0)
    total_count = context.user_data.get('children_total', 0)
    child_num_str = str(collected_count + 1)
    
    # --- Photo Handler Logic ---
    if update.message.photo:
        if 'birth_country' not in current_child:
            await update.message.reply_text(get_text('invalid_photo', context))
            return GET_CHILD_INFO

        if 'photo_id' in current_child:
            await update.message.reply_text(get_text('fallback', context))
            return GET_CHILD_INFO
        
        temp_key_for_validator = f"temp_child_{child_num_str}_photo"
        
        validation_result = await validate_dv_photo_and_store(
            update,
            context,
            user_data_key=temp_key_for_validator,
            next_state=GET_CHILD_INFO
        )
        
        if validation_result != GET_CHILD_INFO:
            return GET_CHILD_INFO

        stored_file_id = context.user_data.pop(temp_key_for_validator, None)
        if not stored_file_id:
             await update.message.reply_text("An error occurred saving the photo after validation. Please try uploading it again.")
             return GET_CHILD_INFO

        current_child['photo_id'] = stored_file_id
        
        context.user_data['children'].append(current_child)
        context.user_data['children_collected'] += 1
        
        if context.user_data['children_collected'] == total_count:
            context.user_data['form_step'] = GET_FINAL_CONFIRM
            await update.message.reply_text(get_text('all_children_done', context))
            
            try:
                summary = format_summary(context.user_data)
                await update.message.reply_text(get_text('final_summary_title', context))
                await update.message.reply_text(summary, parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                logger.error(f"Failed to generate summary in get_child_info: {e}", exc_info=True)
                await update.message.reply_text("Error generating summary. Please contact /support.")
                return await cancel(update, context)

            keyboard = [
                [KeyboardButton(get_text('confirm', context))],
                [KeyboardButton(get_text('edit_restart', context))],
            ]
            await update.message.reply_text(
                get_text('final_summary_confirm', context),
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            )
            return GET_FINAL_CONFIRM
        else:
            context.user_data['current_child'] = {} # Reset for next child
            next_child_num_str = str(context.user_data['children_collected'] + 1)
            await update.message.reply_text(
                get_text('ask_child_surname', context).format(num=next_child_num_str),
                reply_markup=ReplyKeyboardRemove()
            )
            return GET_CHILD_INFO
    
    # --- Text Handler Logic ---
    if not update.message.text:
        await update.message.reply_text(get_text('invalid_text', context))
        return GET_CHILD_INFO

    try:
        text_input = update.message.text.strip()
        if 'surname' not in current_child:
            current_child['surname'] = text_input.upper()
            await update.message.reply_text(get_text('ask_child_given_name', context).format(num=child_num_str))
        
        elif 'given_name' not in current_child:
            current_child['given_name'] = text_input.upper()
            await update.message.reply_text(get_text('ask_child_middle_name', context).format(num=child_num_str))

        elif 'middle_name' not in current_child:
            if text_input.lower() == 'none':
                current_child['middle_name'] = "None"
            else:
                current_child['middle_name'] = text_input.upper()
                
            keyboard = [
                [KeyboardButton(get_text("gender_male", context))],
                [KeyboardButton(get_text("gender_female", context))],
            ]
            await update.message.reply_text(
                get_text('ask_child_gender', context).format(num=child_num_str),
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            )

        elif 'gender' not in current_child:
            if text_input == get_text("gender_female", context):
                current_child['gender'] = "Female"
            else:
                current_child['gender'] = "Male"

            if converter is None:
                await update.message.reply_text("Date converter not installed. Skipping date steps.")
                current_child['dob_ec'] = 'N/A'
                current_child['dob_gc'] = 'N/A'
                await update.message.reply_text(
                    get_text('ask_child_birth_city', context).format(num=child_num_str),
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                await update.message.reply_text(
                    get_text('ask_child_dob', context).format(num=child_num_str),
                    reply_markup=ReplyKeyboardRemove()
                )

        elif 'dob_ec' not in current_child:
            date_str = text_input
            dd, mm, yyyy = map(int, date_str.split('/'))
            gc_date = converter.to_gregorian(yyyy, mm, dd)
            
            current_child['dob_ec'] = date_str
            current_child['dob_gc'] = gc_date.strftime('%d/%m/%Y')
            
            await update.message.reply_text(get_text('ask_child_birth_city', context).format(num=child_num_str))

        elif 'birth_city' not in current_child:
            current_child['birth_city'] = text_input.upper()
            await update.message.reply_text(get_text('ask_child_birth_country', context).format(num=child_num_str))

        elif 'birth_country' not in current_child:
            current_child['birth_country'] = text_input.upper()
            await update.message.reply_text(
                get_text('ask_child_photo', context).format(num=child_num_str),
                reply_markup=get_photo_enhancer_markup(context)
            )
        
        else:
            await update.message.reply_text(
                get_text('invalid_photo', context),
                reply_markup=get_photo_enhancer_markup(context)
            )

    except Exception as e:
        if 'dob_ec' not in current_child and 'gender' in current_child:
            logger.warning(f"Invalid date input for GET_CHILD_INFO (DOB): {update.message.text} - Error: {e}")
            await update.message.reply_text(get_text('invalid_date', context))
        else:
            logger.warning(f"Error in GET_CHILD_INFO (text): {e}", exc_info=True)
            await update.message.reply_text(get_text('invalid_text', context))
        return GET_CHILD_INFO

    context.user_data['current_child'] = current_child
    return GET_CHILD_INFO

# --- Step 13-14: Confirmation & Payment ---
async def get_final_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == get_text('edit_restart', context):
        return await start_new_form(update, context)
    
    context.user_data['form_step'] = GET_PAYMENT_SCREENSHOT
    
    user = update.effective_user
    user_id = user.id if user else 0
    email = context.user_data.get("email", "")
    first_name = context.user_data.get("given_name", "")
    last_name = context.user_data.get("surname", "")
    phone = context.user_data.get("phone", "")

    # Check if Chapa is enabled and try to initialize checkout
    chapa_init = None
    if CHAPA_ENABLED:
        try:
            chapa_init = await initialize_chapa_transaction(
                user_id=user_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone,
                amount=DV_SERVICE_FEE
            )
        except Exception as e:
            logger.error(f"Failed to initialize Chapa transaction: {e}")

    # Combine payment instructions into one single message as requested
    payment_text = (
        f"{get_text('form_complete_payment', context).strip()}\n\n"
        f"{get_text('payment_details', context).strip()}\n\n"
        f"{get_text('payment_ask_screenshot', context).strip()}"
    )

    keyboard = []
    if chapa_init and chapa_init.get("success"):
        checkout_url = chapa_init["checkout_url"]
        tx_ref = chapa_init["tx_ref"]
        context.user_data["chapa_tx_ref"] = tx_ref

        keyboard.append([
            InlineKeyboardButton("💳 Pay with Chapa (Telebirr, CBE...)", web_app=WebAppInfo(url=checkout_url))
        ])
        keyboard.append([
            InlineKeyboardButton("🔄 Verify Payment", callback_data=f"chapa:verify:{tx_ref}")
        ])

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    await update.message.reply_text(
        payment_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_PAYMENT_SCREENSHOT


async def handle_chapa_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles Chapa verification and manual switch inline callbacks."""
    query = update.callback_query
    if not query:
        return GET_PAYMENT_SCREENSHOT
        
    data = query.data or ""
    
    if data.startswith("chapa:verify:"):
        tx_ref = data.split("chapa:verify:", 1)[1].strip()
        await query.answer("🔍 Checking payment status with Chapa...", show_alert=False)
        
        try:
            res = await verify_chapa_transaction(tx_ref)
        except Exception as e:
            logger.error(f"Chapa verification error: {e}")
            res = {"success": False, "error": str(e)}

        if res.get("success"):
            context.user_data["payment_method"] = "chapa"
            context.user_data["payment_tx_ref"] = tx_ref
            context.user_data["payment_status"] = "verified"
            
            await query.edit_message_text(
                "✅ <b>Payment Verified!</b>\n\nYour payment via Chapa has been successfully confirmed.",
                parse_mode=ParseMode.HTML
            )
            
            # Forward submission to admin
            await forward_to_admin(context)
            
            # Send completion success to user
            await query.message.reply_text(
                get_text('form_complete_success', context),
                reply_markup=get_main_menu_keyboard(context)
            )
            
            # Clear temporary form fields
            temp_keys = ['form_step', 'children_total', 'children_collected', 'current_child', 'pending_action', 'chapa_tx_ref']
            for key in temp_keys:
                context.user_data.pop(key, None)
            
            preserved_data = {}
            for key in KEYS_TO_PRESERVE_AFTER_FORM:
                if key in context.user_data:
                    preserved_data[key] = context.user_data[key]
            
            context.user_data.clear()
            context.user_data.update(preserved_data)
            
            return ConversationHandler.END
        else:
            status_desc = res.get("status", "pending")
            await query.answer(
                f"⏳ Payment not yet completed (status: {status_desc}).\nPlease complete the payment on Chapa first, then tap Verify.",
                show_alert=True
            )
            return GET_PAYMENT_SCREENSHOT

    elif data == "chapa:manual":
        await query.answer()
        payment_text = (
            f"{get_text('form_complete_payment', context).strip()}\n\n"
            f"{get_text('payment_details', context).strip()}\n\n"
            f"{get_text('payment_ask_screenshot', context).strip()}"
        )
        await query.message.reply_text(
            payment_text,
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_PAYMENT_SCREENSHOT
        
    return GET_PAYMENT_SCREENSHOT

async def get_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = None
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
    elif update.message.document:
        photo_file = await update.message.document.get_file()

    if not photo_file:
        await update.message.reply_text(get_text("invalid_photo", context))
        return GET_PAYMENT_SCREENSHOT

    context.user_data["payment_screenshot_id"] = photo_file.file_id
    
    await update.message.reply_text(get_text('payment_received', context))
    
    await forward_to_admin(context)
    
    await update.message.reply_text(
        get_text('form_complete_success', context),
        reply_markup=get_main_menu_keyboard(context)
    )
    
    temp_keys = ['form_step', 'children_total', 'children_collected', 'current_child', 'pending_action']
    for key in temp_keys:
        context.user_data.pop(key, None)
    
    preserved_data = {}
    for key in KEYS_TO_PRESERVE_AFTER_FORM:
        if key in context.user_data:
            preserved_data[key] = context.user_data[key]
    
    context.user_data.clear()
    context.user_data.update(preserved_data)
    
    return ConversationHandler.END

# --- Fallback Handlers ---
async def invalid_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles text when a photo is expected, or other invalid text."""
    current_state = context.user_data.get('form_step')
    
    if current_state in [GET_GENDER, GET_SPOUSE_GENDER]:
         logger.warning(f"Patching invalid_text_handler call for state {current_state}.")
         if current_state == GET_GENDER:
             return await get_gender(update, context)
         else:
             return await get_spouse_gender(update, context)
    
    if current_state == GET_PAYMENT_SCREENSHOT:
        return await get_final_confirm(update, context)

    if current_state in [GET_APPLICANT_PHOTO, GET_SPOUSE_PHOTO]:
        await update.message.reply_text(
            get_text('invalid_photo', context),
            reply_markup=get_photo_enhancer_markup(context)
        )
        return current_state
    
    if current_state == GET_DOB or current_state == GET_PASSPORT_EXPIRATION or current_state == GET_SPOUSE_DOB:
         await update.message.reply_text(get_text('invalid_date', context))
         return current_state
         
    if current_state == GET_EMAIL:
         await update.message.reply_text(get_text('invalid_email', context))
         return current_state

    if current_state == GET_PHONE:
         await update.message.reply_text(get_text('invalid_phone', context))
         return current_state
         
    if current_state == GET_CHILDREN_COUNT:
         await update.message.reply_text(f"{get_text('invalid_text', context)} Please enter a number (e.g., 0, 1, 2).")
         return current_state

    await update.message.reply_text(get_text('invalid_text', context))
    if current_state is None:
        return await start_main_menu(update, context)
    return current_state

async def invalid_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles a photo when text is expected."""
    current_state = context.user_data.get('form_step')
    
    if current_state == GET_APPLICANT_PHOTO:
         logger.warning(f"Routing photo directly to get_applicant_photo for state {current_state}.")
         return await get_applicant_photo(update, context)
    if current_state == GET_SPOUSE_PHOTO:
         logger.warning(f"Routing photo directly to get_spouse_photo for state {current_state}.")
         return await get_spouse_photo(update, context)
    if current_state == GET_CHILD_INFO:
         logger.warning(f"Routing photo directly to get_child_info for state {current_state}.")
         return await get_child_info(update, context)
    if current_state == GET_PAYMENT_SCREENSHOT:
         logger.warning(f"Routing photo directly to get_payment_screenshot for state {current_state}.")
         return await get_payment_screenshot(update, context)
    
    await update.message.reply_text(
        "⚠️ You sent a photo, but we are currently waiting for your answer to the question above.\n"
        "Please type your answer, or type /cancel to go back to the main menu."
    )
    if current_state is None:
        return await start_main_menu(update, context)
    return current_state


async def handle_top_level_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles photos or image documents uploaded when NOT inside the DV registration form.
    Provides instant validation feedback and prompts the user to start a new form.
    """
    if not update.message or (update.effective_chat and update.effective_chat.type != "private"):
        return

    # Check language
    if "language" not in context.user_data:
        await start_reset(update, context)
        return

    photo_obj = None
    if update.message.photo:
        photo_obj = update.message.photo[-1]
    elif update.message.document:
        doc = update.message.document
        if (doc.mime_type and doc.mime_type.startswith("image/")) or (doc.file_name and doc.file_name.lower().endswith(('.jpg', '.jpeg', '.png'))):
            photo_obj = doc

    if not photo_obj:
        await update.message.reply_text(
            get_text("fallback", context),
            reply_markup=get_main_menu_keyboard(context)
        )
        return

    file_size = getattr(photo_obj, "file_size", None)
    width = getattr(photo_obj, "width", None)
    height = getattr(photo_obj, "height", None)

    issues = []
    if file_size and file_size > DV_MAX_BYTES:
        issues.append(f"File size ({round(file_size/1024)} KB) exceeds 240 KB limit.")
    if width and height:
        if width < DV_MIN_PX or height < DV_MIN_PX or width > DV_MAX_PX or height > DV_MAX_PX:
            issues.append(f"Dimensions ({width}×{height}) should be between 600×600 and 1200×1200.")
        if abs(width - height) > max(1, DV_ASPECT_TOLERANCE * width):
            issues.append("Photo must be square (1:1 aspect ratio).")

    if issues:
        feedback = "\n".join(f"• {issue}" for issue in issues)
        msg = (
            f"📸 <b>Photo Received!</b>\n\n"
            f"⚠️ <b>DV Photo Check:</b>\n{feedback}\n\n"
            f"To begin your official DV lottery application, tap <b>📋 New Form</b> below."
        )
    else:
        msg = (
            f"📸 <b>Photo Received!</b>\n\n"
            f"✅ This photo meets basic DV lottery dimensions and size requirements!\n\n"
            f"To use this photo and submit your official DV lottery application, please tap <b>📋 New Form</b> below."
        )

    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(context)
    )