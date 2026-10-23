import re
from typing import Dict, Any, List
from telegram.ext import ContextTypes, filters
from config import logger

# --- Translation Dictionary ---
# Updated to comply strictly with official U.S. Electronic Diversity Visa Form DS-5501 (DV-2027 / DV-2028)
translations: Dict[str, Dict[str, str]] = {
    "en": {
        "welcome": "Welcome! 👋 Please select your language.",
        "lang_selected_pre": "Language set to English 🇬🇧.",
        "lang_selected": "You can change this later using the 🌍 /language button.\n\nAll data you enter *must be in English letters* (A, B, C...) for the DV application, even if the questions are in another language.",
        "start_new_form": "Please click 📝 New Form to begin.",
        "new_form_button": "New Form",
        "form_restarted": "Your application form has been restarted.",
        "main_menu_prompt": "You are at the main menu. What would you like to do?",
        "fallback": "Sorry, I didn't understand that. Please use the main menu or type /start to begin.",
        "data_cleared": "Your data has been cleared. Please select your language to start over.",
        "ask_gender": "1️⃣ Great, let's start.\n\nWhat is your gender? 👤\n(Official DS-5501 requirement: Male or Female as listed on civil documents)",
        "gender_male": "👨 Male",
        "gender_female": "👩 Female",
        "ask_surname": "2️⃣ Please enter your full legal name.\n\n*Surname (Last/Family Name):*",
        "ask_given_name": "*Given Name (First Name):*",
        "ask_middle_name": "*Middle Name:*\n(If you have no middle name, please type `None`)",
        "ask_dob": "3️⃣ What is your Date of Birth?\n\nPlease enter it in the *Ethiopian Calendar* (e.g., `20/08/1990`).",
        "ask_birth_city": "4️⃣ What is your City of Birth?\n(If unknown, type `Unknown`)",
        "ask_birth_country": "And your Country of Birth?",
        "ask_eligibility_confirm": "5️⃣ Is your country of eligibility the same as your country of birth?",
        "yes": "✅ Yes",
        "no": "❌ No",
        "ask_eligibility_country": "Please specify your country of eligibility:",
        "ask_passport_confirm": "6️⃣ Do you have a valid, unexpired passport?\n\n*Note for DV-2027/DV-2028:* Under program regulations, a valid passport is required for the principal applicant unless you qualify for an official exemption (e.g., stateless or from a Communist country).",
        "ask_passport_number": "Please enter your Passport Number:",
        "ask_passport_issuance": "Country of Issuance (where the passport was issued):",
        "ask_passport_expiration": "Expiration Date:\n\nPlease enter it in the *Ethiopian Calendar* (e.g., `10/01/2020`).",
        "ask_applicant_photo": "7️⃣ Please upload your recent passport-style photo.\n\n*DV Photo Requirements:*\n- Taken within the last 6 months\n- Plain white or off-white background\n- In sharp focus, natural color\n- NO eyeglasses, NO hats/head coverings (unless religious/daily wear)\n- Neutral facial expression looking straight at the camera",
        "photo_enhance_button": "✨ Enhance my picture",
        "ask_current_residence": "8️⃣ What country do you live in today? (Country of Current Residence)",
        "ask_email": "9️⃣ What is your email address?",
        "ask_phone": "And your phone number? (Please include country code, e.g., `+251...`)",
        "ask_education": "🔟 What is your highest level of education?",
        "edu_primary": "🏫 Primary school only",
        "edu_high_school_no_diploma": "📚 High school, no diploma",
        "edu_high_school_degree": "🎒 High school degree",
        "edu_vocational": "🔧 Vocational / Technical school",
        "edu_some_university": "🎓 Some university courses",
        "edu_bachelor": "🎓 Bachelor’s degree",
        "edu_master": "🏅 Master’s degree",
        "edu_doctorate": "🏆 Doctorate",
        "ask_marital_status": "1️⃣1️⃣ What is your marital status?",
        "status_single": "💍 Single / Unmarried",
        "status_married_non_us": "👫 Married (Spouse is NOT a U.S. Citizen/LPR)",
        "status_married_us": "🇺🇸 Married (Spouse IS a U.S. Citizen/LPR)",
        "status_married": "👫 Married",
        "status_divorced": "📝 Divorced",
        "status_widowed": "🕊️ Widowed",
        "status_separated": "⚖️ Legally Separated",
        "spouse_is_us_citizen_note": "ℹ️ Under DV rules, spouses who are U.S. Citizens or Lawful Permanent Residents do not need a Diversity Visa and will not be entered as derivatives.",
        "ask_spouse_surname": "Got it. Please enter your *spouse's* full name.\n\n*Spouse's Surname (Last/Family Name):*",
        "ask_spouse_given_name": "*Spouse's Given Name (First Name):*",
        "ask_spouse_middle_name": "*Spouse's Middle Name:*\n(If no middle name, type `None`)",
        "ask_spouse_gender": "What is your spouse's gender?",
        "ask_spouse_dob": "What is your spouse's Date of Birth?\n\nPlease enter it in the *Ethiopian Calendar* (e.g., `20/08/1990`).",
        "ask_spouse_birth_city": "What is your spouse's City of Birth?\n(If unknown, type `Unknown`)",
        "ask_spouse_birth_country": "What is your spouse's Country of Birth?",
        "ask_spouse_photo": "Please upload your *spouse's* passport-style photo (plain white background, no glasses).",
        "ask_children_count": "1️⃣2️⃣ How many *unmarried* children under the age of 21 do you have?\n\n(Include all living biological children, legally adopted children, and stepchildren. Enter `0` if none)",
        "ask_child_surname": "Please provide info for *Child {num}*.\n\n*Child's Surname (Last/Family Name):*",
        "ask_child_given_name": "*Child's Given Name (First Name):*",
        "ask_child_middle_name": "*Child's Middle Name:*\n(If no middle name, type `None`)",
        "ask_child_gender": "What is Child {num}'s gender?",
        "ask_child_dob": "Child {num}'s Date of Birth:\n\nPlease enter it in the *Ethiopian Calendar* (e.g., `20/08/2015`).",
        "ask_child_birth_city": "Child {num}'s City of Birth:\n(If unknown, type `Unknown`)",
        "ask_child_birth_country": "Child {num}'s Country of Birth:",
        "ask_child_photo": "Please upload *Child {num}'s* passport-style photo.",
        "all_children_done": "All children's data collected.",
        "final_summary_title": "1️⃣3️⃣ Amazing! Please review your information.",
        "final_summary_confirm": "Is all this information correct?",
        "confirm": "✅ Yes, Confirm & Submit",
        "edit_restart": "✏️ No, Edit (Restart form)",
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
        "my_data_title": "My Submitted Data",
        "my_data_none": "You have not submitted any data yet. Click 📝 New Form to start.",
        "support_text": "For support, please contact @nahoomac.",
        "help_title": "--- *Help Guide (DV Program)* ---",
        "help_1": "Welcome! This guide shows you how to submit your official U.S. Diversity Visa (DV) application details through this bot.",
        "help_2": "Step 1: Start the Application\nClick the “📋 New Form” button. The bot will ask for your gender (Male/Female) and then your full legal name matching your passport.",
        "help_3": "Step 2: Personal & Passport Info\nProvide your Date of Birth (Ethiopian Calendar), birthplace, eligibility country, and valid passport details.",
        "help_4": "Step 3: Upload Compliant Photos\nUpload a recent (within 6 months) passport-style photo. Plain white background, neutral expression, and NO eyeglasses.",
        "help_5": "Step 4: Contact & Education\nEnter your country of residence, email, phone number, education level, and marital status.",
        "help_6": "Step 5: Derivatives (Spouse & Children)\nIf married and spouse is not a U.S. Citizen/LPR, enter spouse details. List all unmarried children under 21 with photos and birth info.",
        "help_7": "Step 6: Review, Confirm & Complete\nReview your submission summary, confirm, and complete the service fee.",
        "invalid_text": "That doesn't look right. Please try again.",
        "invalid_photo": "I'm waiting for a photo. Please upload an image.",
        "invalid_date": "Invalid date format. Please use DD/MM/YYYY (e.g., `20/08/1990`) in the *Ethiopian Calendar*.",
        "invalid_email": "That doesn't look like a valid email. Please try again (e.g., `user@example.com`).",
        "invalid_phone": "That doesn't look like a valid phone number. Please include the country code (e.g., `+251...`).",
        "admin_pdf_caption": "Here is your registration document from the admin. Please save it.",
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
        "ask_gender": "1️⃣ በጣም ጥሩ፣ እንጀምር።\n\nጾታዎ ምንድነው? 👤\n(በDS-5501 ደንብ መሠረት: በሰነድዎ ላይ የተመዘገበው ወንድ ወይም ሴት ብቻ)",
        "gender_male": "👨 ወንድ",
        "gender_female": "👩 ሴት",
        "ask_surname": "2️⃣ እባክዎ ሙሉ ህጋዊ ስምዎን ያስገቡ።\n\n*የአያት ስም (የቤተሰብ ስም):*",
        "ask_given_name": "*የመጀመሪያ ስም (የራስ ስም):*",
        "ask_middle_name": "*የአባት ስም:*\n(የአባት ስም ከሌለዎት `None` ብለው ይተይቡ)",
        "ask_dob": "3️⃣ የትውልድ ቀንዎ መቼ ነው?\n\nእባክዎ *በኢትዮጵያ ካሌንደር* ያስገቡ (ለምሳሌ፡ `20/08/1990`)።",
        "ask_birth_city": "4️⃣ የትውልድ ከተማዎ የት ነው?\n(የማይታወቅ ከሆነ `Unknown` ብለው ይተይቡ)",
        "ask_birth_country": "የትውልድ ሀገርዎስ?",
        "ask_eligibility_confirm": "5️⃣ የውድድር ብቁ የሆኑበት ሀገር ከትውልድ ሀገርዎ ጋር ተመሳሳይ ነው?",
        "yes": "✅ አዎ",
        "no": "❌ አይ",
        "ask_eligibility_country": "እባክዎ የብቁነት ሀገርዎን ይግለጹ:",
        "ask_passport_confirm": "6️⃣ ሕጋዊ እና ያላበቃለት ፓስፖርት አለዎት?\n\n*ማስታወሻ ለDV-2027/DV-2028:* በፕሮግራሙ ደንብ መሠረት፣ በይፋዊ ሁኔታ ካልተፈቀደ በስተቀር ለዋናው አመልካች ሕጋዊ ፓስፖርት ያስፈልጋል።",
        "ask_passport_number": "እባክዎ የፓስፖርት ቁጥርዎን ያስገቡ:",
        "ask_passport_issuance": "ፓስፖርቱ የተሰጠበት ሀገር:",
        "ask_passport_expiration": "ፓስፖርቱ የሚያበቃበት ቀን:\n\nእባክዎ *በኢትዮጵያ ካሌንደር* ያስገቡ (ለምሳሌ፡ `10/01/2020`)።",
        "ask_applicant_photo": "7️⃣ እባክዎ የቅርብ ጊዜ ፓስፖርት-ስታይል ፎቶዎን ይስቀሉ።\n\n*የፎቶ መስፈርቶች (DV Program)*:\n- ባለፉት 6 ወራት ውስጥ የተነሳ\n- ግልጽ፣ በነጭ ጀርባ ላይ ያለ\n- ያለ ፊልተር፣ ያለ መነጽር፣ ያለ ጥላ\n- ፊትዎ መሃል ላይ ሆኖ ካሜራውን በቀጥታ የሚመለከት",
        "photo_enhance_button": "✨ ፎቶዬን አሻሽል",
        "ask_current_residence": "8️⃣ በአሁኑ ጊዜ የሚኖሩበት ሀገር የት ነው? (የአሁኑ መኖሪያ ሀገር)",
        "ask_email": "9️⃣ የእርስዎ ኢሜይል አድራሻ ምንድነው?",
        "ask_phone": "ስልክ ቁጥርዎስ? (እባክዎ የሀገር ኮድ ያካትቱ፣ ለምሳሌ፡ `+251...`)",
        "ask_education": "🔟 የእርስዎ ከፍተኛ የትምህርት ደረጃ ምንድነው?",
        "edu_primary": "🏫 የመጀመሪያ ደረጃ ትምህርት ብቻ",
        "edu_high_school_no_diploma": "📚 ሁለተኛ ደረጃ ትምህርት ቤት፣ ዲፕሎማ የለም",
        "edu_high_school_degree": "🎒 የሁለተኛ ደረጃ ትምህርት ቤት ዲግሪ",
        "edu_vocational": "🔧 የሙያ / ቴክኒክ ትምህርት ቤት",
        "edu_some_university": "🎓 የተወሰኑ የዩኒቨርሲቲ ኮርሶች",
        "edu_bachelor": "🎓 የባችለር ዲግሪ",
        "edu_master": "🏅 የማስተርስ ዲግሪ",
        "edu_doctorate": "🏆 ዶክትሬት",
        "ask_marital_status": "1️⃣1️⃣ የጋብቻ ሁኔታዎ ምንድነው?",
        "status_single": "💍 ያላገባ / ያላገባች",
        "status_married_non_us": "👫 ያገባ (የትዳር ጓደኛ የUS ዜጋ ያልሆነ/ች)",
        "status_married_us": "🇺🇸 ያገባ (የትዳር ጓደኛ የUS ዜጋ ወይም LPR የሆነ/ች)",
        "status_married": "👫 ያገባ / ያገባች",
        "status_divorced": "📝 የተፋታ / የተፋታች",
        "status_widowed": "🕊️ በሞት የተለየ / የተለየች",
        "status_separated": "⚖️ በህግ የተለየ",
        "spouse_is_us_citizen_note": "ℹ️ በDV ደንብ መሠረት፣ የUS ዜጋ ወይም ቋሚ ነዋሪ የሆኑ የትዳር አጋሮች የDV ቪዛ ስለማያስፈልጋቸው በዝርዝር ውስጥ አይካተቱም።",
        "ask_spouse_surname": "ገባኝ። እባክዎ *የትዳር ጓደኛዎን* ሙሉ ስም ያስገቡ።\n\n*የትዳር ጓደኛ የአያት ስም:*",
        "ask_spouse_given_name": "*የትዳር ጓደኛ የመጀመሪያ ስም:*",
        "ask_spouse_middle_name": "*የትዳር ጓደኛ የአባት ስም:*\n(`None` ብለው ይተይቡ)",
        "ask_spouse_gender": "የትዳር ጓደኛዎ ጾታ ምንድነው?",
        "ask_spouse_dob": "የትዳር ጓደኛዎ የትውልድ ቀን መቼ ነው?\n\nእባክዎ *በኢትዮጵያ ካሌንደር* ያስገቡ (ለምሳሌ፡ `20/08/1990`)።",
        "ask_spouse_birth_city": "የትዳር ጓደኛዎ የትውልድ ከተማ የት ነው?\n(የማይታወቅ ከሆነ `Unknown` ብለው ይተይቡ)",
        "ask_spouse_birth_country": "የትዳር ጓደኛዎ የትውልድ ሀገር ምንድነው?",
        "ask_spouse_photo": "እባክዎ *የትዳር ጓደኛዎን* ፓስፖርት-ስታይል ፎቶ ይስቀሉ (በነጭ ጀርባ፣ ያለ መነጽር)።",
        "ask_children_count": "1️⃣2️⃣ ዕድሜያቸው ከ21 ዓመት በታች የሆኑ *ያላገቡ* ልጆች ስንት ናቸው?\n\n(የእንጀራ ልጆችንና የጉዲፈቻ ልጆችን ጨምሮ። ከሌለ `0` ያስገቡ)",
        "ask_child_surname": "እባክዎ *የልጅ {num}* መረጃ ያስገቡ።\n\n*የልጁ የአያት ስም:*",
        "ask_child_given_name": "*የልጁ የመጀመሪያ ስም:*",
        "ask_child_middle_name": "*የልጁ የአባት ስም:*\n(`None` ብለው ይተይቡ)",
        "ask_child_gender": "የልጅ {num} ጾታ ምንድነው?",
        "ask_child_dob": "የልጅ {num} የትውልድ ቀን:\n\n*በኢትዮጵያ ካሌንደር* (ለምሳሌ፡ `20/08/2015`)።",
        "ask_child_birth_city": "የልጅ {num} የትውልድ ከተማ:\n(የማይታወቅ ከሆነ `Unknown` ብለው ይተይቡ)",
        "ask_child_birth_country": "የልጅ {num} የትውልድ ሀገር:",
        "ask_child_photo": "እባክዎ *የልጅ {num}* ፓስፖርት-ስታይል ፎቶ ይስቀሉ።",
        "all_children_done": "የልጆቹ መረጃ በሙሉ ተሰብስቧል።",
        "final_summary_title": "1️⃣3️⃣ በጣም ጥሩ! እባክዎ መረጃዎን ይገምግሙ።",
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
        "help_title": "--- *የDV ፕሮግራም የእርዳታ መመሪያ* ---",
        "help_1": "እንኳን ደህና መጡ! ይህ መመሪያ ለUS Diversity Visa (DV) ሎተሪ ማመልከቻ መረጃዎትን በዚህ ቦት እንዴት እንደሚያስገቡ ያሳያል።",
        "help_2": "ደረጃ 1: ማመልከቻ መጀመር\n“📋 New Form” አዝራርን ይጫኑ። ቦቱ ጾታዎን (ወንድ/ሴት) እና በፓስፖርት ላይ ያለውን ሙሉ ስምዎን ይጠይቃል።",
        "help_3": "ደረጃ 2: የግል እና የፓስፖርት መረጃ\nየትውልድ ቀንዎን በኢትዮጵያ ካሌንደር፣ የትውልድ ከተማ/ሀገርዎን እና የፓስፖርት ዝርዝሮችን ያስገቡ።",
        "help_4": "ደረጃ 3: ህጋዊ ፎቶ መስቀል\nባለፉት 6 ወራት ውስጥ የተነሳ፣ ነጭ ጀርባ ያለው፣ ያለ መነጽር የሆነ የቅርብ ጊዜ ፎቶ ይስቀሉ።",
        "help_5": "ደረጃ 4: የመኖሪያ እና የትምህርት መረጃ\nየአሁኑ መኖሪያ ሀገርዎን፣ ኢሜይል፣ ስልክ ቁጥር፣ የትምህርት ደረጃ እና የጋብቻ ሁኔታ ያስገቡ።",
        "help_6": "ደረጃ 5: የትዳር አጋር እና የልጆች መረጃ\nያገቡ ከሆኑ እና የትዳር አጋርዎ የUS ዜጋ ካልሆነ/ች፣ ሙሉ መረጃቸውን እና ፎቷቸውን ያስገቡ። ዕድሜያቸው ከ21 ዓመት በታች የሆኑ ያላገቡ ልጆችን ሁሉ ይመዝግቡ።",
        "help_7": "ደረጃ 6: ማረጋገጥ እና ክፍያ\nሁሉንም መረጃ በጥንቃቄ ይገምግሙ፣ ያረጋግጡ እና የአገልግሎት ክፍያውን ይፈጽሙ።",
        "invalid_text": "ትክክል አይመስልም። እባክዎ እንደገና ይሞክሩ።",
        "invalid_photo": "ፎቶ እየጠበቅኩ ነው። እባክዎ ምስል ይስቀሉ።",
        "invalid_date": "የቀን ቅርጸት ልክ አይደለም። እባክዎ DD/MM/YYYY (ለምሳሌ፡ `20/08/1990`) *በኢትዮጵያ ካሌንደር* ይጠቀሙ።",
        "invalid_email": "ትክክለኛ ኢሜይል አይመስልም። እባክዎ እንደገና ይሞክሩ (ለምሳሌ፡ `user@example.com`)።",
        "invalid_phone": "ትክክለኛ ስልክ ቁጥር አይመስልም። እባክዎ የሀገር ኮድ ያካትቱ (ለምሳሌ፡ `+251...`)።",
        "admin_pdf_caption": "ከአስተዳዳሪው የተላከልዎት የመመዝገቢያ ሰነድ ይኸውና።",
        "warning_mid_form": "You’re in the middle of filling a form. Do you want to cancel?",
        "confirm_cancel_yes": "✅ Yes, cancel the form",
        "confirm_cancel_no": "↩️ No, continue filling",
        "continuing_form": "👍 Okay — continuing where you left off.",
        "form_cancelled": "✅ Form cancelled. You are back at the main menu.",
        "form_cancelled_and_cleared": "Form cancelled and all data cleared. Please select your language to start over.",
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
        "ask_gender": "1️⃣ Gaarii dha, haa jalqabnu.\n\nSaalli kee maali? 👤\n(Ulaagaa DS-5501: Dhiira ykn Dubartii ragaa kee irratti galmaa'e qofa)",
        "gender_male": "👨 Dhiira",
        "gender_female": "👩 Dubartii",
        "ask_surname": "2️⃣ Maaloo maqaa kee guutuu seera qabeessa galchi.\n\n*Maqaa Akaakayyuu (Maqaa Maatii):*",
        "ask_given_name": "*Maqaa Jalqabaa (Maqaa Mataa):*",
        "ask_middle_name": "*Maqaa Gidduu (Maqaa Abbaa):*\n(Maqaa gidduu yoo hin qabaanne, `None` galchi)",
        "ask_dob": "3️⃣ Guyyaan dhaloota kee yoomi?\n\nMaaloo *Kalandara Itoophiyaatiin* galchi (fkn, `20/08/1990`).",
        "ask_birth_city": "4️⃣ Magaalaan dhaloota kee eessa?\n(Yoo hin beekamne `Unknown` galchi)",
        "ask_birth_country": "Biyyi dhaloota keehoo?",
        "ask_eligibility_confirm": "5️⃣ Biyyi ulaagaa dorgommichaaf ittiin guuttu biyya dhaloota kee wajjin tokkoo?",
        "yes": "✅ Eeyyee",
        "no": "❌ Lakkii",
        "ask_eligibility_country": "Maaloo biyya ulaagaa ittiin guuttu ibsi:",
        "ask_passport_confirm": "6️⃣ Paaspoortii seera qabeessa yeroon isaa hin dhumne qabdaa?\n\n*Hubachiisa DV-2027/DV-2028:* Akka qajeelfama DVtti, haala addaatiin yoo ta'e malee iyyataa duraatiif paaspoortiin barbaachisaadha.",
        "ask_passport_number": "Maaloo Lakkoofsa Paaspoortii kee galchi:",
        "ask_passport_issuance": "Biyya Paaspoortiin itti kenname:",
        "ask_passport_expiration": "Guyyaa itti xumuramu:\n\nMaaloo *Kalandara Itoophiyaatiin* galchi (fkn, `10/01/2020`).",
        "ask_applicant_photo": "7️⃣ Maaloo suuraa kee kan dhiheenya kan paaspoortii fe'i.\n\n*Ulaagaa Suuraa (DV Program)*:\n- Ji'oota 6 darban keessatti kan kaafame\n- Ifa kan ta'e, dugdi isaa adii qulqulluu\n- Kooblee ijaa malee, gaaddidduu fi filteerii malee\n- Fuulli kee kallattiin gara kaameraatti kan ilaalu",
        "photo_enhance_button": "✨ Suuraa koo fooyyessi",
        "ask_current_residence": "8️⃣ Yeroo ammaa kana biyya kam keessa jiraatta? (Biyya Jireenyaa)",
        "ask_email": "9️⃣ Teessoon imeelii kee maali?",
        "ask_phone": "Lakkoofsi bilbilaa keehoo? (Maaloo koodii biyyaa dabalii, fkn, `+251...`)",
        "ask_education": "🔟 Sadarkaan barnootaa kee isa ol'aanaa maali?",
        "edu_primary": "🏫 Barnoota sadarkaa 1ffaa qofa",
        "edu_high_school_no_diploma": "📚 Mana barumsaa sadarkaa 2ffaa, diippiloomaa hin qabu",
        "edu_high_school_degree": "🎒 Diippiloomaa mana barumsaa sadarkaa 2ffaa",
        "edu_vocational": "🔧 Mana barumsaa Ogummaa / Teeknikaa",
        "edu_some_university": "🎓 Koorsoota Yuunivarsiitii muraasa",
        "edu_bachelor": "🎓 Digirii Baacheelarii",
        "edu_master": "🏅 Digirii Maasterii",
        "edu_doctorate": "🏆 Digirii Doktoreetii",
        "ask_marital_status": "1️⃣1️⃣ Haalli gaa'elaa kee maali?",
        "status_single": "💍 Kan hin fuune / Hin heerumne",
        "status_married_non_us": "👫 Kan fuudhe/heerumte (Haati/Abbaan warraa lammummaa US hin qabne)",
        "status_married_us": "🇺🇸 Kan fuudhe/heerumte (Haati/Abbaan warraa lammummaa US/LPR qabu)",
        "status_married": "👫 Kan fuudhe / Heerumte",
        "status_divorced": "📝 Kan hiike / Hiikte",
        "status_widowed": "🕊️ Kan irraa du'e / duute",
        "status_separated": "⚖️ Seeraan kan addaan bahe",
        "spouse_is_us_citizen_note": "ℹ️ Akka qajeelfama DVtti, haati/abbaan warraa lammummaa US qaban viizaa DV waan hin barbaachifneef hin galmeeffaman.",
        "ask_spouse_surname": "Hubadheera. Maaloo maqaa guutuu *haadha/abbaa warraa* kee galchi.\n\n*Maqaa Akaakayyuu haadha/abbaa warraa:*",
        "ask_spouse_given_name": "*Maqaa Jalqabaa haadha/abbaa warraa:*",
        "ask_spouse_middle_name": "*Maqaa Gidduu haadha/abbaa warraa:*\n(`None` galchi)",
        "ask_spouse_gender": "Saalli haadha/abbaa warraa keetii maali?",
        "ask_spouse_dob": "Guyyaan dhaloota haadha/abbaa warraa kee yoomi?\n\nMaaloo *Kalandara Itoophiyaatiin* galchi (fkn, `20/08/1990`).",
        "ask_spouse_birth_city": "Magaalaan dhaloota haadha/abbaa warraa keetii eessa?\n(Yoo hin beekamne `Unknown` galchi)",
        "ask_spouse_birth_country": "Biyyi dhaloota haadha/abbaa warraa kee eessa?",
        "ask_spouse_photo": "Maaloo suuraa paaspoortii *haadha/abbaa warraa* kee fe'i (dugda adii, kooblee malee).",
        "ask_children_count": "1️⃣2️⃣ Ijoollee *kan hin fuune/hin heerumne* umuriin isaanii waggaa 21 gadii meeqa qabda?\n\n(Ijoollee guddifachaa fi ijoollee abbaa/haadha manaa dabalatee. Yoo hin qabaanne `0` galchi)",
        "ask_child_surname": "Maaloo odeeffannoo *Mucaa {num}* galchi.\n\n*Maqaa Akaakayyuu mucaa:*",
        "ask_child_given_name": "*Maqaa Jalqabaa mucaa:*",
        "ask_child_middle_name": "*Maqaa Gidduu mucaa:*\n(`None` galchi)",
        "ask_child_gender": "Saalli Mucaa {num} maali?",
        "ask_child_dob": "Guyyaan dhaloota Mucaa {num}:\n\n*Kalandara Itoophiyaatiin* (fkn, `20/08/2015`).",
        "ask_child_birth_city": "Magaalaan dhaloota Mucaa {num}:\n(Yoo hin beekamne `Unknown` galchi)",
        "ask_child_birth_country": "Biyyi dhaloota Mucaa {num}:",
        "ask_child_photo": "Maaloo suuraa paaspoortii *Mucaa {num}* fe'i.",
        "all_children_done": "Ragaan ijoollee hunda walitti qabameera.",
        "final_summary_title": "1️⃣3️⃣ Gaariidha! Maaloo odeeffannoo kee mirkaneeffadhu.",
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
        "help_title": "--- *Qajeelfama Gargaarsaa DV* ---",
        "help_1": "Baga nagaan dhuftan! Qajeelfamni kun carraa DV Lottery USA karaa bot kanaa akkamitti akka galmeeffattan isin agarsiisa.",
        "help_2": "Tarkaanfii 1: Galmee Jalqabuu\nQabduu “📋 New Form” jedhu tuqaa. Botichi dura saala (Dhiira/Dubartii) fi maqaa keessan guutuu akkuma paaspoortii irratti jiru gaafata.",
        "help_3": "Tarkaanfii 2: Ragaa Dhuunfaa fi Paaspoortii\nGuyyaa dhalootaa Kalandara Itoophiyaatiin, bakka dhalootaa fi odeeffannoo paaspoortii guutaa.",
        "help_4": "Tarkaanfii 3: Suuraa Seera Qabeessa Fe'uu\nSuuraa ji'oota 6 darban keessatti kaafame, dugdi isaa adii qulqulluu ta'ee fi kooblee ijaa kan hin qabne fe'aa.",
        "help_5": "Tarkaanfii 4: Jireenyaa fi Barnoota\nBiyya jireenyaa, imeelii, bilbila, sadarkaa barnootaa fi haala gaa'elaa galchaa.",
        "help_6": "Tarkaanfii 5: Haadha/Abbaa Warraa fi Ijoollee\nYoo kan fuutan/heerumtan ta'e fi lammummaa US kan hin qabne yoo ta'e ragaa isaanii guutaa. Ijoollee umuriin isaanii 21 gadii hunda galmeessaa.",
        "help_7": "Tarkaanfii 6: Mirkaneessuu fi Xumuruu\nRagaa keessan hunda sirriitti mirkaneessaa, kaffaltii tajaajilaa kaffalaa.",
        "invalid_text": "Sirrii miti. Maaloo irra deebi'ii yaali.",
        "invalid_photo": "Suuraan eegaa jira. Maaloo suuraa fe'i.",
        "invalid_date": "Unki guyyaa sirrii miti. Maaloo DD/MM/YYYY (fkn, `20/08/1990`) *Kalandara Itoophiyaatiin* fayyadami.",
        "invalid_email": "Kun imeelii sirrii hin fakkaatu. Maaloo irra deebi'ii yaali (fkn, `user@example.com`).",
        "invalid_phone": "Kun lakkoofsa bilbilaa sirrii hin fakkaatu. Maaloo koodii biyyaa dabalii (fkn, `+251...`).",
        "admin_pdf_caption": "Kunooti sanada galmee kee kan bulchaa irraa ergame.",
        "warning_mid_form": "You’re in the middle of filling a form. Do you want to cancel?",
        "confirm_cancel_yes": "✅ Yes, cancel the form",
        "confirm_cancel_no": "↩️ No, continue filling",
        "continuing_form": "👍 Okay — continuing where you left off.",
        "form_cancelled": "✅ Form cancelled. You are back at the main menu.",
        "form_cancelled_and_cleared": "Form cancelled and all data cleared. Please select your language to start over.",
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
        "main_menu_prompt": "ኣብ ቀንዲ መርዝር ኣለኹም። እንታይ ክንገብረልኩም ትደልዩ?",
        "fallback": "ይቕረታ፣ ኣይተረድኣንን። በጃኹም ነቲ ቀንዲ መርዝር ተጠቐሙ ወይ ንምጅማር /start በሉ።",
        "data_cleared": "ሓበሬታኹም ተደምሲሱ። ዳግማይ ንምጅማር በጃኹም ቋንቋኹም ምረጹ።",
        "new_form_button": "New Form",
        "my_data_button": "My Submitted Data",
        "language_button": "/language (ቋንቋ)",
        "help_button": "/help (ሓገዝ)",
        "support_button": "/support (ድጋፍ)",
        "clear_data_button": "/cleardata (ሓበሬታ ምጽራይ)",
        "ask_gender": "1️⃣ ብጣዕሚ ጽቡቕ፣ ንጀምር።\n\nጾታኹም እንታይ እዩ? 👤\n(ብመሰረት DS-5501: ኣብ ወግዓዊ ሰነድ ዝተመዝገበ ወዲ ወይ ጓል ጥራይ)",
        "gender_male": "ወዲ",
        "gender_female": "ጓል",
        "ask_surname": "2️⃣ በጃኹም ምሉእ ሕጋዊ ስምኩም ኣእትዉ።\n\n*ስም ስድራቤት ( ናይ መወዳእታ ስም):*",
        "ask_given_name": "*ቀዳማይ ስም ( ናይ ገዛእ ስም):*",
        "ask_middle_name": "*ማእከላይ ስም (ናይ ኣቦ ስም):*\n(ማእከላይ ስም እንተዘይብልኩም፣ `None` ኢልኩም ጸሓፉ)",
        "ask_dob": "3️⃣ ዕለተ ልደትኩም መዓስ እዩ?\n\nበጃኹም *ብኢትዮጵያዊ ኣቆጻጽራ* ኣእትዉ (ንኣብነት፡ `20/08/1990`)።",
        "ask_birth_city": "4️⃣ እትተወልድኹምላ ከተማ ኣበይ እያ?\n(ዘይፍለጥ እንተኾይኑ `Unknown` ኢልኩም ጸሓፉ)",
        "ask_birth_country": "እትተወልድኹምላ ሃገርስ?",
        "ask_eligibility_confirm": "5️⃣ ንውድድር ብቕዕቲ እትገብረኩም ሃገር ምስ እትተወልድኹምላ ሃገር ሓንቲ ድያ?",
        "yes": "እወ",
        "no": "ኣይፋልን",
        "ask_eligibility_country": "በጃኹም ነታ ብቕዕቲ እትገብረኩም ሃገር ግለጹ:",
        "ask_passport_confirm": "6️⃣ ሕጋዊ ዘየብቅዐ ፓስፖርት ኣለኩምዶ?\n\n*መዘካከሪ ንDV-2027/DV-2028:* ብመሰረት ሕጊ ፕሮግራም፣ ብፍሉይ ኩነታት እንተዘይኮይኑ ንቀንዲ መመልከቲ ሕጋዊ ፓስፖርት የድሊ እዩ።",
        "ask_passport_number": "በጃኹም ቁጽሪ ፓስፖርትኩም ኣእትዉ:",
        "ask_passport_issuance": "ፓስፖርት እተዋህበላ ሃገር:",
        "ask_passport_expiration": "እቲ ፓስፖርት ዘብቅዓሉ ዕለት:\n\nበጃኹም *ብኢትዮጵያዊ ኣቆጻጽራ* ኣእትዉ (ንኣብነት፡ `10/01/2020`)።",
        "ask_applicant_photo": "7️⃣ በጃኹም ናይ ቀረባ ግዜ ናይ ፓስፖርት ዓይነት ስእልኹም ኣስገሩ።\n\n*ናይ ስእሊ ረቋሒታት (DV Program)*:\n- ኣብ ዝሓለፉ 6 ኣዋርሕ እተላዕለ\n- ጽሩይ፣ ኣብ ጻዕዳ ድሕሪት ዘለዎ\n- ብዘይ ፊልተር፣ ብዘይ መነጸር፣ ብዘይ ጽላሎት\n- ገጽኩም ማእከል ገይሩ ናብ ካሜራ ብቐጥታ ዝጥምት",
        "photo_enhance_button": "✨ ንስእለይ ኣመሓይሽ",
        "ask_current_residence": "8️⃣ ኣብዚ እዋን ኣብ ኣየነይቲ ሃገር ትነብሩ ኣለኹም? (ናይ ሕጂ መነበሪ ሃገር)",
        "ask_email": "9️⃣ ኣድራሻ ኢሜይልኩም እንታይ እዩ?",
        "ask_phone": "ቁጽሪ ስልኩኹምከ? (በጃኹም መእተዊ ቁጽሪ ሃገር የካትቱ፣ ንኣብነት፡ `+251...`)",
        "ask_education": "🔟 ዝለዓለ ደረጃ ትምህርትኹም እንታይ እዩ?",
        "edu_primary": "ናይ መጀመርታ ደረጃ ትምህርቲ ጥራይ",
        "edu_high_school_no_diploma": "ካልኣይ ደረጃ ቤት ትምህርቲ፣ ዲፕሎማ የብለይን",
        "edu_high_school_degree": "ናይ ካልኣይ ደረጃ ቤት ትምህርቲ ዲግሪ",
        "edu_vocational": "ናይ ሞያ / ቴክኒክ ቤት ትምህርቲ",
        "edu_some_university": "ገለ ናይ ዩኒቨርሲቲ ኮርሳት",
        "edu_bachelor": "ባችለር ዲግሪ",
        "edu_master": "ማስተርስ ዲግሪ",
        "edu_doctorate": "ዶክትሬት",
        "ask_marital_status": "1️⃣1️⃣ ኩነታት መርዓኹም እንታይ እዩ?",
        "status_single": "ዘይተመርዓኹ / ዘይተመርዓወት",
        "status_married_non_us": "👫 እተመርዓወ/ት (መጻምድቲ ናይ US ዜጋ ዘይኮነ/ት)",
        "status_married_us": "🇺🇸 እተመርዓወ/ት (መጻምድቲ ናይ US ዜጋ ወይ LPR ዝኾነ/ት)",
        "status_married": "እተመርዓኹ / እተመርዓወት",
        "status_divorced": "እተፈትሐ / እተፈትሐት",
        "status_widowed": "ሰብኣያ ዝሞታ / ሰበይቱ ዝሞተቶ",
        "status_separated": "ብሕጊ እተፈላለየ",
        "spouse_is_us_citizen_note": "ℹ️ ብመሰረት ሕጊ DV፣ ናይ US ዜጋ ወይ ቀዋሚ ነበርቲ ዝኾኑ መጻምድቲ ናይ DV ቪዛ ስለዘየድልዮም ኣብ መዝገብ ኣይኣትዉን።",
        "ask_spouse_surname": "ተረዲአ። በጃኹም ምሉእ ስም *ናይ መጻምድትኹም* ኣእትዉ።\n\n*ናይ መጻምድቲ ስም ስድራቤት:*",
        "ask_spouse_given_name": "*ናይ መጻምድቲ ቀዳማይ ስም:*",
        "ask_spouse_middle_name": "*ናይ መጻምድቲ ማእከላይ ስም:*\n(`None` ኢልኩም ጸሓፉ)",
        "ask_spouse_gender": "ጾታ መጻምድትኹም እንታይ እዩ?",
        "ask_spouse_dob": "ዕለተ ልደት መጻምድትኹም መዓስ እዩ?\n\nበጃኹም *ብኢትዮጵያዊ ኣቆጻጽራ* ኣእትዉ (ንኣብነት፡ `20/08/1990`)።",
        "ask_spouse_birth_city": "መጻምድትኹም እተወልደላ ከተማ ኣበይ እያ?\n(ዘይፍለጥ እንተኾይኑ `Unknown` ኢልኩም ጸሓፉ)",
        "ask_spouse_birth_country": "መጻምድትኹም እተወልደላ ሃገር ኣበይ እያ?",
        "ask_spouse_photo": "በጃኹም ናይ ፓስፖርት ዓይነት ስእሊ *መጻምድትኹም* ኣስገሩ (ጻዕዳ ድሕሪት፣ ብዘይ መነጸር)።",
        "ask_children_count": "1️⃣2️⃣ ክንደይ ዕድሚኦም ትሕቲ 21 ዝኾኑ *ዘይተመርዓዉ* ቖልዑ ኣለኹም?\n\n(ናይ ሕሳስን ጉዲፈቻን ቆልዑ ሓዊስካ። እንተዘይብልኩም `0` ኣእትዉ)",
        "ask_child_surname": "በጃኹም ሓበሬታ *ናይ ቆልዓ {num}* ኣእትዉ።\n\n*ናይ ቆልዓ ስም ስድራቤት:*",
        "ask_child_given_name": "*ናይ ቆልዓ ቀዳማይ ስም:*",
        "ask_child_middle_name": "*ናይ ቆልዓ ማእከላይ ስም:*\n(`None` ኢልኩም ጸሓፉ)",
        "ask_child_gender": "ጾታ ቆልዓ {num} እንታይ እዩ?",
        "ask_child_dob": "ዕለተ ልደት ቆልዓ {num}:\n\n*ብኢትዮጵያዊ ኣቆጻጽራ* (ንኣብነት፡ `20/08/2015`)።",
        "ask_child_birth_city": "ቆልዓ {num} እተወልደላ ከተማ:\n(ዘይፍለጥ እንተኾይኑ `Unknown` ኢልኩም ጸሓፉ)",
        "ask_child_birth_country": "ቆልዓ {num} እተወልደላ ሃገር:",
        "ask_child_photo": "በጃኹም ናይ ፓስፖርት ዓይነት ስእሊ *ቆልዓ {num}* ኣስገሩ።",
        "all_children_done": "ሓበሬታ ናይ ኩሎም ቆልዑ ተኣኪቡ።",
        "final_summary_title": "1️⃣3️⃣ ብጣዕሚ ጽቡቕ! በጃኹም ሓበሬታኹም ገምግሙ።",
        "final_summary_confirm": "እዚ ሓበሬታ'ዚ ኩሉ ቅኑዕ ድዩ?",
        "confirm": "እወ، ኣረጋግጽ",
        "edit_restart": "አይፋልን፣ ኣተዓራሪ (ነቲ ቅጥዒ ዳግማይ የጀምሮ)",
        "form_complete_payment": "የቐንየለይ!\n\nምስዳድኩም ንምዝዛም፣ ናይ ኣገልግሎት ክፍሊት *350 ብር* ኣሎ።\n\nበጃኹም ናብ ሓደ ካብ'ዞም ዝስዕቡ መሳርሒታት ክፈሉ:",
        "payment_details": """
*CBE (ንግዲ ባንኪ ኢትዮጵያ)*
`1000181234281`

*Telebirr (ቴሌብር)*
`0937105764`
        """,
        "payment_ask_screenshot": "ድሕሪ ምኽፋልኩም፣ በጃኹም ናይቲ ክፍሊት መረጋገጺ *ስክሪንሹት* (screenshot) ኣብዚ ኣስግሩ።",
        "payment_received": "ኣብ መስርሕ'ዩ...",
        "form_complete_success": "🎉 ኩሉ ተወዲኡ! ሓበሬታኹም ተመዝጊቡ።\n\nመመልከቲኹምን ክፍሊትኩምን ክንፍትሽ ኢና። ዝቕጽል ስጉምትታት ክንሕብረኩም ኢና። ንረዳኢና ስለ እተተጠቐምኩም የቐንየልና!",
        "my_data_title": "እዚ እቲ ዘስገድኩምዎ ሓበሬታ እዩ:",
        "my_data_none": "ክሳብ ሕጂ ዝኾነ ሓበሬታ ኣየስገድኩምን። ንምጅማር 📝 New Form ጠውቑ።",
        "support_text": "ንድጋፍ፣ በጃኹም @nahoomacርኸቡ።",
        "help_title": "--- *ናይ DV ፕሮግራም ሓገዝ መምርሒ* ---",
        "help_1": "እንቋዕ ብደሓን መጻእኹም! እዚ መምርሒ ንUS Diversity Visa (DV) ሎተሪ መመልከቲ ሓበሬታኹም ብኸመይ ከም እተእትዉ ይገልጽ።",
        "help_2": "ስጉምቲ 1: ምጅማር\n“📋 New Form” ዝብል ጠውቑ። ቦት መጀመሪያ ጾታኹም (ወዲ/ጓል) ድሕሪኡ ኣብ ፓስፖርት ዘሎ ምሉእ ስምኩም ይሓትት።",
        "help_3": "ስጉምቲ 2: ናይ ውልቀን ፓስፖርትን ሓበሬታ\nዕለተ ልደትኩም ብኢትዮጵያዊ ኣቆጻጽራ፣ ከተማን ሃገርን ልደትኩም ከምኡ'ውን ናይ ፓስፖርት ዝርዝር ኣእትዉ።",
        "help_4": "ስጉምቲ 3: ቅኑዕ ስእሊ ምእታው\nኣብ ዝሓለፉ 6 ኣዋርሕ እተላዕለ፣ ጻዕዳ ድሕሪት ዘለዎ፣ ብዘይ መነጸር ስእሊ ኣእትዉ።",
        "help_5": "ስጉምቲ 4: መነበሪ ሃገርን ትምህርትን\nናይ ሕጂ መነበሪ ሃገርኩም፣ ኢሜይል፣ ቁጽሪ ስልኪ፣ ደረጃ ትምህርቲ ከምኡ'ውን ኩነታት መርዓ ኣእትዉ።",
        "help_6": "ስጉምቲ 5: መጻምድትን ቆልዑን\nእተመርዓውኹም እንተኾይንኩም መጻምድትኹም ናይ US ዜጋ እንተዘይኮይኖም/ነን፣ ምሉእ ሓበሬታኦምን ስእሎምን ኣእትዉ። ዕድሚኦም ትሕቲ 21 ዝኾኑ ዘይተመርዓዉ ቆልዑ ኩሎም ኣመዝግቡ።",
        "help_7": "ስጉምቲ 6: ምጽዳቕን ምኽፋልን\nሓበሬታኹም ብጥንቃቐ ገምግሙ፣ ኣረጋግጹን ናይ ኣገልግሎት ክፍሊት ክፈሉን።",
        "invalid_text": "ቅኑዕ ኣይመስልን። በጃኹም እንደገና ፈትኑ።",
        "invalid_photo": "ስእሊ እጽበ ኣለኹ። በጃኹም ስእሊ ኣስግሩ።",
        "invalid_date": "ናይ ዕለት ቅርጺ ቅኑዕ ኣይኮነን። በጃኹም DD/MM/YYYY (ንኣብነት፡ `20/08/1990`) *ብኢትዮጵያዊ ኣቆጻጽራ* ተጠቐሙ።",
        "invalid_email": "ቅኑዕ ኢሜይል ኣይመስልን። በጃኹም እንደገና ፈትኑ (ንኣብነት፡ `user@example.com`)።",
        "invalid_phone": "ቅኑዕ ቁጽሪ ስልኪ ኣይመስልን። በጃኹም መእተዊ ቁጽሪ ሃገር የካትቱ (ንኣብነት፡ `+251...`)።",
        "admin_pdf_caption": "እዚ ናይ ምዝገባ ሰነድኩም ካብ ኣድሚን እተላእከ እዩ።",
        "warning_mid_form": "You’re in the middle of filling a form. Do you want to cancel?",
        "confirm_cancel_yes": "✅ Yes, cancel the form",
        "confirm_cancel_no": "↩️ No, continue filling",
        "continuing_form": "👍 Okay — continuing where you left off.",
        "form_cancelled": "✅ Form cancelled. You are back at the main menu.",
        "form_cancelled_and_cleared": "Form cancelled and all data cleared. Please select your language to start over.",
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
    """Formats user data for the final summary (updated with full DS-5501 DV fields)."""
    
    def _get_val(key: str, default: str = "N/A") -> str:
        """Helper to get value or default."""
        val = data.get(key)
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
        name_parts = [_get_val('given_name'), _get_val('middle_name'), _get_val('surname')]
        full_name = " ".join(part for part in name_parts if part and part != "N/A" and part != "None")
        
        summary = f"👤 *Applicant Info*\n"
        summary += f"  Name: {full_name}\n"
        summary += f"  Gender: {_get_val('gender')}\n"
        summary += f"  DOB: {_format_date('dob_ec', 'dob_gc')}\n"
        summary += f"  Birth City: {_get_val('birth_city')}\n"
        summary += f"  Birth Country: {_get_val('birth_country')}\n"
        summary += f"  Eligibility: {_get_val('eligibility_country')}\n"
        summary += f"  Current Residence: {_get_val('current_residence')}\n"
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
            summary += f"  Gender: {_get_val('spouse_gender')}\n"
            summary += f"  DOB: {_format_date('spouse_dob_ec', 'spouse_dob_gc')}\n"
            summary += f"  Birth City: {_get_val('spouse_birth_city')}\n"
            summary += f"  Birth Country: {_get_val('spouse_birth_country')}\n"
        
        children = data.get('children', [])
        if children:
            summary += f"\n👶 *Children Info* (Total: {len(children)})\n"
            for i, child in enumerate(children, 1):
                child_name_parts = [child.get('given_name', 'N/A'), child.get('middle_name', 'N/A'), child.get('surname', 'N/A')]
                child_full_name = " ".join(part for part in child_name_parts if part and part != "N/A" and part != "None")
                
                summary += f"  *Child {i}*\n"
                summary += f"    Name: {child_full_name}\n"
                summary += f"    Gender: {child.get('gender', 'N/A')}\n"
                
                child_ec = child.get('dob_ec')
                child_gc = child.get('dob_gc')
                child_dob_str = "N/A"
                if child_ec and child_gc:
                    child_dob_str = f"{child_ec} (EC) / [{child_gc} (GC)]"
                elif child_ec:
                    child_dob_str = f"{child_ec} (EC)"
                
                summary += f"    DOB: {child_dob_str}\n"
                summary += f"    Birth City: {child.get('birth_city', 'N/A')}\n"
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
            pattern_list.append(re.escape(f"{prefix}{text}"))
    
    if not pattern_list:
        return filters.Regex(f"^{re.escape(prefix)}{key}$")
        
    return filters.Regex(f"^({'|'.join(pattern_list)})$")
