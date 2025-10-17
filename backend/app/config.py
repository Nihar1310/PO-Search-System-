import os
from functools import lru_cache
from typing import List

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
    FRONTEND_ORIGINS: List[str]
    DOCAI_PROJECT_ID: str
    DOCAI_LOCATION: str
    DOCAI_PROCESSOR_ID: str
    DOCAI_PROCESSOR_VERSION: str
    DOCAI_API_ENDPOINT: str

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
        raw_origins = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173")
        self.FRONTEND_ORIGINS = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        self.DOCAI_PROJECT_ID = os.getenv("DOCAI_PROJECT_ID", "")
        self.DOCAI_LOCATION = os.getenv("DOCAI_LOCATION", "us")
        self.DOCAI_PROCESSOR_ID = os.getenv("DOCAI_PROCESSOR_ID", "")
        self.DOCAI_PROCESSOR_VERSION = os.getenv("DOCAI_PROCESSOR_VERSION", "")
        self.DOCAI_API_ENDPOINT = os.getenv("DOCAI_API_ENDPOINT", "")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
