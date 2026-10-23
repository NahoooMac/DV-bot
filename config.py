import logging
import os
import re
from dotenv import load_dotenv
from ethiopian_date import EthiopianDateConverter # Assumes this is installed
import cv2 # For HAAR_PATH

# --- CONFIGURATION ---
load_dotenv()

# Bot Token
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    print("Error: BOT_TOKEN not found in .env file.")
    exit()

# Admin Configuration
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "-1003274949797")
_env_usernames = os.environ.get("ADMIN_USERNAMES")
if _env_usernames:
    ADMIN_USERNAMES = [u.strip() for u in _env_usernames.split(",") if u.strip()]
else:
    ADMIN_USERNAMES = ["@nahoomac", "@abeba"]

ADMIN_USER_IDS = [
    int(x.strip()) 
    for x in os.environ.get("ADMIN_USER_IDS", "").split(",") 
    if x.strip().isdigit()
]

# Bot URL
IMAGE_ENHANCER_BOT_URL = "https://t.me/DV_IMAGE_ENHANCER_BOT"

# Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_ENABLED = False
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        GEMINI_ENABLED = True
    except ImportError:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            GEMINI_ENABLED = True
        except ImportError:
            print("Warning: Neither 'google-generativeai' nor 'google-genai' installed. Gemini features disabled.")
    except Exception as e:
        print(f"Warning: Failed to configure Gemini: {e}. Gemini features disabled.")

# --- Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Converters ---
try:
    converter = EthiopianDateConverter()
except (ImportError, NameError, Exception) as e:
    print(f"Warning: 'ethiopian-date' library not available ({e}). Date conversion will be skipped.")
    converter = None # Bot will run but skip date conversion

# --- Chapa Payment Gateway ---
CHAPA_SECRET_KEY = os.environ.get("CHAPA_SECRET_KEY", "").strip()
CHAPA_API_URL = os.environ.get("CHAPA_API_URL", "https://api.chapa.co/v1").rstrip("/")
CHAPA_ENABLED = bool(CHAPA_SECRET_KEY)
DV_SERVICE_FEE = int(os.environ.get("DV_SERVICE_FEE", 350))
SERVICE_FEE_AMOUNT = DV_SERVICE_FEE

# --- Bot Constants ---
KEYS_TO_PRESERVE_AFTER_FORM = [
    "language", "user_object", "surname", "given_name", "middle_name", "gender",
    "dob_ec", "dob_gc", "birth_city", "birth_country", "eligibility_country",
    "passport_number", "passport_issuance", "passport_expiration_ec", "passport_expiration_gc",
    "applicant_photo_id", "current_residence", "email", "phone", "education", "marital_status",
    "spouse_surname", "spouse_given_name", "spouse_middle_name", "spouse_gender",
    "spouse_dob_ec", "spouse_dob_gc", "spouse_birth_city", "spouse_birth_country",
    "spouse_photo_id", "children", "payment_screenshot_id",
    "payment_method", "payment_tx_ref", "payment_status"
]

# --- Load Database variables (Supports Neon DATABASE_URL and standalone PG) ---
DATABASE_URL = os.environ.get("DATABASE_URL")
DATABASE_URL_UNPOOLED = os.environ.get("DATABASE_URL_UNPOOLED", DATABASE_URL)
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")

if not DATABASE_URL and not all([DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME]):
    logger.warning("Database configuration missing in .env.")
    DB_HOST = None

# --- Neon Object Storage (S3-compatible) ---
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_ENDPOINT_URL_S3 = os.environ.get("AWS_ENDPOINT_URL_S3")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
STORAGE_BUCKET_NAME = os.environ.get("STORAGE_BUCKET_NAME", "assets")


# --- Photo Validation Constants ---
DV_MIN_PX = 600
DV_MAX_PX = 1200
DV_MAX_BYTES = 240 * 1024  # 240 KB
DV_ASPECT_TOLERANCE = 0.01
FACE_CENTER_TOLERANCE = 0.22
HAAR_MIN_FACE_SIZE = (80, 80)
HAAR_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"