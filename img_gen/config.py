# img_gen/config.py
import sys
from pathlib import Path
import os
from dotenv import load_dotenv
from groq import Groq
from google import genai

# --------------------------------------------------
# ENVIRONMENT & CLIENTS
# --------------------------------------------------
if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).resolve().parent   # folder containing Traybakes.exe
else:
    APP_ROOT = Path(__file__).resolve().parent.parent   # project root in dev mode
load_dotenv(APP_ROOT / ".env")

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# --------------------------------------------------
# PATHS
# --------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PRODUCTS_DIR = os.path.join(
    BASE_DIR,
    "products"
)

OUTPUTS_DIR = os.path.join(
    BASE_DIR,
    "outputs"
)

os.makedirs(
    OUTPUTS_DIR,
    exist_ok=True
)

# --------------------------------------------------
# MODELS & LIMITS
# --------------------------------------------------

IMAGE_PROMPT_MODEL = "openai/gpt-oss-120b"
PRODUCT_SELECTOR_MODEL = "openai/gpt-oss-20b"
IMAGE_GEN_MODEL = "gemini-3.1-flash-image"

MAX_PRODUCT_IMAGES = 4
MIN_MATCH_SCORE = 0.5

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2