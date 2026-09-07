import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    
    # Vision models
    GROQ_VISION_MODEL: str = os.environ.get("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")
    GROQ_TEXT_MODEL: str = os.environ.get("GROQ_TEXT_MODEL", "llama-3.3-70b-versatile")
    
    # Database
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./bills.db")
    
    # App
    BASE_URL: str = os.environ.get("BASE_URL", "http://localhost:8000")
    FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    
    # Force mock extractor flag (for offline tests/CI)
    FORCE_MOCK_EXTRACTOR: bool = os.environ.get("FORCE_MOCK_EXTRACTOR", "").lower() in ("true", "1", "yes")


settings = Settings()
