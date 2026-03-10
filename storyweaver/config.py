import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY  = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL             = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Generation temperature settings
GENERATION_TEMPERATURE  = 0.8
INTENT_TEMPERATURE      = 0.1
CONSISTENCY_TEMPERATURE = 0.2
CHOICE_TEMPERATURE      = 0.9

# Context window
MAX_HISTORY_TURNS = 8
CONTEXT_TURNS     = 3

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not DEEPSEEK_API_KEY:
            raise ValueError(
                "DEEPSEEK_API_KEY is not set. "
                "Please copy .env.example to .env and fill in your key."
            )
        _client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
    return _client
