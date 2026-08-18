import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Loyiha ildiz katalogi (mutlaq yo'l)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Get the bot token from environment variable. Raise a clear error if missing.
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set. Please define it in the .env file or environment variables.")

# Load admin IDs from environment variable, with a default fallback
admin_ids_raw = os.getenv("ADMIN_IDS", "8781024332")
ADMIN_IDS = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip().isdigit()]

DB_DIR = "db"
DB_FILE = os.path.join(DB_DIR, "questions.json")
TEST_SOURCE_URL = os.getenv("TEST_SOURCE_URL", "https://osonprava.uz/api/tests")
SQLITE_DB_FILE = os.path.join(DB_DIR, "database.sqlite")
REQUIRED_SUB_CHANNEL = "@your_channel_username"  # Bot foydalanuvchilaridan ushbu kanalga obuna bo‘lishni talab qiladi
