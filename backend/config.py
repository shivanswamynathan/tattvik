import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Config:
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Model Settings
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # MongoDB Settings
    MONGODB_URI: str = "mongodb+srv://haswath1810:haswath18@cluster0.tkjt0ke.mongodb.net/?retryWrites=true&w=majority"
    DATABASE_NAME: str = "ncert_class8"
    COLLECTION_NAME: str = "chapter1"
    
    MAX_CONVERSATIONS_PER_SESSION: int = -1  
    TOPIC_COMPLETION_THRESHOLD: int = 15 
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    @classmethod
    def validate_config(cls):
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required")
        if not cls.MONGODB_URI:
            raise ValueError("MONGODB_URI is required")