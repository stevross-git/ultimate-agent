#!/usr/bin/env python3
"""
ultimate_agent/ai/chat/conversation_manager.py
Advanced conversational AI backend for the chat interface
"""

import time
import json
import uuid
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import threading
from collections import deque, defaultdict


class ConversationManager:
    """Manages AI conversations and chat sessions"""
    
    def __init__(self, ai_manager, config_manager):
        self.ai_manager = ai_manager
        self.config = config_manager
        self.conversations = {}
        self.user_sessions = {}
        self.chat_history = deque(maxlen=10000)
        
        # Conversation settings
        self.max_context_length = 4000
        self.context_memory_enabled = True
        self.response_creativity = 0.7
        self.conversation_timeout = 3600  # 1 hour

        # Rate limiting
        self.user_message_counts = defaultdict(lambda: {'count': 0, 'reset_time': time.time()})
        self.rate_limit_messages = 100
        self.rate_limit_window = 3600
        
        # Advanced chat responses
        self.personality_traits = {
            'helpful': 0.9,
            'friendly': 0.8,
            'professional': 0.7,
            'creative': 0.6,
            'technical': 0.8
        }
        
        self.conversation_templates = {
            'greeting': [
                "Hello! I'm your personal AI assistant. How can I help you today?",
                "Hi there! I'm here to assist you with anything you need. What's on your mind?",
                "Welcome! I'm ready to help with questions, creative tasks, or just have a conversation.",
                "Hello! As your local AI assistant, I'm here to help with whatever you need."
            ],
            'clarification': [
                "Could you provide more details about what you're looking for?",
                "I'd be happy to help! Can you tell me more about your specific needs?",
                "That's interesting! What particular aspect would you like to explore?",
                "I want to give you the best answer possible. Could you elaborate a bit more?"
            ],
            'encouragement': [
                "That's a great question! Let me think about this...",
                "I appreciate you asking that - it's really thoughtful.",
                "Excellent point! Here's what I think about that...",
                "That's exactly the kind of question I love to explore!"
            ]
        }
        
        print("💬 Conversation Manager initialized")

    def _check_rate_limit(self, user_id: str) -> bool:
        """Check whether the user is within rate limits"""
        current_time = time.time()
        user_data = self.user_message_counts[user_id]
        if current_time > user_data['reset_time'] + self.rate_limit_window:
            user_data['count'] = 0
            user_data['reset_time'] = current_time

        if user_data['count'] >= self.rate_limit_messages:
            return False

        user_data['count'] += 1
        return True
    
    def create_conversation(self, user_id: str = None, model_type: str = 'general') -> str:
        """Create a new conversation session"""
        conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
        
        conversation = {
            'id': conversation_id,
            'user_id': user_id or 'anonymous',
            'model_type': model_type,
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'messages': [],
            'context': '',
            'metadata': {
                'message_count': 0,
                'total_tokens': 0,
                'avg_response_time': 0,
                'user_satisfaction': None
            }
        }
        
        self.conversations[conversation_id] = conversation
        
        # Add welcome message
        welcome_msg = self._generate_welcome_message(model_type)
        self._add_message(conversation_id, 'assistant', welcome_msg)
        
        print(f"💬 New conversation created: {conversation_id}")
        return conversation_id
    
    def _generate_welcome_message(self, model_type: str) -> str:
        """Generate appropriate welcome message based on model type"""
        if model_type == 'technical':
            return "Hello! I'm your technical AI assistant. I can help with programming, system administration, troubleshooting, and technical explanations. What technical challenge are you working on?"
        elif model_type == 'creative':
            return "Hi! I'm your creative writing assistant. I can help with stories, poems, brainstorming ideas, character development, and all kinds of creative projects. What would you like to create today?"
        elif model_type == 'sentiment':
            return "Hello! I'm specialized in understanding emotions and sentiment. I can analyze text, help with communication, or discuss feelings and perspectives. How can I help you today?"
        elif model_type == 'transformer':
            return "Welcome! I'm an advanced language AI with deep understanding capabilities. I can help with complex analysis, detailed explanations, research, and nuanced conversations. What would you like to explore?"
        else:
            return random.choice(self.conversation_templates['greeting'])
    
    async def process_message(self, conversation_id: str, user_message: str,
                            context_aware: bool = True) -> Dict[str, Any]:
        """Process user message and generate AI response"""
        start_time = time.time()
        
        if conversation_id not in self.conversations:
            conversation_id = self.create_conversation()
        
        conversation = self.conversations[conversation_id]
        
        # Rate limit check
        user_id = conversation.get('user_id', 'anonymous')
        if not self._check_rate_limit(user_id):
            return {
                'success': False,
                'error': 'Rate limit exceeded',
                'conversation_id': conversation_id
            }

        # Add user message
        self._add_message(conversation_id, 'user', user_message)
        
        # Update activity
        conversation['last_activity'] = datetime.now().isoformat()
        
        try:
            # Generate context if enabled
            context = ''
            if context_aware and self.context_memory_enabled:
                context = self._build_context(conversation_id)
            
            # Determine response strategy
            response_strategy = self._analyze_message_intent(user_message)
            
            # Generate AI response
            ai_response = await self._generate_ai_response(
                user_message, 
                context, 
                conversation['model_type'],
                response_strategy
            )
            
            # Add AI response to conversation
            self._add_message(conversation_id, 'assistant', ai_response['content'])
            
            # Update metadata
            end_time = time.time()
            response_time = end_time - start_time
            self._update_conversation_metadata(conversation_id, response_time)
            
            # Log to chat history
            self.chat_history.append({
                'conversation_id': conversation_id,
                'user_message': user_message,
                'ai_response': ai_response['content'],
                'response_time': response_time,
                'timestamp': datetime.now().isoformat(),
                'model_type': conversation['model_type']
            })
            
            return {
                'success': True,
                'conversation_id': conversation_id,
                'response': ai_response['content'],
                'confidence': ai_response.get('confidence', 0.9),
                'response_time': response_time,
                'message_count': len(conversation['messages']),
                'context_used': bool(context),
                'strategy': response_strategy
            }
            
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            
            # Generate fallback response
            fallback_response = self._generate_fallback_response(user_message)
            self._add_message(conversation_id, 'assistant', fallback_response)
            
            return {
                'success': False,
                'conversation_id': conversation_id,
                'response': fallback_response,
                'error': str(e),
                'fallback': True
            }

    def _sanitize_message_content(self, content: str) -> str:
        """Sanitize message content to mitigate XSS attacks"""
        import html
        import re

        if not isinstance(content, str):
            content = str(content)

        content = html.escape(content)
        content = re.sub(r'<script.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
        content = re.sub(r'on\w+\s*=', '', content, flags=re.IGNORECASE)

        if len(content) > 10000:
            content = content[:10000] + '... [truncated]'

        return content
    
    def _add_message(self, conversation_id: str, role: str, content: str):
        """Add message to conversation"""
        if conversation_id not in self.conversations:
            return

        if role not in ['user', 'assistant', 'system']:
            raise ValueError(f"Invalid role: {role}")

        sanitized_content = self._sanitize_message_content(content)

        message = {
            'role': role,
            'content': sanitized_content,
            'timestamp': datetime.now().isoformat(),
            'id': f"msg_{uuid.uuid4().hex[:8]}"
        }
        
        self.conversations[conversation_id]['messages'].append(message)
        self.conversations[conversation_id]['metadata']['message_count'] += 1
    
    def _build_context(self, conversation_id: str, max_messages: int = 10) -> str:
        """Build conversation context for AI processing"""
        if conversation_id not in self.conversations:
            return ''
        
        messages = self.conversations[conversation_id]['messages']
        recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
        
        context_parts = []
        for msg in recent_messages[:-1]:  # Exclude the current message
            role = "Human" if msg['role'] == 'user' else "Assistant"
            context_parts.append(f"{role}: {msg['content']}")
        
        context = '\n'.join(context_parts)
        
        # Truncate if too long
        if len(context) > self.max_context_length:
            context = context[-self.max_context_length:]
        
        return context
    
    def _analyze_message_intent(self, message: str) -> str:
        """Analyze user message to determine response strategy"""
        message_lower = message.lower()
        
        # Question patterns
        if any(word in message_lower for word in ['?', 'what', 'how', 'why', 'when', 'where', 'who']):
            return 'informational'
        
        # Request patterns
        if any(word in message_lower for word in ['can you', 'could you', 'please', 'help me']):
            return 'assistance'
        
        # Creative patterns
        if any(word in message_lower for word in ['write', 'create', 'story', 'poem', 'imagine']):
            return 'creative'
        
        # Technical patterns
        if any(word in message_lower for word in ['code', 'programming', 'debug', 'error', 'function']):
            return 'technical'
        
        # Emotional patterns
        if any(word in message_lower for word in ['feel', 'emotion', 'sad', 'happy', 'angry', 'excited']):
            return 'emotional'
        
        # Greeting patterns
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
            return 'greeting'
        
        # Default to conversational
        return 'conversational'
    
    async def _generate_ai_response(self, message: str, context: str, 
                                  model_type: str, strategy: str) -> Dict[str, Any]:
        """Generate AI response using the appropriate model and strategy"""
        
        # Prepare input for AI
        if context:
            full_input = f"Context:\n{context}\n\nCurrent message: {message}"
        else:
            full_input = message
        
        # Choose AI model based on type and strategy
        ai_model = self._select_ai_model(model_type, strategy)
        
        try:
            # Call AI inference
            if hasattr(self.ai_manager, 'inference_engine'):
                result = self.ai_manager.inference_engine.run_inference(ai_model, full_input)
                
                if result.get('success'):
                    # Process AI result based on model type
                    response_content = self._process_ai_result(result, strategy, message)
                    
                    return {
                        'content': response_content,
                        'confidence': result.get('confidence', 0.9),
                        'model_used': ai_model,
                        'processing_method': result.get('processing_method', 'inference')
                    }
            
            # Fallback to intelligent response generation
            return await self._generate_intelligent_response(message, context, strategy)
            
        except Exception as e:
            print(f"⚠️ AI generation error: {e}")
            return await self._generate_intelligent_response(message, context, strategy)
    
    def _select_ai_model(self, model_type: str, strategy: str) -> str:
        """Select appropriate AI model based on type and strategy"""
        if model_type == 'sentiment' or strategy == 'emotional':
            return 'sentiment'
        elif model_type == 'transformer' or strategy in ['informational', 'technical']:
            return 'transformer'
        elif model_type == 'creative' or strategy == 'creative':
            return 'transformer'  # Use transformer for creative tasks
        else:
            return 'sentiment'  # Default to sentiment for conversational
    
    def _process_ai_result(self, result: Dict[str, Any], strategy: str, original_message: str) -> str:
        """Process AI model result into conversational response"""
        model_result = result.get('prediction', '')
        confidence = result.get('confidence', 0.9)
        
        # Handle sentiment analysis results
        if 'sentiment_scores' in result:
            return self._create_sentiment_response(result, original_message)
        
        # Handle transformer results
        if 'sequence_embedding' in result:
            return self._create_transformer_response(result, strategy, original_message)
        
        # Handle classification results
        if 'class_probabilities' in result:
            return self._create_classification_response(result, original_message)
        
        # Default processing
        if isinstance(model_result, str) and len(model_result) > 10:
            return model_result
        
        # Generate contextual response
        return self._generate_contextual_response(original_message, strategy, confidence)
    
    def _create_sentiment_response(self, result: Dict[str, Any], message: str) -> str:
        """Create response based on sentiment analysis"""
        sentiment = result.get('prediction', 'neutral')
        confidence = result.get('confidence', 0.9)
        
        if sentiment == 'positive':
            if confidence > 0.8:
                return f"I can sense the positive energy in your message! {self._generate_positive_response(message)}"
            else:
                return f"That sounds quite positive! {self._generate_encouraging_response(message)}"
        
        elif sentiment == 'negative':
            if confidence > 0.8:
                return f"I understand you might be feeling frustrated or concerned. {self._generate_supportive_response(message)}"
            else:
                return f"I hear that this might be challenging. {self._generate_helpful_response(message)}"
        
        else:  # neutral
            return self._generate_balanced_response(message)
    
    def _create_transformer_response(self, result: Dict[str, Any], strategy: str, message: str) -> str:
        """Create response based on transformer analysis"""
        # Use transformer results to create more sophisticated responses
        
        if strategy == 'technical':
            return f"From a technical perspective, {self._generate_technical_response(message)}"
        elif strategy == 'creative':
            return self._generate_creative_response(message)
        elif strategy == 'informational':
            return self._generate_informational_response(message)
        else:
            return self._generate_thoughtful_response(message)
    
    async def _generate_intelligent_response(self, message: str, context: str, strategy: str) -> Dict[str, Any]:
        """Generate intelligent response using rule-based system"""
        
        response_generators = {
            'greeting': self._generate_greeting_response,
            'informational': self._generate_informational_response,
            'assistance': self._generate_assistance_response,
            'creative': self._generate_creative_response,
            'technical': self._generate_technical_response,
            'emotional': self._generate_emotional_response,
            'conversational': self._generate_conversational_response
        }
        
        generator = response_generators.get(strategy, self._generate_conversational_response)
        response_content = generator(message)
        
        return {
            'content': response_content,
            'confidence': 0.85,
            'model_used': 'intelligent_generator',
            'processing_method': 'rule_based'
        }
    
    def _generate_greeting_response(self, message: str) -> str:
        """Generate greeting response"""
        greetings = [
            "Hello! Great to see you. How can I help you today?",
            "Hi there! I'm ready to assist with whatever you need.",
            "Welcome! What would you like to explore or discuss?",
            "Hello! I'm here and ready to help. What's on your mind?"
        ]
        return random.choice(greetings)
    
    def _generate_informational_response(self, message: str) -> str:
        """Generate informational response"""
        message_lower = message.lower()
        
        if 'time' in message_lower:
            now = datetime.now()
            return f"The current time is {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}."
        
        elif 'weather' in message_lower:
            return "I don't have access to real-time weather data since I'm running locally, but I can help you think about weather-related questions or direct you to reliable weather sources!"
        
        elif 'agent' in message_lower or 'ai' in message_lower:
            return "I'm your personal AI assistant running locally on your device. I can help with analysis, creative tasks, technical questions, and general conversation. I process everything locally for privacy and can work offline!"
        
        elif any(word in message_lower for word in ['what', 'how', 'why', 'explain']):
            topic = self._extract_topic(message)
            return f"That's a great question about {topic}! While I'm running locally and might not have the most current information, I can help analyze this topic, break it down into components, or explore different perspectives. What specific aspect interests you most?"
        
        else:
            return "That's an interesting question! I'd be happy to help you explore this topic. Could you give me a bit more context about what you're looking for?"
    
    def _generate_assistance_response(self, message: str) -> str:
        """Generate assistance response"""
        if 'write' in message.lower():
            return "I'd be happy to help with writing! I can assist with essays, emails, creative stories, technical documentation, or any other writing task. What type of writing are you working on?"
        
        elif 'code' in message.lower() or 'program' in message.lower():
            return "I can definitely help with programming! I can assist with code review, debugging, explaining concepts, or writing new code. What programming language or specific challenge are you working with?"
        
        elif 'learn' in message.lower():
            return "Learning is wonderful! I can help explain concepts, create study plans, answer questions, or provide different perspectives on topics. What subject or skill are you interested in learning about?"
        
        else:
            return "I'm here to help! I can assist with a wide range of tasks including writing, analysis, problem-solving, creative projects, and answering questions. What specifically would you like help with?"
    
    def _generate_creative_response(self, message: str) -> str:
        """Generate creative response"""
        if 'story' in message.lower():
            return "I love helping with stories! I can help you develop characters, plot ideas, dialogue, or even write sections of your story. What kind of story are you thinking about? Fantasy, sci-fi, mystery, romance, or something else entirely?"
        
        elif 'poem' in message.lower():
            return "Poetry is beautiful! I can help you write poems in various styles - haiku, sonnets, free verse, or any style you prefer. What's the theme or feeling you'd like to capture in your poem?"
        
        elif 'idea' in message.lower():
            return "Let's brainstorm! I excel at generating creative ideas and helping you explore possibilities. What kind of project or challenge are you looking for ideas about?"
        
        else:
            return "Creative projects are my favorite! Whether it's writing, brainstorming ideas, developing concepts, or thinking outside the box, I'm excited to help. What creative endeavor has caught your interest?"
    
    def _generate_technical_response(self, message: str) -> str:
        """Generate technical response"""
        if 'error' in message.lower() or 'bug' in message.lower():
            return "Debugging can be challenging! I can help you analyze error messages, review code logic, or suggest troubleshooting approaches. What specific error or issue are you encountering?"
        
        elif 'database' in message.lower():
            return "Database questions are right up my alley! I can help with SQL queries, database design, optimization, or troubleshooting. What database system are you working with and what's your specific question?"
        
        elif 'api' in message.lower():
            return "APIs are fundamental to modern development! I can help with API design, integration, testing, or troubleshooting. What API-related challenge are you working on?"
        
        else:
            return "Technical problems are my specialty! I can help with programming languages, system administration, architecture decisions, debugging, or explaining complex concepts. What technical challenge can I help you tackle?"
    
    def _generate_emotional_response(self, message: str) -> str:
        """Generate empathetic emotional response"""
        if any(word in message.lower() for word in ['sad', 'down', 'depressed', 'upset']):
            return "I hear that you're going through a difficult time. While I'm an AI and can't replace human support, I'm here to listen and maybe help you think through things. Would you like to talk about what's bothering you?"
        
        elif any(word in message.lower() for word in ['happy', 'excited', 'great', 'awesome']):
            return "That's wonderful to hear! I love when people share positive experiences. Your enthusiasm is contagious! What's making you feel so good today?"
        
        elif any(word in message.lower() for word in ['stressed', 'anxious', 'worried']):
            return "Stress and worry are really challenging to deal with. Sometimes it helps just to talk through what's on your mind. I'm here to listen and maybe help you organize your thoughts. What's causing you the most concern right now?"
        
        else:
            return "I appreciate you sharing your feelings with me. Emotions are complex and important. I'm here to listen and support you however I can. What's on your heart today?"
    
    def _generate_conversational_response(self, message: str) -> str:
        """Generate general conversational response"""
        conversation_starters = [
            f"That's interesting! Tell me more about {self._extract_topic(message)}.",
            "I find that fascinating. What got you thinking about this?",
            "That's a great point. How do you see this affecting things?",
            "Interesting perspective! I'd love to explore this further with you.",
            "That makes me think... what's your experience been with this?",
            "I appreciate you bringing this up. What aspects are most important to you?"
        ]
        
        return random.choice(conversation_starters)
    
    def _generate_positive_response(self, message: str) -> str:
        """Generate positive, encouraging response"""
        responses = [
            "That sounds amazing! I'd love to help you explore this further.",
            "How exciting! What aspects are you most looking forward to?",
            "That's fantastic! I can sense your enthusiasm and I'm here to support your goals.",
            "Wonderful! Your positive attitude is inspiring. How can I help you build on this?"
        ]
        return random.choice(responses)
    
    def _generate_supportive_response(self, message: str) -> str:
        """Generate supportive response for negative sentiment"""
        responses = [
            "I understand this is challenging. Let's work through this together - what would be most helpful right now?",
            "That sounds really difficult. I'm here to help however I can. What support do you need?",
            "I hear that this is tough for you. Sometimes it helps to break things down - what's the biggest concern?",
            "This seems like a lot to handle. Let's take it one step at a time. What feels most manageable to start with?"
        ]
        return random.choice(responses)
    
    def _generate_thoughtful_response(self, message: str) -> str:
        """Generate thoughtful, analytical response"""
        topic = self._extract_topic(message)
        return f"You've raised an interesting point about {topic}. There are several ways to look at this. From one perspective... but I'm curious about your thoughts. What's your take on this?"
    
    def _extract_topic(self, message: str) -> str:
        """Extract main topic from message"""
        # Simple topic extraction - could be enhanced with NLP
        words = message.split()
        
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'how', 'what', 'why', 'when', 'where', 'who', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'about'}
        
        meaningful_words = [word.lower().strip('.,!?') for word in words if word.lower() not in stop_words and len(word) > 2]
        
        if meaningful_words:
            # Return first meaningful word or phrase
            return meaningful_words[0] if len(meaningful_words) == 1 else ' '.join(meaningful_words[:2])
        
        return 'that topic'
    
    def _generate_fallback_response(self, message: str) -> str:
        """Generate fallback response when AI processing fails"""
        fallbacks = [
            "I'm having a small technical hiccup, but I'm still here! Could you rephrase that or ask me something else?",
            "Sorry, I didn't quite process that correctly. I'm running locally and sometimes need a moment. Could you try again?",
            "I encountered a small issue with that request. As your local AI, I'm continuously learning. How else can I help you?",
            "Let me try a different approach - could you give me a bit more context about what you're looking for?"
        ]
        return random.choice(fallbacks)
    
    def _update_conversation_metadata(self, conversation_id: str, response_time: float):
        """Update conversation metadata"""
        if conversation_id not in self.conversations:
            return
        
        metadata = self.conversations[conversation_id]['metadata']
        
        # Update average response time
        current_avg = metadata.get('avg_response_time', 0)
        message_count = metadata.get('message_count', 1)
        
        new_avg = ((current_avg * (message_count - 1)) + response_time) / message_count
        metadata['avg_response_time'] = new_avg
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID"""
        return self.conversations.get(conversation_id)
    
    def get_user_conversations(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversations for a specific user"""
        user_conversations = []
        
        for conv in self.conversations.values():
            if conv.get('user_id') == user_id:
                # Return summary info, not full messages
                summary = {
                    'id': conv['id'],
                    'created_at': conv['created_at'],
                    'last_activity': conv['last_activity'],
                    'message_count': conv['metadata']['message_count'],
                    'model_type': conv['model_type']
                }
                
                # Add preview of last message
                if conv['messages']:
                    last_msg = conv['messages'][-1]
                    summary['last_message_preview'] = last_msg['content'][:100] + '...' if len(last_msg['content']) > 100 else last_msg['content']
                
                user_conversations.append(summary)
        
        # Sort by last activity
        user_conversations.sort(key=lambda x: x['last_activity'], reverse=True)
        
        return user_conversations[:limit]
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            print(f"💬 Conversation deleted: {conversation_id}")
            return True
        return False
    
    def cleanup_old_conversations(self, days: int = 30) -> int:
        """Clean up conversations older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        conversations_to_delete = []
        for conv_id, conv in self.conversations.items():
            last_activity = datetime.fromisoformat(conv['last_activity'])
            if last_activity < cutoff_date:
                conversations_to_delete.append(conv_id)
        
        for conv_id in conversations_to_delete:
            del self.conversations[conv_id]
        
        print(f"💬 Cleaned up {len(conversations_to_delete)} old conversations")
        return len(conversations_to_delete)
    
    def get_chat_statistics(self) -> Dict[str, Any]:
        """Get chat system statistics"""
        total_conversations = len(self.conversations)
        total_messages = sum(conv['metadata']['message_count'] for conv in self.conversations.values())
        
        # Model usage statistics
        model_usage = {}
        for conv in self.conversations.values():
            model = conv.get('model_type', 'unknown')
            model_usage[model] = model_usage.get(model, 0) + 1
        
        # Response time statistics
        response_times = [conv['metadata']['avg_response_time'] for conv in self.conversations.values() if conv['metadata']['avg_response_time'] > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'active_conversations': len([c for c in self.conversations.values() if (datetime.now() - datetime.fromisoformat(c['last_activity'])).seconds < 3600]),
            'model_usage': model_usage,
            'average_response_time': avg_response_time,
            'chat_history_size': len(self.chat_history),
            'context_memory_enabled': self.context_memory_enabled
        }
    
    def export_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Export conversation for backup or analysis"""
        if conversation_id not in self.conversations:
            return None
        
        conversation = self.conversations[conversation_id].copy()
        conversation['exported_at'] = datetime.now().isoformat()
        
        return conversation
    
    def get_status(self) -> Dict[str, Any]:
        """Get conversation manager status"""
        return {
            'active_conversations': len(self.conversations),
            'chat_history_size': len(self.chat_history),
            'context_memory_enabled': self.context_memory_enabled,
            'conversation_timeout': self.conversation_timeout,
            'max_context_length': self.max_context_length,
            'statistics': self.get_chat_statistics()
        }


