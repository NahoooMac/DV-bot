import re
from typing import Dict, Any, List
from telegram.ext import ContextTypes, filters
from config import logger # Import logger from config

# --- Translation Dictionary ---
translations: Dict[str, Dict[str, str]] = {
    "en": {
        "welcome": "Welcome! 👋 Please select your language.",
        "lang_selected_pre": "Language set to English 🇬🇧.",
        "lang_selected": "You can change this later using the 🌍 /language button.\n\nAll data you enter *must be in English letters* (A, B, C...) for the DV application, even if the questions are in another language.",
        "start_new_form": "Please click 📝 New Form to begin.",
        "new_form_button": "New Form", # New key for the button
        "form_restarted": "Your application form has been restarted.",
        "main_menu_prompt": "You are at the main menu. What would you like to do?",
        "fallback": "Sorry, I didn't understand that. Please use the main menu or type /start to begin.",
        "data_cleared": "Your data has been cleared. Please select your language to start over.",
        "ask_gender": "1️⃣ Great, let's start.\n\nWhat is your gender? 👤",
        "gender_male": "👨 Male",
        "gender_female": "👩 Female",
        "gender_other": "🤝 Other / Prefer not to say",
        "ask_surname": "2️⃣ Please enter your full legal name.\n\n*Surname (Last/Family Name):*",
        "ask_given_name": "*Given Name (First Name):*",
        "ask_middle_name": "*Middle Name:*\n(If you have no middle name, please type `None`)",
        "ask_dob": "3️⃣ What is your Date of Birth?\n\nPlease enter it in the *Ethiopian Calendar* (e.g., `20/08/1990`).",
        "ask_birth_city": "4️⃣ What is your City of Birth?",
        "ask_birth_country": "And your Country of Birth?",
        "ask_eligibility_confirm": "5️⃣ Is your country of eligibility the same as your country of birth?",
        "yes": "✅ Yes",
        "no": "❌ No",
        "ask_eligibility_country": "Please specify your country of eligibility:",
        "ask_passport_confirm": "6️⃣ Do you want to add your passport details? (Optional)",
        "ask_passport_number": "Please enter your Passport Number:",
        "ask_passport_issuance": "Country of Issuance (where the passport was issued):",
        "ask_passport_expiration": "Expiration Date:\n\nPlease enter it in the *Ethiopian Calendar* (e.g., `10/01/2020`).",
        "ask_applicant_photo": "7️⃣ Please upload your recent passport-style photo.\n\nIt *must* be:\n- In color\n- Clear, with a plain white or off-white background\n- No filters, no glasses, no shadows\n- Face centered and looking at the camera",
        "photo_enhance_button": "✨ Enhance my picture",
        "ask_email": "8️⃣ What is your email address?",
        "ask_phone": "And your phone number? (Please include country code, e.g., `+251...`)",
        "ask_education": "9️⃣ What is your highest level of education?",
        "edu_primary": "🏫 Primary school only",
        "edu_high_school_no_diploma": "📚 High school, no diploma",
        "edu_high_school_degree": "🎒 High school degree",
        "edu_vocational": "🔧 Vocational / Technical school",
        "edu_some_university": "🎓 Some university courses",
        "edu_bachelor": "🎓 Bachelor’s degree",
        "edu_master": "🏅 Master’s degree",
        "edu_doctorate": "🏆 Doctorate",
        "ask_marital_status": "🔟 What is your marital status?",
        "status_single": "💍 Single / Unmarried",
        "status_married": "👫 Married",
        "status_divorced": "📝 Divorced",
        "status_widowed": "🕊️ Widowed",
        "status_separated": "⚖️ Legally Separated",
        "ask_spouse_surname": "Got it. Please enter your *spouse's* full name.\n\n*Spouse's Surname (Last/Family Name):*",
        "ask_spouse_given_name": "*Spouse's Given Name (First Name):*",
        "ask_spouse_middle_name": "*Spouse's Middle Name:*\n(If no middle name, type `None`)",
        "ask_spouse_dob": "What is your spouse's Date of Birth?\n\nPlease enter it in the *Ethiopian Calendar* (e.g., `20/08/1990`).",
        "ask_spouse_birth_country": "What is your spouse's Country of Birth?",
        "ask_spouse_photo": "Please upload your *spouse's* passport-style photo.",
        "ask_children_count": "1️⃣1️⃣ How many *unmarried* children under the age of 21 do you have?\n\n(Enter `0` if none)",
        "ask_child_surname": "Please provide info for *Child {num}*.\n\n*Child's Surname (Last/Family Name):*",
        "ask_child_given_name": "*Child's Given Name (First Name):*",
        "ask_child_middle_name": "*Child's Middle Name:*\n(If no middle name, type `None`)",
        "ask_child_dob": "Child {num}'s Date of Birth:\n\nPlease enter it in the *Ethiopian Calendar* (e.g., `20/08/2015`).",
        "ask_child_birth_country": "Child {num}'s Country of Birth:",
        "ask_child_photo": "Please upload *Child {num}'s* passport-style photo.",
        "all_children_done": "All children's data collected.",
        "final_summary_title": "1️⃣2️⃣ Amazing! Please review your information.",
        "final_summary_confirm": "Is all this information correct?",
        "confirm": "✅ Yes, Confirm & Submit",
        "edit_restart": "✏️ No, Edit (Restart form)", # This is for the final confirm
        "form_complete_payment": "Thank you!\n\nTo complete your submission, there is a *350 Birr* service fee.\n\nPlease pay to one of the following accounts:",
        "payment_details": """
*CBE (Commercial Bank)*
`1000181234281`

*Telebirr*
`0937105764`
        """,
        "payment_ask_screenshot": "After paying, please upload a *screenshot* of the payment receipt here.",
        "payment_received": "Processing...",
        "form_complete_success": "🎉 All set! Your information has been recorded.\n\nWe will review your application and the payment. You will be notified of the next steps. Thank you for using our DV Assistant!",
        "my_data_title": "My Submitted Data", # Changed for button matching
        "my_data_none": "You have not submitted any data yet. Click 📝 New Form to start.",
        "support_text": "For support, please contact @nahoomac.",
        
        # --- FIX: ENGLISH HELP TEXT ---
        "help_title": "--- *Help Guide* ---",
        "help_1": "Welcome! This guide will show you how to apply for the U.S. Diversity Visa (DV) Lottery and submit your application through this bot.",
        "help_2": "Step 1: Start the Application\nClick the “📝 New Form” button. The bot will ask you for your gender first, then your personal information step-by-step.",
        "help_3": "Step 2: Provide Personal Information\nFollow the bot’s questions: full name, date of birth, city & country of birth, and country of eligibility. Answer carefully.",
        "help_4": "Step 3: Upload a Photo\nUpload a recent passport-style photo when asked. It must be clear, plain background, and your face must be visible.",
        "help_5": "Step 4: Provide Contact Information\nEnter your email and phone number so the bot can contact you for updates.",
        "help_6": "Step 5: Review and Submit\nAfter all questions are answered, review your information carefully and press “Confirm” to submit.",
        "help_7": "Step 6: Finished\n🎉 All done! Your application is submitted. You will be notified of the next steps.",
        # --- END FIX ---

        "invalid_text": "That doesn't look right. Please try again.",
        "invalid_photo": "I'm waiting for a photo. Please upload an image.",
        "invalid_date": "Invalid date format. Please use DD/MM/YYYY (e.g., `20/08/1990`) in the *Ethiopian Calendar*.",
        "invalid_email": "That doesn't look like a valid email. Please try again (e.g., `user@example.com`).",
        "invalid_phone": "That doesn't look like a valid phone number. Please include the country code (e.g., `+251...`).",
        "admin_pdf_caption": "Here is your registration document from the admin. Please save it.",
        # New "cancel confirm" text
        "warning_mid_form": "You’re in the middle of filling a form. Do you want to cancel?",
        "confirm_cancel_yes": "✅ Yes, cancel the form",
        "confirm_cancel_no": "↩️ No, continue filling",
        "continuing_form": "👍 Okay — continuing where you left off.",
        "form_cancelled": "✅ Form cancelled. You are back at the main menu.",
        "form_cancelled_and_cleared": "Form cancelled and all data cleared. Please select your language to start over.",
    },
    "am": {
        "welcome": "እንኳን ደህና መጡ! 👋 እባክዎ ቋንቋዎን ይምረጡ።",
        "lang_selected_pre": "ቋንቋ ወደ አማርኛ 🇪🇹 ተቀይሯል።",
        "lang_selected": "ይህንን በኋላ 🌍 /language የሚለውን ቁልፍ በመጠቀም መቀየር ይችላሉ።\n\nጥያቄዎቹ በአማርኛ ቢሆኑም፣ ለDV ማመልከቻ የሚያስገቡት መረጃ *በሙሉ በእንግሊዝኛ ፊደላት* (A, B, C...) መሆን አለበት።",
        "start_new_form": "ለመጀመር እባክዎ 📝 New Form የሚለውን ይጫኑ።",
        "form_restarted": "የማመልከቻ ቅጽዎ እንደገና ተጀምሯል።",
        "main_menu_prompt": "ዋናው ምናሌ ላይ ነዎት። ምን ማድረግ ይፈልጋሉ?",
        "fallback": "ይቅርታ፣ አልገባኝም። እባክዎ ዋናውን ምናሌ ይጠቀሙ ወይም ለመጀመር /start ይተይቡ።",
        "data_cleared": "መረጃዎ ተሰርዟል። እንደገና ለመጀመር እባክዎ ቋንቋዎን ይምረጡ።",
        "new_form_button": "New Form",
        "my_data_button": "My Submitted Data",
        "language_button": "/language (ቋንቋ)",
        "help_button": "/help (እርዳታ)",
        "support_button": "/support (ድጋፍ)",
        "clear_data_button": "/cleardata (መረጃን አጽዳ)",
        "ask_gender": "1️⃣ በጣም ጥሩ፣ እንጀምር።\n\nጾታዎ ምንድነው? 👤",
        "gender_male": "👨 ወንድ",
        "gender_female": "👩 ሴት",
        "gender_other": "🤝 ሌላ / መናገር አልፈልግም",
        "ask_surname": "2️⃣ እባክዎ ሙሉ ህጋዊ ስምዎን ያስገቡ።\n\n*የአያት ስም (የቤተሰብ ስም):*",
        "ask_given_name": "*የመጀመሪያ ስም (የራስ ስም):*",
        "ask_middle_name": "*የአባት ስም:*\n(የአባት ስም ከሌለዎት `None` ብለው ይተይቡ)",
        "ask_dob": "3️⃣ የትውልድ ቀንዎ መቼ ነው?\n\nእባክዎ *በኢትዮጵያ ካሌንደር* ያስገቡ (ለምሳሌ፡ `20/08/1990`)።",
        "ask_birth_city": "4️⃣ የትውልድ ከተማዎ የት ነው?",
        "ask_birth_country": "የትውልድ ሀገርዎስ?",
        "ask_eligibility_confirm": "5️⃣ የውድድር ብቁ የሆኑበት ሀገር ከትውልድ ሀገርዎ ጋር ተመሳሳይ ነው?",
        "yes": "✅ አዎ",
        "no": "❌ አይ",
        "ask_eligibility_country": "እባክዎ የብቁነት ሀገርዎን ይግለጹ:",
        "ask_passport_confirm": "6️⃣ የፓስፖርት ዝርዝሮችዎን ማከል ይፈልጋሉ? (አስገዳጅ ያልሆነ)",
        "ask_passport_number": "እባክዎ የፓስፖርት ቁጥርዎን ያስገቡ:",
        "ask_passport_issuance": "ፓስፖርቱ የተሰጠበት ሀገር:",
        "ask_passport_expiration": "ፓስፖርቱ የሚያበቃበት ቀን:\n\nእባክዎ *በኢትዮጵያ ካሌንደር* ያስገቡ (ለምሳሌ፡ `10/01/2020`)።",
        "ask_applicant_photo": "7️⃣ እባክዎ የቅርብ ጊዜ ፓስፖርት-ስታይል ፎቶዎን ይስቀሉ።\n\n*መሆን አለበት*:\n- ከለር ፎቶ\n- ግልጽ፣ በነጭ ጀርባ\n- ያለ ፊልተር፣ ያለ መነጽር፣ ያለ ጥላ\n- ፊትዎ መሃል ላይ ሆኖ ካሜራውን የሚመለከት",
        "photo_enhance_button": "✨ ፎቶዬን አሻሽል",
        "ask_email": "8️⃣ የእርስዎ ኢሜይል አድራሻ ምንድነው?",
        "ask_phone": "ስልክ ቁጥርዎስ? (እባክዎ የሀገር ኮድ ያካትቱ፣ ለምሳሌ፡ `+251...`)",
        "ask_education": "9️⃣ የእርስዎ ከፍተኛ የትምህርት ደረጃ ምንድነው?",
        "edu_primary": "🏫 የመጀመሪያ ደረጃ ትምህርት ብቻ",
        "edu_high_school_no_diploma": "📚 ሁለተኛ ደረጃ ትምህርት ቤት፣ ዲፕሎማ የለም",
        "edu_high_school_degree": "🎒 የሁለተኛ ደረጃ ትምህርት ቤት ዲግሪ",
        "edu_vocational": "🔧 የሙያ / ቴክኒክ ትምህርት ቤት",
        "edu_some_university": "🎓 የተወሰኑ የዩኒቨርሲቲ ኮርሶች",
        "edu_bachelor": "🎓 የባችለር ዲግሪ",
        "edu_master": "🏅 የማስተርስ ዲግሪ",
        "edu_doctorate": "🏆 ዶክትሬት",
        "ask_marital_status": "🔟 የጋብቻ ሁኔታዎ ምንድነው?",
        "status_single": "💍 ያላገባ / ያላገባች",
        "status_married": "👫 ያገባ / ያገባች",
        "status_divorced": "📝 የተፋታ / የተፋታች",
        "status_widowed": "🕊️ በሞት የተለየ / የተለየች",
        "status_separated": "⚖️ በህግ የተለየ",
        "ask_spouse_surname": "ገባኝ። እባክዎ *የትዳር ጓደኛዎን* ሙሉ ስም ያስገቡ።\n\n*የትዳር ጓደኛ የአያት ስም:*",
        "ask_spouse_given_name": "*የትዳር ጓደኛ የመጀመሪያ ስም:*",
        "ask_spouse_middle_name": "*የትዳር ጓደኛ የአባት ስም:*\n(`None` ብለው ይተይቡ)",
        "ask_spouse_dob": "የትዳር ጓደኛዎ የትውልድ ቀን መቼ ነው?\n\nእባክዎ *በኢትዮጵያ ካሌንደር* ያስገቡ (ለምሳሌ፡ `20/08/1990`)።",
        "ask_spouse_birth_country": "የትዳር ጓደኛዎ የትውልድ ሀገር ምንድነው?",
        "ask_spouse_photo": "እባክዎ *የትዳር ጓደኛዎን* ፓስፖርት-ስታይል ፎቶ ይስቀሉ።",
        "ask_children_count": "1️⃣1️⃣ ዕድሜያቸው ከ21 ዓመት በታች የሆኑ *ያላገቡ* ልጆች ስንት ናቸው?\n\n(ከሌለ `0` ያስገቡ)",
        "ask_child_surname": "እባክዎ *የልጅ {num}* መረጃ ያስገቡ።\n\n*የልጁ የአያት ስም:*",
        "ask_child_given_name": "*የልጁ የመጀመሪያ ስም:*",
        "ask_child_middle_name": "*የልጁ የአባት ስም:*\n(`None` ብለው ይተይቡ)",
        "ask_child_dob": "የልጅ {num} የትውልድ ቀን:\n\n*በኢትዮጵያ ካሌንደር* (ለምሳሌ፡ `20/08/2015`)።",
        "ask_child_birth_country": "የልጅ {num} የትውልድ ሀገር:",
        "ask_child_photo": "እባክዎ *የልጅ {num}* ፓስፖርት-ስታይል ፎቶ ይስቀሉ።",
        "all_children_done": "የልጆቹ መረጃ በሙሉ ተሰብስቧል።",
        "final_summary_title": "1️⃣2️⃣ በጣም ጥሩ! እባክዎ መረጃዎን ይገምግሙ።",
        "final_summary_confirm": "ይህ ሁሉ መረጃ ትክክል ነው?",
        "confirm": "✅ አዎ፣ አረጋግጥ",
        "edit_restart": "✏️ አይ፣ አስተካክል (ቅጹን እንደገና ያስጀምራል)",
        "form_complete_payment": "አመሰግናለሁ!\n\nማስገባቱን ለማጠናቀቅ *350 ብር* የአገልግሎት ክፍያ አለ።\n\nእባክዎ ከሚከተሉት መለያዎች በአንዱ ይክፈሉ:",
        "payment_details": """
*CBE (የኢትዮጵያ ንግድ ባንክ)*
`1000181234281`

*Telebirr (ቴሌብር)*
`0937105764`
        """,
        "payment_ask_screenshot": "ከከፈሉ በኋላ፣ እባክዎ የክፍያ ደረሰኝ *ስክሪንሹት* እዚህ ይስቀሉ።",
        "payment_received": "በማስኬድ ላይ...",
        "form_complete_success": "🎉 ሁሉም ተጠናቋል! መረጃዎ ተመዝግቧል።\n\nማመልከቻዎን እና ክፍያዎን እንገመግማለን። ቀጣይ እርምጃዎችን እናሳውቅዎታለን። ረዳታችንን ስለተጠቀሙ እናመሰግናለን!",
        "my_data_title": "ያስገቡት መረጃ ይኸውና:",
        "my_data_none": "እስካሁን ምንም መረጃ አላስገቡም። ለመጀመር 📝 New Form ይጫኑ።",
        "support_text": "ለድጋፍ፣ እባክዎ @nahoomac ያግኙ።",
        
        # --- FIX: AMHARIC HELP TEXT ---
        "help_title": "--- *የእርዳታ መመሪያ* ---",
        "help_1": "AM: እንኳን ደህና መጡ! ይህ መመሪያ እንዴት ማመልከቻ ማስገባት እና በዚህ ቦት የDV ሎተሪ መተግበሪያ እንዴት እንደሚፈጽም ይገልጻል።",
        "help_2": "Step 1: Start the Application\nAM: “📝 New Form” አዝራር ይጫኑ። ቦቱ መጀመሪያ ፆታዎን ይጠይቃል ከዚያም የግል መረጃዎን ደረጃ በደረጃ ይሰብስባል።",
        "help_3": "Step 2: Provide Personal Information\nAM: ቦቱ የሚጠይቁትን ይሙሉ: ሙሉ ስም፣ የትውልድ ቀን፣ የትውልድ ከተማ እና ሀገር፣ እና የምትማር ሀገር በጥንቃቄ ይሙሉ።",
        "help_4": "Step 3: Upload a Photo\nAM: በቦት ሲጠይቅ የቅርብ ጊዜ ፓስፖርት ቅርጸ-ምስል ያስገቡ። ፊትዎ ግልጽ ሊኖር እና በማንኛውም መልኩ የተለያዩ አልሆነም።",
        "help_5": "Step 4: Provide Contact Information\nAM: ኢሜልና ስልክ ቁጥርዎን ያስገቡ ቦቱ ለማሳወቅ እና ለአዳዲስ ማስታወቂያዎች ይጠቀሙበታል።",
        "help_6": "Step 5: Review and Submit\nAM: ሁሉንም ጥያቄዎች ከሞሉት በኋላ መረጃዎን በጥንቃቄ ይገምግሙ እና “አረጋግጥ” ይጫኑ።",
        "help_7": "Step 6: Finished\nAM: 🎉 ሁሉም ተጠናቀቀ! መተግበሪያዎን አስገቡ። ሚናዎች በሚቀጥለው ይሰጡሃል።",
        # --- END FIX ---
        
        "invalid_text": "ትክክል አይመስልም። እባክዎ እንደገና ይሞክሩ።",
        "invalid_photo": "ፎቶ እየጠበቅኩ ነው። እባክዎ ምስል ይስቀሉ።",
        "invalid_date": "የቀን ቅርጸት ልክ አይደለም። እባክዎ DD/MM/YYYY (ለምሳሌ፡ `20/08/1990`) *በኢትዮጵያ ካሌንደር* ይጠቀሙ።",
        "invalid_email": "ትክክለኛ ኢሜይል አይመስልም። እባክዎ እንደገና ይሞክሩ (ለምሳሌ፡ `user@example.com`)።",
        "invalid_phone": "ትክክለኛ ስልክ ቁጥር አይመስልም። እባክዎ የሀገር ኮድ ያካትቱ (ለምሳሌ፡ `+251...`)።",
        "admin_pdf_caption": "ከአስተዳዳሪው የተላከልዎት የመመዝገቢያ ሰነድ ይኸውና።",
        "soft_cancel_prompt": "ቅጹን በመሙላት መካከል ላይ ነዎት። ለመሰረዝ እና ወደ ዋናው ምናሌ ለመመለስ እርግጠኛ ነዎት?",
        "soft_cancel_yes": "✅ አዎ፣ ሰርዝ",
        "soft_cancel_no": "↩️ አይ፣ ቀጥል",
        "soft_cancel_confirm": "ቅጹ ተሰርዟል። ወደ ዋናው ምናሌ ተመልሰዋል።",
        "soft_cancel_decline": "እሺ፣ ካቆሙበት ይቀጥሉ።",
    },
    "om": {
        "welcome": "Baga nagaan dhuftan! 👋 Maaloo afaan keessan filadhaa.",
        "lang_selected_pre": "Afaan Oromiffaatti 🇪🇹 jijjiirameera.",
        "lang_selected": "Kana booda yeroo barbaaddetti 🌍 /language tuquun jijjiiruu dandeessa.\n\nGaaffileen Afaan Oromootiin yoo dhiyaatan illee, ragaan ati galchitu *hundi qubee Afaan Ingiliffaatiin* (A, B, C...) ta'uu qaba.",
        "start_new_form": "Maaloo jalqabuuf 📝 New Form tuqi.",
        "form_restarted": "Unkaan iyyannoo kee irra deebiin jalqabeera.",
        "main_menu_prompt": "Menyuu ijoo irra jirta. Maaltu akka siif godhamu barbaadda?",
        "fallback": "Dhiifama, siif hin galle. Maaloo menyuu ijoo fayyadami ykn jalqabuuf /start galchi.",
        "data_cleared": "Ragaan kee haqameera. Irra deebiin jalqabuuf maaloo afaan kee filadhaa.",
        "new_form_button": "New Form",
        "my_data_button": "My Submitted Data",
        "language_button": "/language (Afaan)",
        "help_button": "/help (Gargaarsa)",
        "support_button": "/support (Deeggarsa)",
        "clear_data_button": "/cleardata (Ragaa Haqaa)",
        "ask_gender": "1️⃣ Gaarii dha, haa jalqabnu.\n\nSaalli kee maali? 👤",
        "gender_male": "👨 Dhiira",
        "gender_female": "👩 Dubartii",
        "gender_other": "🤝 Bira / Hin himu",
        "ask_surname": "2️⃣ Maaloo maqaa kee guutuu seera qabeessa galchi.\n\n*Maqaa Akaakayyuu (Maqaa Maatii):*",
        "ask_given_name": "*Maqaa Jalqabaa (Maqaa Mataa):*",
        "ask_middle_name": "*Maqaa Gidduu (Maqaa Abbaa):*\n(Maqaa gidduu yoo hin qabaanne, `None` galchi)",
        "ask_dob": "3️⃣ Guyyaan dhaloota kee yoomi?\n\nMaaloo *Kalandara Itoophiyaatiin* galchi (fkn, `20/08/1990`).",
        "ask_birth_city": "4️⃣ Magaalaan dhaloota kee eessa?",
        "ask_birth_country": "Biyyi dhaloota keehoo?",
        "ask_eligibility_confirm": "5️⃣ Biyyi ulaagaa dorgommichaaf ittiin guuttu biyya dhaloota kee wajjin tokkoo?",
        "yes": "✅ Eeyyee",
        "no": "❌ Lakkii",
        "ask_eligibility_country": "Maaloo biyya ulaagaa ittiin guuttu ibsi:",
        "ask_passport_confirm": "6️⃣ Odeeffannoo paaspoortii kee galchuu barbaaddaa? (Filatamaa)",
        "ask_passport_number": "Maaloo Lakkoofsa Paaspoortii kee galchi:",
        "ask_passport_issuance": "Biyya Paaspoortiin itti kenname:",
        "ask_passport_expiration": "Guyyaa itti xumuramu:\n\nMaaloo *Kalandara Itoophiyaatiin* galchi (fkn, `10/01/2020`).",
        "ask_applicant_photo": "7️⃣ Maaloo suuraa kee kan dhiheenya kan paaspoortii fe'i.\n\n*Kan ta'uu qabu*:\n- Kan halluu qabu\n- Ifa kan ta'e, dugdi isaa adii ykn adii-diimaa\n- Filteerii, kooblee ijaa, gaaddidduu kan hin qabne\n- Fuulli kee gidduutti gara kaameraatti kan ilaalu",
        "photo_enhance_button": "✨ Suuraa koo fooyyessi",
        "ask_email": "8️⃣ Teessoon imeelii kee maali?",
        "ask_phone": "Lakkoofsi bilbilaa keehoo? (Maaloo koodii biyyaa dabalii, fkn, `+251...`)",
        "ask_education": "9️⃣ Sadarkaan barnootaa kee isa ol'aanaa maali?",
        "edu_primary": "🏫 Barnoota sadarkaa 1ffaa qofa",
        "edu_high_school_no_diploma": "📚 Mana barumsaa sadarkaa 2ffaa, diippiloomaa hin qabu",
        "edu_high_school_degree": "🎒 Diippiloomaa mana barumsaa sadarkaa 2ffaa",
        "edu_vocational": "🔧 Mana barumsaa Ogummaa / Teeknikaa",
        "edu_some_university": "🎓 Koorsoota Yuunivarsiitii muraasa",
        "edu_bachelor": "🎓 Digirii Baacheelarii",
        "edu_master": "🏅 Digirii Maasterii",
        "edu_doctorate": "🏆 Digirii Doktoreetii",
        "ask_marital_status": "🔟 Haalli gaa'elaa kee maali?",
        "status_single": "💍 Kan hin fuune / Hin heerumne",
        "status_married": "👫 Kan fuudhe / Heerumte",
        "status_divorced": "📝 Kan hiike / Hiikte",
        "status_widowed": "🕊️ Kan irraa du'e / duute",
        "status_separated": "⚖️ Seeraan kan addaan bahe",
        "ask_spouse_surname": "Hubadheera. Maaloo maqaa guutuu *haadha/abbaa warraa* kee galchi.\n\n*Maqaa Akaakayyuu haadha/abbaa warraa:*",
        "ask_spouse_given_name": "*Maqaa Jalqabaa haadha/abbaa warraa:*",
        "ask_spouse_middle_name": "*Maqaa Gidduu haadha/abbaa warraa:*\n(`None` galchi)",
        "ask_spouse_dob": "Guyyaan dhaloota haadha/abbaa warraa kee yoomi?\n\nMaaloo *Kalandara Itoophiyaatiin* galchi (fkn, `20/08/1990`).",
        "ask_spouse_birth_country": "Biyyi dhaloota haadha/abbaa warraa kee eessa?",
        "ask_spouse_photo": "Maaloo suuraa paaspoortii *haadha/abbaa warraa* kee fe'i.",
        "ask_children_count": "1️⃣1️⃣ Ijoollee *kan hin fuune/hin heerumne* umuriin isaanii waggaa 21 gadii meeqa qabda?\n\n(Yoo hin qabaanne `0` galchi)",
        "ask_child_surname": "Maaloo odeeffannoo *Mucaa {num}* galchi.\n\n*Maqaa Akaakayyuu mucaa:*",
        "ask_child_given_name": "*Maqaa Jalqabaa mucaa:*",
        "ask_child_middle_name": "*Maqaa Gidduu mucaa:*\n(`None` galchi)",
        "ask_child_dob": "Guyyaan dhaloota Mucaa {num}:\n\n*Kalandara Itoophiyaatiin* (fkn, `20/08/2015`).",
        "ask_child_birth_country": "Biyyi dhaloota Mucaa {num}:",
        "ask_child_photo": "Maaloo suuraa paaspoortii *Mucaa {num}* fe'i.",
        "all_children_done": "Ragaan ijoollee hunda walitti qabameera.",
        "final_summary_title": "1️⃣2️⃣ Gaariidha! Maaloo odeeffannoo kee mirkaneeffadhu.",
        "final_summary_confirm": "Odeeffannoon kun hundi sirriidhaa?",
        "confirm": "✅ Eeyyee, Mirkaneessi",
        "edit_restart": "✏️ Lakkii, Sirreessi (Unka haaraya jalqabsiisa)",
        "form_complete_payment": "Galatoomi!\n\nGalmee kee xumuruuf kaffaltii tajaajilaa *Birrii 350* jira.\n\nMaaloo herrega armaan gadii keessaa tokkotti kaffali:",
        "payment_details": """
*CBE (Baankii Daldalaa)*
`1000181234281`

*Telebirr (ቴሌብር)*
`0937105764`
        """,
        "payment_ask_screenshot": "Erga kaffalte booda, maaloo *suuraa nagahee* (screenshot) kaffaltii kee as irratti fe'i.",
        "payment_received": "Adeemsa irra jira...",
        "form_complete_success": "🎉 Hunduu xumurameera! Odeeffannoon kee galmaa'eera.\n\nIyyannoo fi kaffaltii kee ni ilaalla. Tarkaanfii itti aanu si beeksifna. Gargaaraa keenya fayyadamuu keetiif galatoomi!",
        "my_data_title": "Odeeffannoo ati galchite kunooti:",
        "my_data_none": "Hanga ammaatti ragaa homaatuu hin galchine. Jalqabuuf 📝 New Form tuqi.",
        "support_text": "Gargaarsaaf, maaloo @nahoomacqunnami.",

        # --- FIX: OROMIFFA HELP TEXT ---
        "help_title": "--- *Qajeelfama Gargaarsaa* ---",
        "help_1": "OR: Baga nagaan dhuftan! Kuni gorsa itti fayyadamuu fi galmee DV Lottery USA karaa bot kanaa akka galchitan isinitti agarsiisa.",
        "help_2": "Step 1: Start the Application\nOR: “📝 New Form” tuqaa. Botichi dura saala kee si gaafata, itti aansuun immoo odeeffannoo dhuunfaa kee sadarkaa sadarkaan si gaafata.",
        "help_3": "Step 2: Provide Personal Information\nOR: Gaafilee botii hordofaa: maqaa guutuu, guyyaa dhalootaa, magaalaa fi biyya dhalootaa, akkasumas biyya filannoo. Sirriitti deebisi.",
        "help_4": "Step 3: Upload a Photo\nOR: Suuraa haaraya paaspoortii kee fe’i. Suuraa ifaa fi halluu salphaa qabaachuu qaba, fuulli kee mul’achuu qaba.",
        "help_5": "Step 4: Provide Contact Information\nOR: Imeelii fi bilbila kee galchi; botichi odeeffannoo fi haala haaraa siif dabarsa.",
        "help_6": "Step 5: Review and Submit\nOR: Gaafilee hunda deebistee booda, odeeffannoo kee sirriitti ilaali, “Confirm” tuqaa.",
        "help_7": "Step 6: Finished\nOR: 🎉 Hundumtuu xumurame! Galmee kee ergameera. Odeeffannoo itti aanu ni argatta.",
        # --- END FIX ---

        "invalid_text": "Sirrii miti. Maaloo irra deebi'ii yaali.",
        "invalid_photo": "Suuraan eegaa jira. Maaloo suuraa fe'i.",
        "invalid_date": "Unki guyyaa sirrii miti. Maaloo DD/MM/YYYY (fkn, `20/08/1990`) *Kalandara Itoophiyaatiin* fayyadami.",
        "invalid_email": "Kun imeelii sirrii hin fakkaatu. Maaloo irra deebi'ii yaali (fkn, `user@example.com`).",
        "invalid_phone": "Kun lakkoofsa bilbilaa sirrii hin fakkaatu. Maaloo koodii biyyaa dabalii (fkn, `+251...`).",
        "admin_pdf_caption": "Kunooti sanada galmee kee kan bulchaa irraa ergame.",
        "soft_cancel_prompt": "Unka guutaa jirta. Dhuguma haqxee gara menyuu ijoo deebi'uu barbaaddaa?",
        "soft_cancel_yes": "✅ Eeyyee, haqi",
        "soft_cancel_no": "↩️ Lakkii, itti fufi",
        "soft_cancel_confirm": "Unkaan haqameera. Gara menyuu ijoo deebiteetta.",
        "soft_cancel_decline": "Tole, bakka dhiisterraa itti fufi.",
    },
    "ti": {
        "welcome": "እንቋዕ ብደሓን መጻእኹም! 👋 በጃኹም ቋንቋኹም ምረጹ።",
        "lang_selected_pre": "ቋንቋ ናብ ትግርኛ 🇪🇹 ተቐይሩ።",
        "lang_selected": "እዚ ጸኒሕኩም 🌍 /language ዝብል ብምጥዋቕ ክትቅይርዎ ትኽእሉ ኢኹም።\n\nሕቶታት ብትግርኛ እንተኾኑ'ኳ፣ ንDV መመልከቲ እትእትውዎ ሓበሬታ *ብሙሉኡ ብፊደላት እንግሊዝኛ* (A, B, C...) ክኸውን ኣለዎ።",
        "start_new_form": "ንምጅማር በጃኹም 📝 New Form ጠውቑ።",
        "form_restarted": "መመልከቲ ቅጥዕኹም ዳግማይ ተጀሚሩ።",
        "main_menu_prompt": "ኣብ ቀንዲ መርዝር ኣለኹም። እንታይ ክንገብረਲኩም ትደልዩ?",
        "fallback": "ይቕረታ፣ ኣይተረድኣንን። በጃኹም ነቲ ቀንዲ መርዝር ተጠቐሙ ወይ ንምጅማር /start በሉ።",
        "data_cleared": "ሓበሬታኹም ተደምሲሱ። ዳግማይ ንምጅማር በጃኹም ቋንቋኹም ምረጹ።",
        "new_form_button": "New Form",
        "my_data_button": "My Submitted Data",
        "language_button": "/language (ቋንቋ)",
        "help_button": "/help (ሓገዝ)",
        "support_button": "/support (ድጋፍ)",
        "clear_data_button": "/cleardata (ሓበሬታ ምጽራይ)",
        "ask_gender": "1️⃣ ብጣዕሚ ጽቡቕ፣ ንጀምር።\n\nጾታኹም እንታይ እዩ? 👤",
        "gender_male": "ወዲ",
        "gender_female": "ጓል",
        "gender_other": "ካልእ / ምግላጽ ኣይደልን",
        "ask_surname": "2️⃣ በጃኹም ምሉእ ሕጋዊ ስምኩም ኣእትዉ።\n\n*ስም ስድራቤት ( ናይ መወዳእታ ስም):*",
        "ask_given_name": "*ቀዳማይ ስም ( ናይ ገዛእ ስም):*",
        "ask_middle_name": "*ማእከላይ ስም (ናይ ኣቦ ስም):*\n(ማእከላይ ስም እንተዘይብልኩም፣ `None` ኢልኩም ጸሓፉ)",
        "ask_dob": "3️⃣ ዕለተ ልደትኩም መዓስ እዩ?\n\nበጃኹም *ብኢትዮጵያዊ ኣቆጻጽራ* ኣእትዉ (ንኣብነት፡ `20/08/1990`)።",
        "ask_birth_city": "4️⃣ እትተወልድኹምላ ከተማ ኣበይ እያ?",
        "ask_birth_country": "እትተወልድኹምላ ሃገርስ?",
        "ask_eligibility_confirm": "5️⃣ ንውድድር ብቕዕቲ እትገብረኩም ሃገር ምስ እትተወልድኹምላ ሃገር ሓንቲ ድያ?",
        "yes": "እወ",
        "no": "ኣይፋልን",
        "ask_eligibility_country": "በጃኹም ነታ ብቕዕቲ እትገብረኩም ሃገር ግለጹ:",
        "ask_passport_confirm": "6️⃣ ዝርዝር ፓስፖርትኩም ከተእትዉ ትደልዩዶ? (ኣገዳሲ ኣይኮነን)",
        "ask_passport_number": "በጃኹም ቁጽሪ ፓስፖርትኩም ኣእትዉ:",
        "ask_passport_issuance": "ፓስፖርት እተዋህበላ ሃገር:",
        "ask_passport_expiration": "እቲ ፓስፖርት ዘብቅዓሉ ዕለት:\n\nበጃኹም *ብኢትዮጵያዊ ኣቆጻጽራ* ኣእትዉ (ንኣብነት፡ `10/01/2020`)።",
        "ask_applicant_photo": "7️⃣ በጃኹም ናይ ቀረባ ግዜ ናይ ፓስፖርት ዓይነት ስእልኹም ኣስገሩ።\n\n*ክኸውን ኣለዎ*:\n- ሕብሪ ዘለዎ\n- ጽሩይ፣ ድሕሪትኡ ጻዕዳ ወይ ፍኹስ ዝበለ ጻዕዳ\n- ብዘይ ፊልተር፣ ብዘይ መነጸር፣ ብዘይ ጽላሎት\n- ገጽኩም ማእከል ገይሩ ናብ ካሜራ ዝጥምት",
        "photo_enhance_button": "✨ ንስእለይ ኣመሓይሽ",
        "ask_email": "8️⃣ ኣድራሻ ኢሜይልኩም እንታይ እዩ?",
        "ask_phone": "ቁጽሪ ስልኩኹምከ? (በጃኹም መእተዊ ቁጽሪ ሃገር የካትቱ፣ ንኣብነት፡ `+251...`)",
        "ask_education": "9️⃣ ዝለዓለ ደረጃ ትምህርትኹም እንታይ እዩ?",
        "edu_primary": "ናይ መጀመርታ ደረጃ ትምህርቲ ጥራይ",
        "edu_high_school_no_diploma": "ካልኣይ ደረጃ ቤት ትምህርቲ፣ ዲፕሎማ የብለይን",
        "edu_high_school_degree": "ናይ ካልኣይ ደረጃ ቤት ትምህርቲ ዲግሪ",
        "edu_vocational": "ናይ ሞያ / ቴክኒክ ቤት ትምህርτι",
        "edu_some_university": "ገለ ናይ ዩኒቨርሲቲ ኮርሳት",
        "edu_bachelor": "ባችለር ዲግሪ",
        "edu_master": "ማስተርስ ዲግሪ",
        "edu_doctorate": "ዶክትሬት",
        "ask_marital_status": "🔟 ኩነታት መርዓኹም እንታይ እዩ?",
        "status_single": "ዘይተመርዓኹ / ዘይተመርዓወት",
        "status_married": "እተመርዓኹ / እተመርዓወት",
        "status_divorced": "እተፈትሐ / እተፈትሐት",
        "status_widowed": "ሰብኣያ ዝሞታ / ሰበይቱ ዝሞተቶ",
        "status_separated": "ብሕጊ እተፈላለየ",
        "ask_spouse_surname": "ተረዲአ። በጃኹም ምሉእ ስም *ናይ መጻምድትኹም* ኣእትዉ።\n\n*ናይ መጻምድቲ ስም ስድራቤት:*",
        "ask_spouse_given_name": "*ናይ መጻምድቲ ቀዳማይ ስም:*",
        "ask_spouse_middle_name": "*ናይ መጻምድቲ ማእከላይ ስም:*\n(`None` ኢልኩም ጸሓፉ)",
        "ask_spouse_dob": "ዕለተ ልደት መጻምድትኹም መዓስ እዩ?\n\nበጃኹም *ብኢትዮጵያዊ ኣቆጻጽራ* ኣእትዉ (ንኣብነት፡ `20/08/1990`)።",
        "ask_spouse_birth_country": "መጻምድትኹም እተወልደላ ሃገር ኣበይ እያ?",
        "ask_spouse_photo": "በጃኹም ናይ ፓስፖርት ዓይነት ስእሊ *መጻምድትኹም* ኣስገሩ።",
        "ask_children_count": "1️⃣1️⃣ ክንደይ ዕድሚኦም ትሕቲ 21 ዝኾኑ *ዘይተመርዓዉ* ቖልዑ ኣለኹም?\n\n(እንተዘይብልኩም `0` ኣእትዉ)",
        "ask_child_surname": "በጃኹም ሓበሬታ *ናይ ቆልዓ {num}* ኣእትዉ።\n\n*ናይ ቆልዓ ስም ስድራቤት:*",
        "ask_child_given_name": "*ናይ ቆልዓ ቀዳማይ ስም:*",
        "ask_child_middle_name": "*ናይ ቆልዓ ማእከላይ ስም:*\n(`None` ኢልኩም ጸሓፉ)",
        "ask_child_dob": "ዕለተ ልደት ቆልዓ {num}:\n\n*ብኢትዮጵያዊ ኣቆጻጽራ* (ንኣብነት፡ `20/08/2015`)።",
        "ask_child_birth_country": "ቆልዓ {num} እተወልደላ ሃገር:",
        "ask_child_photo": "በጃኹም ናይ ፓስፖርት ዓይነት ስእሊ *ቆልዓ {num}* ኣስገሩ።",
        "all_children_done": "ሓበሬታ ናይ ኩሎም ቆልዑ ተኣኪቡ።",
        "final_summary_title": "1️⃣2️⃣ ብጣዕሚ ጽቡቕ! በጃኹም ሓበሬታኹም ገምግሙ።",
        "final_summary_confirm": "እዚ ሓበሬታ'ዚ ኩሉ ቅኑዕ ድዩ?",
        "confirm": "እወ، ኣረጋግጽ",
        "edit_restart": "አይፋልን፣ ኣተዓራሪ (ነቲ ቅጥዒ ዳግማይ የጀምሮ)",
        "form_complete_payment": "የቐንየለይ!\n\nምስዳድኩም ንምዝዛም، ናይ ኣገልግሎት ክፍሊት *350 ብር* ኣሎ።\n\nበጃኹም ናብ ሓደ ካብ'ዞም ዝስዕቡ መሳርሒታት ክፈሉ:",
        "payment_details": """
*CBE (ንግዲ ባንኪ ኢትዮጵያ)*
`1000181234281`

*Telebirr (ቴሌብር)*
`0937105764`
        """,
        "payment_ask_screenshot": "ድሕሪ ምኽፋልኩም، በጃኹም ናይቲ ክፍሊት መረጋገጺ *ስክሪንሹት* (screenshot) ኣብዚ ኣስግሩ።",
        "payment_received": "ኣብ መስርሕ'ዩ...",
        "form_complete_success": "🎉 ኩሉ ተወዲኡ! ሓበሬታኹም ተመዝጊቡ።\n\nመመልከτιኹምን ክፍሊትኩምን ክንፍትሽ ኢና። ዝቕጽል ስጉምትታት ክንሕብረኩም ኢና። ንረዳኢና ስለ እተተጠቐምኩም የቐንየልና!",
        "my_data_title": "እዚ እቲ ዘስገድኩምዎ ሓበሬታ እዩ:",
        "my_data_none": "ክሳብ ሕጂ ዝኾነ ሓበሬታ ኣየስገድኩምን። ንምጅማር 📝 New Form ጠውቑ።",
        "support_text": "ንድጋፍ፣ በጃኹም @nahoomacርኸቡ።",

        # --- FIX: TIGRIGNA HELP TEXT ---
        "help_title": "--- *ናይ ሓገዝ መምርሒ* ---",
        "help_1": "TG: እንኳን ደሓን መጹ! ዚህ መመርያ እንተዘርከቡ ኣብ ውሽጢ ቦት እንደት መዋቅር ኣብ DV Lottery እትሰርሕ ይገልጽ።",
        "help_2": "Step 1: Start the Application\nTG: “📝 New Form” ንዕድል ጠቓሚ ኣጥፍእ! ቦት መጀመሪያ ፆታካ/ኪ ይጠይቅ ከዚያም መረጃካ/ኪ ኣብ ደረጃ ደረጃ ይሰብስባ።",
        "help_3": "Step 2: Provide Personal Information\nTG: ቦት ዝተጠየቑ ኣገልግሎት ተከታታይ ይከተሉ፡ ሙሉ ስምካ/ኪ፣ ዕለት ልደት፣ ከተማን ሃገር ልደትካ/ኪ፣ እንተኾይኑ ኣገር መምርሒካ/ኪ ኣብ ጥንቃቐ ይሙሉ።",
        "help_4": "Step 3: Upload a Photo\nTG: ሓደ ቅርጸ ፓስፖርት ፎቶ ኣስገባ እንተ ቦት ጠይቅ! ፎቶ ግልጽ ክኸውን ኣለዎ፣ ፊትካ/ኪ ክትታይ ኣለዎ።",
        "help_5": "Step 4: Provide Contact Information\nTG: ኢሜይልካ/ኪ ኣስገባ፣ ቁጽሪ ስልኪካ/ኪ ኣስገባ፣ ቦት ንዝተሓገዘ ንመልእኽቲ ክኸውን እዩ።",
        "help_6": "Step 5: Review and Submit\nTG: ሓደ ብሙሉ ዝተሓለፈ ጥያቄ ክልተ ተከታታይ ኣሎ፣ መረጃካ/ኪ ብጥንቃቐ ይገምግሙ and “Confirm” ኣጫኑ።",
        "help_7": "Step 6: Finished\nTG: 🎉 ሁሉም ተዘጋጅቷል! መረጃካ/ኪ ተሰጥቷል። መርገጸ ቀጻሊ ክሳብ ተከተል እዩ።",
        # --- END FIX ---

        "invalid_text": "ቅኑዕ ኣይመስልን። በጃኹም እንደገና ፈትኑ።",
        "invalid_photo": "ስእሊ እጽበ ኣለኹ። በጃኹም ስእሊ ኣስግሩ።",
        "invalid_date": "ናይ ዕለት ቅርጺ ቅኑዕ ኣይኮነን። በጃኹም DD/MM/YYYY (ንኣብነት፡ `20/08/1990`) *ብኢትዮጵያዊ ኣቆጻጽራ* ተጠቐሙ።",
        "invalid_email": "ቅኑዕ ኢሜይል ኣይመስልን። በጃኹም እንደገና ፈትኑ (ንኣብነት፡ `user@example.com`)።",
        "invalid_phone": "ቅኑዕ ቁጽሪ ስልኪ ኣይመስልን። በጃኹም መእተዊ ቁጽሪ ሃገር የካትቱ (ንኣብነት፡ `+251...`)።",
        "admin_pdf_caption": "እዚ ናይ ምዝገባ ሰነድኩም ካብ ኣድሚን እተላእከ እዩ።",
        "soft_cancel_prompt": "ኣብ ማእከል ምምላእ ቅጥዒ ኣለኹም። ብርግጽ ክትስርዝዎን ናብ ቀንዲ መርዝር ክትምለሱን ትደልዩ?",
        "soft_cancel_yes": "✅ እወ፣ ስረዝ",
        "soft_cancel_no": "❌ ኣይፋልን፣ ቀጽል",
        "soft_cancel_confirm": "ቅጥዒ ተሰሪዙ። ናብ ቀንዲ መርዝር ተመሊስኩም።",
        "soft_cancel_decline": " ሕራይ፣ ካብ'ቲ ዘቋረጽኩምዎ ቀጽሉ።",
    },
}

