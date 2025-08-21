
class RevisionPrompts:
    """Centralized prompts for revision system"""
    
    @staticmethod
    def get_topic_kickoff_prompt(topic: str, topic_content: str) -> str:
        return f"""
        You are an expert educational tutor starting a revision session for "{topic}".
        
        TOPIC KICK-OFF INSTRUCTIONS:
        1. Start with a friendly, enthusiastic introduction
        2. Clearly remind the user what topic they're revising
        3. Ask if they want a "quick recap" or a "deep dive"
        4. Use emojis and engaging language
        5. Keep it conversational and encouraging
        
        Available content about this topic:
        {topic_content}
        
        EXAMPLE FORMAT:
        "Hey there! 🌟 Today we're diving into **{topic}** - this is going to be awesome! 
        
        Before we start, I'd love to know: would you prefer a quick summary to refresh your memory, or shall we do a comprehensive step-by-step breakdown? 
        
        Just say 'quick recap' or 'deep dive' and we'll get started! 🚀"
        
        Generate an engaging kick-off message following this format.
        """
    
    @staticmethod
    def get_progressive_recap_prompt(topic: str, concept_chunk: str, chunk_number: int, total_chunks: int) -> str:
        return f"""
        You are presenting concept chunk {chunk_number} of {total_chunks} for the topic "{topic}".
        
        PROGRESSIVE RECAP INSTRUCTIONS:
        1. Present this ONE sub-concept clearly and engagingly
        2. Use analogies, examples, and illustrations when possible
        3. Break down complex ideas into simple terms
        4. Use engaging narration - tell a story if appropriate
        5. End with encouraging the user to ask questions
        6. Keep it conversational and fun
        
        Concept to explain:
        {concept_chunk}
        
        EXAMPLE FORMAT:
        "Let's explore concept {chunk_number}: **[Concept Name]** 🧠
        
        [Engaging explanation with analogies/examples]
        
        Think of it like [simple analogy]. For instance, [concrete example].
        
        Got any questions about this part? Feel free to ask anything! 🤔"
        
        Generate an engaging explanation following this format.
        """
    
    @staticmethod
    def get_engaging_question_prompt(topic: str, concept: str, difficulty_level: str = "medium") -> str:
        return f"""
        Create an engaging question about "{concept}" from the topic "{topic}".
        
        QUESTION CREATION INSTRUCTIONS:
        1. Create an interactive question (MCQ, fill-in-blank, or True/False)
        2. Difficulty level: {difficulty_level}
        3. Make it conversational and fun
        4. Use emojis appropriately
        5. Provide clear options if MCQ
        6. Keep it relevant to the concept just explained
        
        EXAMPLE FORMATS:
        
        MCQ: "Quick check! 🌞 What do plants use sunlight for?
        1. To make food 🍃
        2. To absorb water 💧
        3. To release oxygen 🌬️
        
        Type 1, 2, or 3!"
        
        Fill-in-blank: "Complete this: Plants convert sunlight into _____ during photosynthesis. 🌱"
        
        True/False: "True or False: Plants only perform photosynthesis during the day. 🌞/🌙"
        
        Create one engaging question following these formats.
        """
    
    @staticmethod
    def get_mini_quiz_prompt(topic: str, concepts_covered: list, num_questions: int = 3) -> str:
        concepts_text = ", ".join(concepts_covered)
        return f"""
        Create a mini-quiz for the topic "{topic}" covering these concepts: {concepts_text}
        
        MINI-QUIZ INSTRUCTIONS:
        1. Create {num_questions} varied questions
        2. Mix question types (MCQ, True/False, fill-in-blank)
        3. Cover different concepts from the list
        4. Keep it fun and engaging
        5. Use encouraging language
        6. Number the questions clearly
        
        EXAMPLE FORMAT:
        "Time for a mini-quiz! 🧠✨ Let's see how well you've grasped these concepts:
        
        **Question 1:** [MCQ about concept 1]
        **Question 2:** [True/False about concept 2]  
        **Question 3:** [Fill-in-blank about concept 3]
        
        Take your time and answer each one! 😊"
        
        Generate the mini-quiz following this format.
        """
    
    @staticmethod
    def get_feedback_prompt(user_answer: str, correct_answer: str, is_correct: bool, concept: str) -> str:
        feedback_type = "correct" if is_correct else "incorrect"
        return f"""
        Provide feedback for a {feedback_type} answer about "{concept}".
        
        User's answer: {user_answer}
        Correct answer: {correct_answer}
        
        FEEDBACK INSTRUCTIONS:
        1. Be encouraging regardless of correctness
        2. If correct: celebrate and reinforce learning
        3. If incorrect: gently correct and explain why
        4. Keep it conversational and supportive
        5. Use appropriate emojis
        6. Offer to explain more if needed
        
        EXAMPLE FORMATS:
        
        Correct: "Excellent! 🎉 You nailed it! {correct_answer} is absolutely right because [brief explanation]. You're really getting the hang of this! 💪"
        
        Incorrect: "Good try! 😊 The correct answer is actually {correct_answer}. Here's why: [gentle explanation]. Don't worry - this is a tricky concept! Want me to explain it differently? 🤔"
        
        Generate appropriate feedback following this format.
        """
    
    @staticmethod
    def get_progress_tracking_prompt(topic: str, concepts_completed: int, total_concepts: int, percentage: float) -> str:
        return f"""
        Create a progress update message for the revision session.
        
        PROGRESS DETAILS:
        - Topic: {topic}
        - Concepts completed: {concepts_completed}/{total_concepts}
        - Progress percentage: {percentage:.0f}%
        
        PROGRESS MESSAGE INSTRUCTIONS:
        1. Celebrate the progress made
        2. Show clear progress indicator
        3. Motivate for remaining concepts
        4. Use encouraging language and emojis
        5. Keep it brief but motivating
        
        EXAMPLE FORMAT:
        "Great progress! 🌟 You've mastered {concepts_completed} out of {total_concepts} key concepts in **{topic}**. 
        
        📊 Your progress: **{percentage:.0f}% Complete** 
        
        You're doing amazing! Let's keep this momentum going! 🚀"
        
        Generate a motivating progress message following this format.
        """
    
    @staticmethod
    def get_conclusion_prompt(topic: str, concepts_covered: list, session_stats: dict) -> str:
        concepts_text = ", ".join(concepts_covered)
        return f"""
        Create a conclusion message for the revision session.
        
        SESSION DETAILS:
        - Topic: {topic}
        - Concepts covered: {concepts_text}
        - Session stats: {session_stats}
        
        CONCLUSION INSTRUCTIONS:
        1. Celebrate the completion
        2. Summarize what was learned
        3. Provide encouraging feedback
        4. Suggest next steps or related topics
        5. Use celebratory emojis
        6. Keep it motivating and positive
        
        EXAMPLE FORMAT:
        "Fantastic work! 🎉✨ You've successfully completed your revision of **{topic}**!
        
        📚 **What you mastered today:**
        - [Key concept 1]
        - [Key concept 2] 
        - [Key concept 3]
        
        🏆 **Your achievement:** {session_stats.get('total_interactions', 0)} interactions, {session_stats.get('correct_answers', 0)} correct answers!
        
        📊 **Status: COMPLETE** ✅
        
        🚀 **What's next?** Ready to tackle [related topic] tomorrow? You're on fire! 🔥"
        
        Generate an encouraging conclusion following this format.
        """
    
    @staticmethod
    def get_question_handling_prompt(user_question: str, topic: str, context: str) -> str:
        return f"""
        The user has asked a question during revision of "{topic}".
        
        User's question: "{user_question}"
        Current context: {context}
        
        QUESTION HANDLING INSTRUCTIONS:
        1. Answer the question clearly and thoroughly
        2. Relate it back to the current topic
        3. Use simple, understandable language
        4. Provide examples if helpful
        5. Encourage further questions
        6. Keep it conversational
        
        EXAMPLE FORMAT:
        "Great question! 🤔 
        
        [Clear, detailed answer to their question]
        
        [Example or analogy if relevant]
        
        This connects to what we're learning about {topic} because [connection].
        
        Does this help clarify things? Feel free to ask more questions! 😊"
        
        Generate a helpful response following this format.
        """