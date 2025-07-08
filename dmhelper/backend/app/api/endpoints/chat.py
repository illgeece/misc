"""Chat endpoint for conversational AI with RAG."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.services.chat_service import chat_service

router = APIRouter()


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    use_rag: bool = True
    context_limit: int = 2000


class ChatResponse(BaseModel):
    response: str
    session_id: str
    model: str
    response_time_ms: int
    context_used: bool
    context_sources: List[dict] = []
    conversation_length: int


class ContextQueryRequest(BaseModel):
    question: str
    context_sources: Optional[List[str]] = None
    max_context: int = 3000


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the AI assistant with RAG support."""
    try:
        result = await chat_service.send_message(
            session_id=request.session_id or "",
            user_message=request.message,
            use_rag=request.use_rag,
            context_limit=request.context_limit
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return ChatResponse(
            response=result["response"],
            session_id=result["session_id"],
            model=result.get("model", "unknown"),
            response_time_ms=result.get("response_time_ms", 0),
            context_used=result.get("context_used", False),
            context_sources=result.get("context_sources", []),
            conversation_length=result.get("conversation_length", 0)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@router.post("/ask")
async def ask_with_context(request: ContextQueryRequest):
    """Ask a question with specific context sources (one-off query)."""
    try:
        result = await chat_service.ask_with_context(
            question=request.question,
            context_sources=request.context_sources,
            max_context=request.max_context
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context query failed: {str(e)}")


@router.get("/sessions")
async def list_sessions():
    """List active chat sessions."""
    try:
        sessions = chat_service.list_sessions()
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a specific chat session."""
    try:
        session_info = chat_service.get_session_info(session_id)
        
        if "error" in session_info:
            raise HTTPException(status_code=404, detail=session_info["error"])
        
        return session_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session info: {str(e)}")


@router.get("/sessions/{session_id}/summary")
async def get_conversation_summary(session_id: str):
    """Get a summary of the conversation in a session."""
    try:
        summary = await chat_service.get_conversation_summary(session_id)
        
        if "error" in summary:
            raise HTTPException(status_code=404, detail=summary["error"])
        
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


@router.post("/sessions")
async def create_session(metadata: Optional[dict] = None):
    """Create a new chat session."""
    try:
        session_id = chat_service.create_session(metadata)
        return {"session_id": session_id, "message": "Session created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    try:
        success = chat_service.delete_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": f"Session {session_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@router.post("/sessions/{session_id}/clear")
async def clear_session(session_id: str):
    """Clear the conversation history of a session."""
    try:
        success = chat_service.clear_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": f"Session {session_id} history cleared successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear session: {str(e)}")


@router.get("/health")
async def chat_health_check():
    """Check the health of the chat service."""
    try:
        health = chat_service.health_check()
        return health
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}") 