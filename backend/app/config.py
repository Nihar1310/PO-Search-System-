import os
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    OPENAI_API_KEY: str
    OPENAI_MODEL: str
    DATABASE_URL: str
    REDIRECT_URI: str
    GOOGLE_TOKEN_PATH: str
    GOOGLE_SCOPES: str
    GOOGLE_CLIENT_SECRETS_FILE: str

    def __init__(self) -> None:
        self.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
        self.GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./po_cache.db")
        self.REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/auth/callback")
        self.GOOGLE_TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "token.json")
        # Comma-separated scopes override default if provided
        self.GOOGLE_SCOPES = os.getenv(
            "GOOGLE_SCOPES",
            "https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/drive.readonly",
        )
        self.GOOGLE_CLIENT_SECRETS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS_FILE", "")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
