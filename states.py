# --- State Definitions for ConversationHandler ---
# Using numeric states is best practice
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
    GET_EMAIL,
    GET_PHONE,
    GET_EDUCATION,
    GET_MARITAL_STATUS,
    GET_SPOUSE_SURNAME,
    GET_SPOUSE_GIVEN_NAME,
    GET_SPOUSE_MIDDLE_NAME,
    GET_SPOUSE_DOB,
    GET_SPOUSE_BIRTH_COUNTRY,
    GET_SPOUSE_PHOTO,
    GET_CHILDREN_COUNT,
    GET_CHILD_INFO,  # This single state will handle the child loop
    GET_FINAL_CONFIRM,
    GET_PAYMENT_SCREENSHOT,
) = range(29) # 29 states from 0 to 28

# New state for the confirmation pop-up
CONFIRM_CANCEL_FORM = 30 # Use a high number to avoid conflict