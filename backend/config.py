import os
from dotenv import load_dotenv
from typing import Optional, Dict

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
    REVISION_COLLECTION: str = "revision_sessions" 
    
    DEFAULT_MAX_CONVERSATIONS: int = 25
    DEFAULT_COMPLETION_THRESHOLD: int = 15 

    TOPIC_CONFIGURATIONS: Dict[str, Dict[str, int]] = {
        # Format: "topic_name": {"max_conversations": X, "completion_threshold": Y}
        "photosynthesis": {
            "max_conversations": 30,
            "completion_threshold": 20
        },
        "respiration": {
            "max_conversations": 25,
            "completion_threshold": 15
        },
        "cell_structure": {
            "max_conversations": 35,
            "completion_threshold": 25
        },
        "nutrition": {
            "max_conversations": 20,
            "completion_threshold": 12
        },
        # Add more topics as needed
    }
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @classmethod
    def get_topic_config(cls, topic: str) -> Dict[str, int]:
        """Get configuration for a specific topic"""
        topic_lower = topic.lower().strip()
        
        # Check exact match first
        if topic_lower in cls.TOPIC_CONFIGURATIONS:
            return cls.TOPIC_CONFIGURATIONS[topic_lower]
        
        # Check partial matches
        for config_topic, config in cls.TOPIC_CONFIGURATIONS.items():
            if config_topic in topic_lower or topic_lower in config_topic:
                return config
        
        # Return default configuration
        return {
            "max_conversations": cls.DEFAULT_MAX_CONVERSATIONS,
            "completion_threshold": cls.DEFAULT_COMPLETION_THRESHOLD
        }
    
    @classmethod
    def get_max_conversations(cls, topic: str) -> int:
        """Get max conversations for a specific topic"""
        config = cls.get_topic_config(topic)
        return config["max_conversations"]
    
    @classmethod
    def get_completion_threshold(cls, topic: str) -> int:
        """Get completion threshold for a specific topic"""
        config = cls.get_topic_config(topic)
        return config["completion_threshold"]
    
    @classmethod
    def validate_config(cls):
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required")
        if not cls.MONGODB_URI:
            raise ValueError("MONGODB_URI is required")