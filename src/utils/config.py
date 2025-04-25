import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-2024-08-06")

# UI Configuration
UI_CONFIG = {
    "page_title": "AI Chat Assistant",
    "initial_sidebar_state": "expanded",
    "available_models": [
        "gpt-4o-2024-11-20",
        "gpt-4.1-mini-2025-04-14",
        "gpt-4.1-nano-2025-04-14",
        "o3-mini-2025-01-31",
        "o4-mini-2025-04-16",
    ]
} 