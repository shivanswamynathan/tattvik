from langchain.schema import HumanMessage, SystemMessage
from typing import List, Dict, Any, Optional, Callable
import logging
from backend.core.llm import GeminiLLMWrapper
from backend.core.mongodb_client import MongoDBClient
from backend.models.schemas import SessionState
from backend.config import Config
from backend.prompts.revision_prompts import RevisionPrompts
from datetime import datetime
import random

logger = logging.getLogger(__name__)

class ProgressiveRevisionAgent:
    def __init__(self, llm_wrapper: GeminiLLMWrapper, mongodb_client: MongoDBClient):
        self.llm = llm_wrapper
        self.mongodb = mongodb_client
        self.session_states: Dict[str, SessionState] = {}
        self.prompts = RevisionPrompts()
        
        # Flow configuration - defines the revision flow pattern
        self.flow_config = {
            "stage_handlers": {
                "kickoff_response": self._handle_kickoff_response,
                "progressive_recap": self._handle_progressive_recap,
                "engaging_question": self._handle_engaging_question,
                "mini_quiz": self._handle_mini_quiz,
                "user_question": self._handle_user_question,
                "progress_check": self._handle_progress_check,
                "quiz_feedback": self._evaluate_quiz_answers,
                "general": self._handle_general_interaction
            },
            
            "stage_patterns": [
                {"stage": "kickoff_response", "condition": "conversation_count == 1"},
                {"stage": "user_question", "condition": "has_question_indicators"},
                {"stage": "mini_quiz", "condition": "conversation_count % 5 == 0 and conversation_count > 5"},
                {"stage": "engaging_question", "condition": "conversation_count % 3 == 0 and conversation_count > 2"},
                {"stage": "progress_check", "condition": "conversation_count % 8 == 0 and conversation_count > 8"},
                {"stage": "progressive_recap", "condition": "default"}
            ],
            
            "question_indicators": ["?", "what", "why", "how", "explain", "tell me", "help", "can you"],
            "session_end_phrases": ["end session", "finish", "complete", "done", "exit", "summary"]
        }
    
    async def start_revision_session(self, topic: str, student_id: str, session_id: str) -> dict:
        """Start a new revision session with topic kick-off."""
        
        # Get topic configuration
        topic_config = Config.get_topic_config(topic)
        max_conversations = topic_config["max_conversations"]
        completion_threshold = topic_config["completion_threshold"]
        
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
            user_understanding_level="beginner",
            max_conversations=max_conversations,
            completion_threshold=completion_threshold
        )
        self.session_states[session_id] = session_state

        # Get topic content and concept chunks
        topic_content, concept_chunks = self._initialize_topic_content(topic, session_state)
        
        # Generate kick-off response
        response = await self._generate_kickoff_response(topic, topic_content)
        
        # Save session to MongoDB
        self._save_initial_session(session_id, student_id, topic, response, concept_chunks, max_conversations, completion_threshold)

        return self._format_session_response(response, topic, session_id, 0, False, topic_content, "kickoff", max_conversations, completion_threshold)
    
    async def continue_revision(self, session_id: str, user_query: Optional[str] = None) -> Dict[str, Any]:
        """Continue revision with optimized flow handling"""
        
        # Load or restore session
        session_state = await self._get_or_restore_session(session_id)
        if not session_state:
            return {"response": "Session not found. Please start a new revision session.", "is_session_complete": False}
        
        # Update session state
        session_state.conversation_count += 1
        session_state.last_interaction = datetime.now()
        
        # Check for manual session end
        if self._should_end_session(user_query):
            return await self._complete_session(session_state)
        
        # Determine and handle current stage
        response_data = await self._process_revision_flow(session_state, user_query)
        
        # Save conversation and update progress
        await self._save_conversation_turn(session_state, user_query, response_data)
        
        # Add session metadata to response
        response_data.update({
            "topic": session_state.topic,
            "session_id": session_id,
            "conversation_count": session_state.conversation_count,
            "max_conversations": session_state.max_conversations or Config.get_max_conversations(session_state.topic),
            "completion_threshold": session_state.completion_threshold or Config.get_completion_threshold(session_state.topic)
        })
        
        return response_data
    
    def _initialize_topic_content(self, topic: str, session_state: SessionState) -> tuple:
        """Initialize topic content and concept chunks"""
        topic_content = self.mongodb.get_topic_content(topic, limit=3)
        concept_chunks = self.mongodb.get_topic_content_chunks(topic)
        session_state.concept_chunks = concept_chunks
        session_state.current_chunk_index = 0
        return topic_content, concept_chunks
    
    async def _generate_kickoff_response(self, topic: str, topic_content: List[Dict]) -> str:
        """Generate the initial kickoff response"""
        content_text = "\n".join([chunk["text"][:200] + "..." for chunk in topic_content])
        kickoff_prompt = self.prompts.get_topic_kickoff_prompt(topic, content_text)
        
        messages = [
            SystemMessage(content="You are an expert educational tutor starting a revision session."),
            HumanMessage(content=kickoff_prompt)
        ]
        
        return await self.llm.generate_response(messages)
    
    def _save_initial_session(self, session_id: str, student_id: str, topic: str, response: str, 
                             concept_chunks: List, max_conversations: int, completion_threshold: int):
        """Save initial session data to MongoDB"""
        session_data = {
            "session_id": session_id,
            "student_id": student_id,
            "topic": topic,
            "started_at": datetime.now(),
            "conversation_count": 0,
            "is_complete": False,
            "stage": "kickoff",
            "concept_chunks_total": len(concept_chunks),
            "current_chunk_index": 0,
            "max_conversations": max_conversations,
            "completion_threshold": completion_threshold,
            "conversation_history": [{
                "turn": 0,
                "type": "kickoff",
                "assistant_message": response,
                "timestamp": datetime.now()
            }]
        }
        self.mongodb.save_revision_session(session_data)
    
    def _format_session_response(self, response: str, topic: str, session_id: str, conversation_count: int,
                                is_complete: bool, sources: List, stage: str, max_conversations: int, 
                                completion_threshold: int) -> Dict[str, Any]:
        """Format standard session response"""
        return {
            "response": response,
            "topic": topic,
            "session_id": session_id,
            "conversation_count": conversation_count,
            "is_session_complete": is_complete,
            "session_summary": None,
            "sources": [chunk.get("chunk_id", "Unknown") for chunk in sources],
            "current_stage": stage,
            "max_conversations": max_conversations,
            "completion_threshold": completion_threshold
        }
    
    async def _get_or_restore_session(self, session_id: str) -> Optional[SessionState]:
        """Get existing session or restore from MongoDB"""
        if session_id in self.session_states:
            return self.session_states[session_id]
        
        # Try to restore from MongoDB
        session_data = self.mongodb.get_revision_session(session_id)
        if session_data:
            session_state = self._restore_session_state(session_data)
            self.session_states[session_id] = session_state
            return session_state
        
        return None
    
    def _should_end_session(self, user_query: Optional[str]) -> bool:
        """Check if user wants to end session"""
        if not user_query:
            return False
        
        user_query_lower = user_query.lower()
        return any(phrase in user_query_lower for phrase in self.flow_config["session_end_phrases"])
    
    async def _process_revision_flow(self, session_state: SessionState, user_query: Optional[str]) -> Dict[str, Any]:
        """Process revision flow using configuration-driven approach"""
        
        # Determine current stage using flow patterns
        current_stage = self._determine_stage_from_config(session_state, user_query)
        
        # Get and execute stage handler
        handler = self.flow_config["stage_handlers"].get(current_stage, self.flow_config["stage_handlers"]["general"])
        
        try:
            return await handler(session_state, user_query)
        except Exception as e:
            logger.error(f"Error in stage handler {current_stage}: {e}")
            return {
                "response": "I encountered an issue. Let me help you continue with your revision.",
                "current_stage": "general",
                "is_session_complete": False,
                "sources": []
            }
    
    def _determine_stage_from_config(self, session_state: SessionState, user_query: Optional[str]) -> str:
        """Determine stage using configuration patterns"""
        
        # Evaluate each pattern in order
        for pattern in self.flow_config["stage_patterns"]:
            if self._evaluate_stage_condition(pattern["condition"], session_state, user_query):
                return pattern["stage"]
        
        return "general"  # Default fallback
    
    def _evaluate_stage_condition(self, condition: str, session_state: SessionState, user_query: Optional[str]) -> bool:
        """Evaluate stage condition dynamically"""
        
        conversation_count = session_state.conversation_count
        
        # Handle different condition types
        condition_checks = {
            "conversation_count == 1": conversation_count == 1,
            "has_question_indicators": self._has_question_indicators(user_query),
            "conversation_count % 5 == 0 and conversation_count > 5": conversation_count % 5 == 0 and conversation_count > 5,
            "conversation_count % 3 == 0 and conversation_count > 2": conversation_count % 3 == 0 and conversation_count > 2,
            "conversation_count % 8 == 0 and conversation_count > 8": conversation_count % 8 == 0 and conversation_count > 8,
            "default": True
        }
        
        return condition_checks.get(condition, False)
    
    def _has_question_indicators(self, user_query: Optional[str]) -> bool:
        """Check if user query has question indicators"""
        if not user_query:
            return False
        
        user_query_lower = user_query.lower()
        return any(indicator in user_query_lower for indicator in self.flow_config["question_indicators"])
    
    async def _save_conversation_turn(self, session_state: SessionState, user_query: Optional[str], response_data: Dict[str, Any]):
        """Save conversation turn and update progress"""
        
        # Save conversation turn
        turn_data = {
            "turn": session_state.conversation_count,
            "user_message": user_query,
            "assistant_message": response_data["response"],
            "stage": response_data["current_stage"],
            "timestamp": datetime.now()
        }
        self.mongodb.save_conversation_turn(session_state.session_id, turn_data)
        
        # Update session progress
        progress_data = {
            "conversation_count": session_state.conversation_count,
            "current_stage": response_data["current_stage"],
            "current_chunk_index": getattr(session_state, 'current_chunk_index', 0),
            "concepts_covered": session_state.key_concepts_covered
        }
        self.mongodb.update_session_progress(session_state.session_id, progress_data)
    
    # =============== STAGE HANDLERS ===============
    
    async def _handle_kickoff_response(self, session_state: SessionState, user_query: str) -> Dict[str, Any]:
        """Handle user's response to kickoff"""
        
        # Determine revision mode
        revision_mode_indicators = ["quick", "recap", "summary", "brief", "short"]
        is_quick_recap = any(phrase in user_query.lower() for phrase in revision_mode_indicators)
        session_state.revision_mode = "quick_recap" if is_quick_recap else "deep_dive"
        
        # Initialize concept chunks if needed
        if not hasattr(session_state, 'concept_chunks'):
            session_state.concept_chunks = self.mongodb.get_topic_content_chunks(session_state.topic)
        
        session_state.current_chunk_index = 0
        
        if session_state.concept_chunks:
            first_chunk = session_state.concept_chunks[0]
            response = await self._generate_progressive_recap_response(session_state, first_chunk, 1, len(session_state.concept_chunks))
            
            # Track concept
            concept_name = self._extract_concept_name(first_chunk["text"])
            session_state.key_concepts_covered.append(concept_name)
            
            return {
                "response": response,
                "current_stage": "progressive_recap",
                "is_session_complete": False,
                "sources": [first_chunk.get("chunk_id", "Unknown")]
            }
        else:
            return {
                "response": "I'm having trouble loading the content for this topic. Let me help you with general questions instead!",
                "current_stage": "user_question",
                "is_session_complete": False,
                "sources": []
            }
    
    async def _handle_progressive_recap(self, session_state: SessionState, user_query: Optional[str]) -> Dict[str, Any]:
        """Handle progressive recap of concepts"""
        
        if not hasattr(session_state, 'current_chunk_index'):
            session_state.current_chunk_index = 0
        
        session_state.current_chunk_index += 1
        
        if (hasattr(session_state, 'concept_chunks') and 
            session_state.current_chunk_index < len(session_state.concept_chunks)):
            
            current_chunk = session_state.concept_chunks[session_state.current_chunk_index]
            total_chunks = len(session_state.concept_chunks)
            
            response = await self._generate_progressive_recap_response(session_state, current_chunk, session_state.current_chunk_index + 1, total_chunks)
            
            # Track concept
            concept_name = self._extract_concept_name(current_chunk["text"])
            if concept_name not in session_state.key_concepts_covered:
                session_state.key_concepts_covered.append(concept_name)
            
            return {
                "response": response,
                "current_stage": "progressive_recap",
                "is_session_complete": False,
                "sources": [current_chunk.get("chunk_id", "Unknown")]
            }
        else:
            return await self._handle_progress_check(session_state, None)
    
    async def _handle_engaging_question(self, session_state: SessionState, user_query: Optional[str]) -> Dict[str, Any]:
        """Handle engaging questions"""
        
        last_concept = session_state.key_concepts_covered[-1] if session_state.key_concepts_covered else session_state.topic
        
        # Determine difficulty
        difficulty_levels = ["easy", "medium", "hard"]
        difficulty_index = min(session_state.conversation_count // 6, 2)  # 0-5: easy, 6-11: medium, 12+: hard
        difficulty = difficulty_levels[difficulty_index]
        
        response = await self._generate_engaging_question_response(session_state.topic, last_concept, difficulty)
        
        # Set expectation for answer
        session_state.expecting_answer = True
        session_state.current_question_concept = last_concept
        
        return {
            "response": response,
            "current_stage": "engaging_question",
            "is_session_complete": False,
            "sources": []
        }
    
    async def _handle_mini_quiz(self, session_state: SessionState, user_query: Optional[str]) -> Dict[str, Any]:
        """Handle mini-quiz creation and evaluation"""
        
        # Check if evaluating previous quiz
        if hasattr(session_state, 'quiz_in_progress') and session_state.quiz_in_progress:
            return await self._evaluate_quiz_answers(session_state, user_query)
        
        # Create new quiz
        concepts_for_quiz = session_state.key_concepts_covered[-3:] if len(session_state.key_concepts_covered) >= 3 else session_state.key_concepts_covered
        if not concepts_for_quiz:
            concepts_for_quiz = [session_state.topic]
        
        num_questions = min(3, len(concepts_for_quiz))
        response = await self._generate_mini_quiz_response(session_state.topic, concepts_for_quiz, num_questions)
        
        # Mark quiz as in progress
        session_state.quiz_in_progress = True
        session_state.quiz_concepts = concepts_for_quiz
        
        return {
            "response": response,
            "current_stage": "mini_quiz",
            "is_session_complete": False,
            "sources": []
        }
    
    async def _handle_user_question(self, session_state: SessionState, user_query: str) -> Dict[str, Any]:
        """Handle user questions"""
        
        relevant_content = self.mongodb.search_topic_content(session_state.topic, user_query, limit=3)
        context = "\n".join([chunk["text"] for chunk in relevant_content]) if relevant_content else ""
        
        response = await self._generate_question_handling_response(user_query, session_state.topic, context)
        
        return {
            "response": response,
            "current_stage": "user_question",
            "is_session_complete": False,
            "sources": [chunk.get("chunk_id", "Unknown") for chunk in relevant_content]
        }
    
    async def _handle_progress_check(self, session_state: SessionState, user_query: Optional[str] = None) -> Dict[str, Any]:
        """Handle progress tracking"""
        
        total_concepts = len(session_state.concept_chunks) if hasattr(session_state, 'concept_chunks') else len(session_state.key_concepts_covered)
        concepts_completed = len(session_state.key_concepts_covered)
        
        percentage = (concepts_completed / total_concepts * 100) if total_concepts > 0 else (session_state.conversation_count / session_state.completion_threshold * 100)
        
        response = await self._generate_progress_tracking_response(session_state.topic, concepts_completed, total_concepts, percentage)
        
        # Check completion
        completion_threshold = session_state.completion_threshold or Config.get_completion_threshold(session_state.topic)
        
        if (percentage >= 90 or concepts_completed >= total_concepts or session_state.conversation_count >= completion_threshold):
            return await self._complete_session(session_state)
        
        return {
            "response": response,
            "current_stage": "progress_check",
            "is_session_complete": False,
            "sources": [],
            "progress_percentage": percentage
        }
    
    async def _evaluate_quiz_answers(self, session_state: SessionState, user_answer: str) -> Dict[str, Any]:
        """Evaluate quiz answers"""
        
        session_state.quiz_in_progress = False
        
        feedback_prompt = f"""
        Provide encouraging feedback for a student's quiz attempt in the topic "{session_state.topic}".
        Student's response: "{user_answer}"
        Quiz concepts: {getattr(session_state, 'quiz_concepts', [])}
        
        Provide encouraging feedback, brief explanation, and motivation with emojis.
        """
        
        messages = [
            SystemMessage(content="You are an expert educational tutor providing quiz feedback."),
            HumanMessage(content=feedback_prompt)
        ]
        
        response = await self.llm.generate_response(messages)
        
        return {
            "response": response,
            "current_stage": "quiz_feedback",
            "is_session_complete": False,
            "sources": []
        }
    
    async def _handle_general_interaction(self, session_state: SessionState, user_query: Optional[str]) -> Dict[str, Any]:
        """Handle general interactions"""
        return await self._handle_progressive_recap(session_state, user_query)
    

    
    async def _generate_progressive_recap_response(self, session_state: SessionState, chunk: Dict, chunk_num: int, total_chunks: int) -> str:
        """Generate progressive recap response"""
        prompt = self.prompts.get_progressive_recap_prompt(session_state.topic, chunk["text"], chunk_num, total_chunks)
        messages = [
            SystemMessage(content="You are an expert educational tutor providing progressive concept explanation."),
            HumanMessage(content=prompt)
        ]
        return await self.llm.generate_response(messages)
    
    async def _generate_engaging_question_response(self, topic: str, concept: str, difficulty: str) -> str:
        """Generate engaging question response"""
        prompt = self.prompts.get_engaging_question_prompt(topic, concept, difficulty)
        messages = [
            SystemMessage(content="You are an expert educational tutor creating engaging questions."),
            HumanMessage(content=prompt)
        ]
        return await self.llm.generate_response(messages)
    
    async def _generate_mini_quiz_response(self, topic: str, concepts: List[str], num_questions: int) -> str:
        """Generate mini quiz response"""
        prompt = self.prompts.get_mini_quiz_prompt(topic, concepts, num_questions)
        messages = [
            SystemMessage(content="You are an expert educational tutor creating mini-quizzes."),
            HumanMessage(content=prompt)
        ]
        return await self.llm.generate_response(messages)
    
    async def _generate_question_handling_response(self, user_query: str, topic: str, context: str) -> str:
        """Generate question handling response"""
        prompt = self.prompts.get_question_handling_prompt(user_query, topic, context)
        messages = [
            SystemMessage(content="You are an expert educational tutor answering student questions."),
            HumanMessage(content=prompt)
        ]
        return await self.llm.generate_response(messages)
    
    async def _generate_progress_tracking_response(self, topic: str, concepts_completed: int, total_concepts: int, percentage: float) -> str:
        """Generate progress tracking response"""
        prompt = self.prompts.get_progress_tracking_prompt(topic, concepts_completed, total_concepts, percentage)
        messages = [
            SystemMessage(content="You are an expert educational tutor providing progress updates."),
            HumanMessage(content=prompt)
        ]
        return await self.llm.generate_response(messages)
    
    # =============== HELPER METHODS ===============
    
    def _extract_concept_name(self, text: str) -> str:
        """Extract concept name from text"""
        words = text.split()
        if len(words) >= 3:
            return " ".join(words[:3])
        return text[:50] + "..." if len(text) > 50 else text
    
    def _restore_session_state(self, session_data: Dict[str, Any]) -> SessionState:
        """Restore session state from MongoDB data"""
        
        session_state = SessionState(
            session_id=session_data["session_id"],
            topic=session_data["topic"],
            student_id=session_data["student_id"],
            conversation_count=session_data.get("conversation_count", 0),
            started_at=session_data["started_at"],
            last_interaction=session_data.get("updated_at", datetime.now()),
            is_complete=session_data.get("is_complete", False),
            key_concepts_covered=session_data.get("concepts_covered", []),
            user_understanding_level="beginner",
            max_conversations=session_data.get("max_conversations"),
            completion_threshold=session_data.get("completion_threshold")
        )
        
        # Restore additional attributes
        session_state.current_chunk_index = session_data.get("current_chunk_index", 0)
        
        # Get concept chunks if not stored
        if not hasattr(session_state, 'concept_chunks'):
            session_state.concept_chunks = self.mongodb.get_topic_content_chunks(session_state.topic)
        
        return session_state
    
    async def _complete_session(self, session_state: SessionState) -> Dict[str, Any]:
        """Complete revision session with conclusion"""
        
        session_state.is_complete = True
        
        # Calculate statistics
        session_stats = {
            "total_interactions": session_state.conversation_count,
            "concepts_covered": len(session_state.key_concepts_covered),
            "duration_minutes": (datetime.now() - session_state.started_at).total_seconds() / 60,
            "completion_rate": min(100, session_state.conversation_count / session_state.completion_threshold * 100) if session_state.completion_threshold else 100
        }
        
        # Generate conclusion
        conclusion_prompt = self.prompts.get_conclusion_prompt(session_state.topic, session_state.key_concepts_covered, session_stats)
        messages = [
            SystemMessage(content="You are an expert educational tutor providing session conclusion."),
            HumanMessage(content=conclusion_prompt)
        ]
        summary = await self.llm.generate_response(messages)
        
        # Update session in MongoDB
        final_session_data = {
            "is_complete": True,
            "completed_at": datetime.now(),
            "final_stats": session_stats,
            "session_summary": summary,
            "concepts_covered": session_state.key_concepts_covered
        }
        self.mongodb.update_session_progress(session_state.session_id, final_session_data)
        
        return {
            "response": summary,
            "topic": session_state.topic,
            "session_id": session_state.session_id,
            "conversation_count": session_state.conversation_count,
            "is_session_complete": True,
            "session_summary": summary,
            "next_suggested_action": f"Great work! You can explore related topics or review {session_state.topic} again anytime!",
            "sources": [],
            "session_stats": session_stats
        }