# Enhanced Dashboard Routes for Chat Interface
def add_chat_routes(dashboard_manager):
    """Add chat-specific routes to the dashboard manager"""
    
    app = dashboard_manager.app
    agent = dashboard_manager.agent
    
    # Initialize conversation manager
    if not hasattr(agent, 'conversation_manager'):
        agent.conversation_manager = ConversationManager(agent.ai_manager, agent.config_manager)
    
    @app.route('/api/ai/chat', methods=['POST'])
    def ai_chat():
        """Main chat endpoint"""
        try:
            data = request.get_json() or {}
            
            message = data.get('input', '')
            conversation_id = data.get('conversation_id')
            model_type = data.get('model', 'general')
            context_aware = data.get('context_aware', True)
            
            if not message:
                return jsonify({'success': False, 'error': 'Message is required'})
            
            # Create new conversation if needed
            if not conversation_id:
                conversation_id = agent.conversation_manager.create_conversation(
                    user_id='local_user',
                    model_type=model_type
                )
            
            # Process message
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                agent.conversation_manager.process_message(
                    conversation_id, 
                    message, 
                    context_aware
                )
            )
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'response': 'I apologize, but I encountered an error. Please try again.'
            })
    
    @app.route('/api/ai/conversations', methods=['GET'])
    def get_conversations():
        """Get user conversations"""
        try:
            conversations = agent.conversation_manager.get_user_conversations('local_user')
            return jsonify({
                'success': True,
                'conversations': conversations
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/ai/conversations/<conversation_id>', methods=['GET'])
    def get_conversation(conversation_id):
        """Get specific conversation"""
        try:
            conversation = agent.conversation_manager.get_conversation(conversation_id)
            if conversation:
                return jsonify({
                    'success': True,
                    'conversation': conversation
                })
            else:
                return jsonify({'success': False, 'error': 'Conversation not found'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/ai/conversations/<conversation_id>', methods=['DELETE'])
    def delete_conversation(conversation_id):
        """Delete conversation"""
        try:
            success = agent.conversation_manager.delete_conversation(conversation_id)
            return jsonify({'success': success})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/ai/chat/statistics')
    def get_chat_statistics():
        """Get chat system statistics"""
        try:
            stats = agent.conversation_manager.get_chat_statistics()
            return jsonify({
                'success': True,
                'statistics': stats
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    # WebSocket events for real-time chat
    socketio = dashboard_manager.socketio
    
    @socketio.on('chat_message')
    def handle_chat_message(data):
        """Handle real-time chat message"""
        try:
            message = data.get('message', '')
            conversation_id = data.get('conversation_id')
            model_type = data.get('model', 'general')
            
            if not conversation_id:
                conversation_id = agent.conversation_manager.create_conversation(
                    user_id='local_user',
                    model_type=model_type
                )
            
            # Process message asynchronously
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                agent.conversation_manager.process_message(
                    conversation_id, 
                    message, 
                    True
                )
            )
            
            # Emit response
            emit('chat_response', result)
            
        except Exception as e:
            emit('chat_error', {'error': str(e)})
    
    @socketio.on('request_conversations')
    def handle_conversations_request():
        """Handle request for conversation list"""
        try:
            conversations = agent.conversation_manager.get_user_conversations('local_user')
            emit('conversations_list', {'conversations': conversations})
        except Exception as e:
            emit('chat_error', {'error': str(e)})

    print("💬 Chat routes added to dashboard")


# Export the conversation manager and route setup
__all__ = ['ConversationManager', 'add_chat_routes']
