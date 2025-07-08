"""Chat service with RAG (Retrieval Augmented Generation) for DM assistance."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from app.services.llm_service import llm_service, ChatMessage, LLMResponse
from app.services.knowledge_service import knowledge_service

logger = logging.getLogger(__name__)


class ChatSession:
    """Represents a chat session with conversation history."""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.messages: List[ChatMessage] = []
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.metadata: Dict[str, Any] = {}
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        message = ChatMessage(role=role, content=content)
        self.messages.append(message)
        self.last_activity = datetime.now()
    
    def get_recent_messages(self, limit: int = 10) -> List[ChatMessage]:
        """Get the most recent messages from the conversation."""
        return self.messages[-limit:] if len(self.messages) > limit else self.messages
    
    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.messages = []
        self.last_activity = datetime.now()


class ChatService:
    """Service for managing chat sessions with RAG capabilities."""
    
    def __init__(self):
        self.llm_service = llm_service
        self.knowledge_service = knowledge_service
        self.sessions: Dict[str, ChatSession] = {}
    
    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new chat session."""
        session = ChatSession()
        if metadata:
            session.metadata = metadata
        
        self.sessions[session.session_id] = session
        logger.info(f"Created new chat session: {session.session_id}")
        
        return session.session_id
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get an existing chat session."""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted chat session: {session_id}")
            return True
        return False
    
    async def send_message(
        self,
        session_id: str,
        user_message: str,
        use_rag: bool = True,
        context_limit: int = 2000
    ) -> Dict[str, Any]:
        """Send a message and get an AI response with optional RAG."""
        try:
            # Get or create session
            session = self.get_session(session_id)
            if not session:
                session_id = self.create_session()
                session = self.get_session(session_id)
            
            start_time = datetime.now()
            
            # Add user message to session
            session.add_message("user", user_message)
            
            # Get relevant context if RAG is enabled
            retrieved_context = ""
            context_sources = []
            
            if use_rag:
                try:
                    # Search for relevant context using knowledge service
                    search_results = await self.knowledge_service.search_knowledge(
                        user_message,
                        limit=5,
                        min_score=0.1
                    )
                    
                    # Build context from search results
                    context_parts = []
                    for result in search_results.get("results", []):
                        context_parts.append(f"[{result['source']}]\n{result['content']}")
                        context_sources.append({
                            "source": result['source'],
                            "score": result['score']
                        })
                    
                    retrieved_context = "\n\n---\n\n".join(context_parts[:3])  # Limit to top 3 results
                    logger.info(f"RAG found {len(context_parts)} relevant context chunks")
                    
                except Exception as e:
                    logger.error(f"RAG search failed: {e}")
                    retrieved_context = ""
            
            # Generate AI response
            conversation_history = session.get_recent_messages(limit=8)  # Exclude the just-added user message
            
            ai_response = await self.llm_service.generate_dm_response(
                user_message=user_message,
                conversation_history=conversation_history[:-1],  # Exclude current user message
                retrieved_context=retrieved_context if retrieved_context else None
            )
            
            # Add AI response to session
            session.add_message("assistant", ai_response.content)
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "session_id": session_id,
                "response": ai_response.content,
                "user_message": user_message,
                "model": ai_response.model,
                "response_time_ms": int(response_time),
                "context_used": bool(retrieved_context),
                "context_sources": context_sources,
                "conversation_length": len(session.messages),
                "llm_response_time_ms": ai_response.response_time_ms
            }
            
        except Exception as e:
            logger.error(f"Chat message processing failed: {e}")
            return {
                "session_id": session_id,
                "response": "I apologize, but I encountered an error processing your message. Please try again.",
                "user_message": user_message,
                "error": str(e),
                "response_time_ms": 0,
                "context_used": False,
                "context_sources": []
            }
    
    async def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the conversation in a session."""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        try:
            # Prepare conversation for summarization
            conversation_text = ""
            for msg in session.messages:
                role = "DM Assistant" if msg.role == "assistant" else "User"
                conversation_text += f"{role}: {msg.content}\n\n"
            
            if not conversation_text.strip():
                return {
                    "session_id": session_id,
                    "summary": "No conversation yet.",
                    "message_count": 0
                }
            
            # Generate summary using LLM
            summary_prompt = "Please provide a concise summary of this D&D conversation, highlighting key topics, questions, and decisions:"
            
            summary_response = await self.llm_service.generate_response(
                messages=[ChatMessage(role="user", content=f"{summary_prompt}\n\n{conversation_text}")],
                system_prompt="You are summarizing a conversation between a user and a D&D assistant. Focus on key points, decisions, and ongoing topics."
            )
            
            return {
                "session_id": session_id,
                "summary": summary_response.content,
                "message_count": len(session.messages),
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate conversation summary: {e}")
            return {
                "session_id": session_id,
                "summary": f"Error generating summary: {str(e)}",
                "message_count": len(session.messages)
            }
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a chat session."""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        return {
            "session_id": session.session_id,
            "message_count": len(session.messages),
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "metadata": session.metadata
        }
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active chat sessions."""
        return [
            {
                "session_id": session.session_id,
                "message_count": len(session.messages),
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "metadata": session.metadata
            }
            for session in self.sessions.values()
        ]
    
    def clear_session(self, session_id: str) -> bool:
        """Clear the history of a chat session."""
        session = self.get_session(session_id)
        if session:
            session.clear_history()
            logger.info(f"Cleared history for session: {session_id}")
            return True
        return False
    
    async def ask_with_context(
        self,
        question: str,
        context_sources: Optional[List[str]] = None,
        max_context: int = 3000
    ) -> Dict[str, Any]:
        """Ask a question with specific context sources (one-off query)."""
        try:
            start_time = datetime.now()
            
            # Search for relevant context
            search_results = await self.knowledge_service.search_knowledge(
                question,
                limit=5,
                min_score=0.2,
                source_filter=context_sources
            )
            
            # Build context from search results
            context_parts = []
            for result in search_results.get("results", []):
                context_parts.append(f"[{result['source']}]\n{result['content']}")
            
            context = "\n\n---\n\n".join(context_parts[:5])  # Limit to top 5 results
            
            # Generate response
            response = await self.llm_service.generate_dm_response(
                user_message=question,
                conversation_history=[],
                retrieved_context=context if context else None
            )
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "question": question,
                "response": response.content,
                "context_used": bool(context),
                "sources": search_results.get("results", []),
                "model": response.model,
                "response_time_ms": int(response_time)
            }
            
        except Exception as e:
            logger.error(f"Context-based query failed: {e}")
            return {
                "question": question,
                "response": f"I encountered an error: {str(e)}",
                "context_used": False,
                "sources": [],
                "error": str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of the chat service."""
        try:
            llm_health = self.llm_service.health_check()
            knowledge_health = self.knowledge_service.health_check()
            
            return {
                "status": "healthy" if all([
                    llm_health.get("status") == "healthy",
                    knowledge_health.get("status") == "healthy"
                ]) else "unhealthy",
                "active_sessions": len(self.sessions),
                "llm_service": llm_health,
                "knowledge_service": knowledge_health
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "active_sessions": len(self.sessions)
            }


# Global instance
chat_service = ChatService() 