# --- Helper Functions ---

def get_text(key: str, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Gets translated text. Falls back to English if translation is missing."""
    lang = context.user_data.get("language", "en")
    return translations.get(lang, translations["en"]).get(key, translations["en"].get(key, f"_{key}_"))

def format_summary(data: Dict[str, Any]) -> str:
    """Formats user data for the final summary."""
    
    def _get_val(key: str, default: str = "N/A") -> str:
        """Helper to get value or default."""
        val = data.get(key)
        # Handle "None" string from middle name
        if val == "None":
            return ""
        return val if val else default
    
    def _format_date(ec_key: str, gc_key: str, default: str = "N/A") -> str:
        """Helper to format EC and GC dates."""
        ec = data.get(ec_key)
        gc = data.get(gc_key)
        if ec and gc:
            return f"{ec} (EC) / [{gc} (GC)]"
        elif ec:
            return f"{ec} (EC)"
        return default

    try:
        # Build name, handling "None" middle name
        name_parts = [_get_val('given_name'), _get_val('middle_name'), _get_val('surname')]
        full_name = " ".join(part for part in name_parts if part and part != "N/A" and part != "None")
        
        summary = f"👤 *Applicant Info*\n"
        summary += f"  Name: {full_name}\n"
        summary += f"  Gender: {_get_val('gender')}\n"
        summary += f"  DOB: {_format_date('dob_ec', 'dob_gc')}\n"
        summary += f"  Birth City: {_get_val('birth_city')}\n"
        summary += f"  Birth Country: {_get_val('birth_country')}\n"
        summary += f"  Eligibility: {_get_val('eligibility_country')}\n"
        summary += f"  Email: `{_get_val('email')}`\n"
        summary += f"  Phone: `{_get_val('phone')}`\n"
        summary += f"  Education: {_get_val('education')}\n"
        summary += f"  Marital Status: {_get_val('marital_status')}\n"

        if 'passport_number' in data:
            summary += f"\n🛂 *Passport Info*\n"
            summary += f"  Number: {_get_val('passport_number')}\n"
            summary += f"  Issuance: {_get_val('passport_issuance')}\n"
            summary += f"  Expiration: {_format_date('passport_expiration_ec', 'passport_expiration_gc')}\n"
        
        if 'spouse_surname' in data:
            spouse_name_parts = [_get_val('spouse_given_name'), _get_val('spouse_middle_name'), _get_val('spouse_surname')]
            spouse_full_name = " ".join(part for part in spouse_name_parts if part and part != "N/A" and part != "None")
            
            summary += f"\n👩‍❤️‍👨 *Spouse Info*\n"
            summary += f"  Name: {spouse_full_name}\n"
            summary += f"  DOB: {_format_date('spouse_dob_ec', 'spouse_dob_gc')}\n"
            summary += f"  Birth Country: {_get_val('spouse_birth_country')}\n"
        
        children = data.get('children', [])
        if children:
            summary += f"\n👶 *Children Info* (Total: {len(children)})\n"
            for i, child in enumerate(children, 1):
                child_name_parts = [child.get('given_name', 'N/A'), child.get('middle_name', 'N/A'), child.get('surname', 'N/A')]
                child_full_name = " ".join(part for part in child_name_parts if part and part != "N/A" and part != "None")
                
                summary += f"  *Child {i}*\n"
                summary += f"    Name: {child_full_name}\n"
                
                # --- BUG FIX START (Already in your code) ---
                child_ec = child.get('dob_ec')
                child_gc = child.get('dob_gc')
                child_dob_str = "N/A"
                
                if child_ec and child_gc:
                    child_dob_str = f"{child_ec} (EC) / [{child_gc} (GC)]"
                elif child_ec:
                    child_dob_str = f"{child_ec} (EC)"
                
                summary += f"    DOB: {child_dob_str}\n"
                # --- BUG FIX END ---
                
                summary += f"    Birth Country: {child.get('birth_country', 'N/A')}\n"
        
        return summary
    except Exception as e:
        logger.error(f"Error formatting summary: {e}", exc_info=True)
        return "Error generating summary. Please contact support."

def build_regex_pattern(key: str, prefix: str = "") -> filters.Regex:
    """Builds regex patterns from the translations dict directly."""
    pattern_list = []
    for lang_code in translations:
        text = translations[lang_code].get(key)
        if text:
            # Escape special regex chars from the prefix and text
            pattern_list.append(re.escape(f"{prefix}{text}"))
    
    if not pattern_list:
        # Fallback in case key is missing
        return filters.Regex(f"^{re.escape(prefix)}{key}$")
        
    return filters.Regex(f"^({'|'.join(pattern_list)})$")