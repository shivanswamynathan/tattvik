from langchain.schema import HumanMessage, SystemMessage
from typing import List, Dict, Any, Optional
import logging
from backend.core.llm import GeminiLLMWrapper
from backend.core.mongodb_client import MongoDBClient
from backend.models.schemas import SessionState
from backend.config import Config
from datetime import datetime

logger = logging.getLogger(__name__)

class ProgressiveRevisionAgent:
    async def start_revision_session(
        self,
        topic: str,
        student_id: str,
        session_id: str
    ) -> dict:
        """Start a new revision session for a topic."""
        from backend.models.schemas import SessionState
        from datetime import datetime

        # Create new session state
        session_state = SessionState(
            session_id=session_id,
            topic=topic,
            student_id=student_id,
            conversation_count=0,
            started_at=datetime.now(),
            last_interaction=datetime.now(),
            is_complete=False,
            key_concepts_covered=[],
            user_understanding_level="beginner"
        )
        self.session_states[session_id] = session_state

        # Get initial topic content
        topic_content = self.mongodb.get_topic_content(topic, limit=3)
        context = "\n".join([chunk["text"] for chunk in topic_content])
        stage = self._get_learning_stage(0)

        response = await self._generate_stage_appropriate_response(
            session_state, None, context, stage
        )

        return {
            "response": response,
            "topic": topic,
            "session_id": session_id,
            "conversation_count": 0,
            "is_session_complete": False,
            "session_summary": None,
            "sources": [chunk.get("chunk_id", "Unknown") for chunk in topic_content],
            "current_stage": stage
        }
    def __init__(self, llm_wrapper: GeminiLLMWrapper, mongodb_client: MongoDBClient):
        self.llm = llm_wrapper
        self.mongodb = mongodb_client
        self.session_states: Dict[str, SessionState] = {}
    
    async def continue_revision(
        self,
        session_id: str,
        user_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """Continue an existing revision session - NOW UNLIMITED!"""
        
        if session_id not in self.session_states:
            return {
                "response": "Session not found. Please start a new revision session.",
                "is_session_complete": False,  # Changed: Never auto-complete
                "session_summary": None
            }
        
        session_state = self.session_states[session_id]
        session_state.conversation_count += 1
        session_state.last_interaction = datetime.now()
        
        # REMOVED: No more automatic session completion based on count
        # OLD CODE: if session_state.conversation_count >= 20:
        #              return await self._complete_session(session_state)
        
        # Get relevant content
        if user_query:
            topic_content = self.mongodb.search_topic_content(
                session_state.topic, 
                user_query, 
                limit=3
            )
        else:
            topic_content = self.mongodb.get_topic_content(
                session_state.topic, 
                limit=3
            )
        
        context = "\n".join([chunk["text"] for chunk in topic_content])
        
        # Determine revision stage based on conversation count (but no limits!)
        stage = self._get_learning_stage(session_state.conversation_count)
        
        # Check if user wants to end session manually
        if user_query and any(phrase in user_query.lower() for phrase in 
                             ["end session", "finish", "complete", "done", "exit", "summary"]):
            return await self._complete_session(session_state)
        
        response = await self._generate_stage_appropriate_response(
            session_state, user_query, context, stage
        )
        
        return {
            "response": response,
            "topic": session_state.topic,
            "session_id": session_id,
            "conversation_count": session_state.conversation_count,
            "is_session_complete": False,  # Never auto-complete now
            "session_summary": None,
            "sources": [chunk.get("chunk_id", "Unknown") for chunk in topic_content],
            "current_stage": stage
        }
    
    def _get_learning_stage(self, conversation_count: int) -> str:
        """Determine learning stage - now with unlimited progression"""
        if conversation_count <= 5:
            return "introduction"
        elif conversation_count <= Config.TOPIC_COMPLETION_THRESHOLD:
            return "deep_learning"
        elif conversation_count <= 25:  # Extended consolidation phase
            return "consolidation"
        elif conversation_count <= 40:  # Advanced exploration
            return "advanced_exploration"
        else:  # Mastery level - unlimited
            return "mastery_discussion"
    
    async def _generate_stage_appropriate_response(
        self,
        session_state: SessionState,
        user_query: Optional[str],
        context: str,
        stage: str
    ) -> str:
        """Generate response appropriate for the current revision stage"""
        
        stage_prompts = {
            "introduction": f"""
            You are in the introduction stage of revision for "{session_state.topic}".
            Conversation #{session_state.conversation_count}
            
            Context: {context}
            User's input: {user_query or "Continue with basic concepts"}
            
            At this stage:
            1. Focus on fundamental concepts and definitions
            2. Use simple explanations and examples
            3. Check understanding with easy questions
            4. Build confidence and interest
            5. If user asks questions, answer them clearly and encourage more questions
            
            Provide an engaging explanation and ask a follow-up question to test understanding.
            """,
            
            "deep_learning": f"""
            You are in the deep learning stage of revision for "{session_state.topic}".
            Conversation #{session_state.conversation_count}
            
            Context: {context}
            User's input: {user_query or "Continue with deeper concepts"}
            
            At this stage:
            1. Dive deeper into concepts and relationships
            2. Provide detailed explanations and examples
            3. Ask analytical questions that test comprehension
            4. Connect concepts to real-world applications
            5. If user asks questions, provide comprehensive answers and probe deeper
            
            Provide detailed explanations and ask thought-provoking questions.
            """,
            
            "consolidation": f"""
            You are in the consolidation stage of revision for "{session_state.topic}".
            Conversation #{session_state.conversation_count}
            
            Context: {context}
            User's input: {user_query or "Help me consolidate my learning"}
            
            At this stage:
            1. Summarize key concepts
            2. Test comprehensive understanding
            3. Help identify knowledge gaps
            4. Connect all learned concepts together
            5. If user asks questions, help them see the bigger picture
            
            Focus on synthesis and connecting all concepts together.
            """,
            
            "advanced_exploration": f"""
            You are in the advanced exploration stage for "{session_state.topic}".
            Conversation #{session_state.conversation_count}
            
            Context: {context}
            User's input: {user_query or "Let's explore advanced aspects"}
            
            At this stage:
            1. Explore advanced concepts and edge cases
            2. Discuss latest developments or research
            3. Challenge the student with complex scenarios
            4. Encourage critical analysis and evaluation
            5. Connect to other subjects and broader implications
            
            Provide advanced insights and challenge critical thinking.
            """,
            
            "mastery_discussion": f"""
            You are in the mastery discussion stage for "{session_state.topic}".
            Conversation #{session_state.conversation_count}
            
            Context: {context}
            User's input: {user_query or "Let's discuss at mastery level"}
            
            At this stage:
            1. Engage in expert-level discussions
            2. Explore cutting-edge research and applications
            3. Encourage the student to teach concepts back
            4. Discuss controversies, debates, and open questions
            5. Help student become a subject matter expert
            
            Engage at an expert level and encourage deep mastery.
            Note: The student can continue this conversation indefinitely. If they want to end, 
            they can say "end session" or "summary".
            """
        }
        
        messages = [
            SystemMessage(content="You are an expert educational tutor conducting unlimited progressive revision."),
            HumanMessage(content=stage_prompts[stage])
        ]
        
        return await self.llm.generate_response(messages)
    
    async def _complete_session(self, session_state: SessionState) -> Dict[str, Any]:
        """Complete the revision session - only when user requests it"""
        
        session_state.is_complete = True
        
        # Generate session summary
        summary_prompt = f"""
        Create a comprehensive conclusion for a revision session on "{session_state.topic}" 
        that lasted {session_state.conversation_count} interactions.
        
        The student chose to end the session, so provide:
        1. Congratulations on their dedication ({session_state.conversation_count} interactions!)
        2. Summary of key concepts covered
        3. Acknowledgment of their commitment to learning
        4. Suggestions for continued exploration
        5. Encouragement for future learning
        6. Option to restart session anytime for deeper exploration
        
        Make it encouraging and highlight that they can always continue learning more.
        """
        
        messages = [
            SystemMessage(content="You are an expert educational tutor providing a session conclusion."),
            HumanMessage(content=summary_prompt)
        ]
        
        summary = await self.llm.generate_response(messages)
        
        return {
            "response": summary,
            "topic": session_state.topic,
            "session_id": session_state.session_id,
            "conversation_count": session_state.conversation_count,
            "is_session_complete": True,
            "session_summary": summary,
            "next_suggested_action": "Feel free to start a new session anytime to explore more topics or dive deeper into this one!",
            "sources": []
        }