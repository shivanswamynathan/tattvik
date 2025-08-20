from pymongo import MongoClient
from typing import List, Dict, Any, Optional
import logging
from backend.config import Config

logger = logging.getLogger(__name__)

class MongoDBClient:
    def __init__(self):
        self.client = MongoClient(Config.MONGODB_URI)
        self.db = self.client[Config.DATABASE_NAME]
        self.collection = self.db[Config.COLLECTION_NAME]
    
    def get_available_topics(self) -> List[Dict[str, Any]]:
        """Fetch all available topics from MongoDB"""
        try:
            # Get distinct topics
            topics = self.collection.distinct("topic")
            
            # Get topic details with counts
            topic_details = []
            for topic in topics:
                count = self.collection.count_documents({"topic": topic})
                topic_details.append({
                    "topic": topic,
                    "chunk_count": count,
                    "description": f"Study material with {count} content sections"
                })
            
            return topic_details
        except Exception as e:
            logger.error(f"Error fetching topics: {e}")
            return []
    
    def get_topic_content(self, topic: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get content chunks for a specific topic"""
        try:
            cursor = self.collection.find(
                {"topic": topic},
                {"text": 1, "chunk_id": 1, "topic": 1, "_id": 0}
            ).limit(limit)
            
            return list(cursor)
        except Exception as e:
            logger.error(f"Error fetching topic content: {e}")
            return []
    
    def search_topic_content(self, topic: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search within topic content using text search"""
        try:
            # Simple text search within topic
            cursor = self.collection.find(
                {
                    "topic": topic,
                    "$text": {"$search": query}
                },
                {"text": 1, "chunk_id": 1, "topic": 1, "score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            results = list(cursor)
            
            # If no text search results, fall back to regex search
            if not results:
                cursor = self.collection.find(
                    {
                        "topic": topic,
                        "text": {"$regex": query, "$options": "i"}
                    },
                    {"text": 1, "chunk_id": 1, "topic": 1}
                ).limit(limit)
                results = list(cursor)
            
            return results
        except Exception as e:
            logger.error(f"Error searching topic content: {e}")
            return []