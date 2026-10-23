# --- State Definitions for ConversationHandler ---
# Updated for DV-2027 / DV-2028 Electronic Diversity Visa (DS-5501) Requirements
(
    SELECT_LANGUAGE,
    GET_GENDER,
    GET_SURNAME,
    GET_GIVEN_NAME,
    GET_MIDDLE_NAME,
    GET_DOB,
    GET_BIRTH_CITY,
    GET_BIRTH_COUNTRY,
    GET_ELIGIBILITY_CONFIRM,
    GET_ELIGIBILITY_COUNTRY,
    GET_PASSPORT_CONFIRM,
    GET_PASSPORT_NUMBER,
    GET_PASSPORT_ISSUANCE,
    GET_PASSPORT_EXPIRATION,
    GET_APPLICANT_PHOTO,
    GET_CURRENT_RESIDENCE,       # Official Question 9: Country where you live today
    GET_EMAIL,
    GET_PHONE,
    GET_EDUCATION,
    GET_MARITAL_STATUS,
    GET_SPOUSE_SURNAME,
    GET_SPOUSE_GIVEN_NAME,
    GET_SPOUSE_MIDDLE_NAME,
    GET_SPOUSE_GENDER,           # Part Two: Mandatory Spouse Gender
    GET_SPOUSE_DOB,
    GET_SPOUSE_BIRTH_CITY,       # Part Two: Mandatory Spouse City of Birth
    GET_SPOUSE_BIRTH_COUNTRY,
    GET_SPOUSE_PHOTO,
    GET_CHILDREN_COUNT,
    GET_CHILD_INFO,              # Child loop: Surname, Given, Middle, Gender, DOB, Birth City, Country, Photo
    GET_FINAL_CONFIRM,
    GET_PAYMENT_SCREENSHOT,
) = range(32) # 32 states from 0 to 31

# State for the confirmation pop-up
CONFIRM_CANCEL_FORM = 50 # High number to avoid conflict