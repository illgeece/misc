"""API routes configuration for the DM Helper application."""

from fastapi import APIRouter

from app.api.endpoints import chat, dice, characters, knowledge, encounters

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(dice.router, prefix="/dice", tags=["dice"])
api_router.include_router(characters.router, prefix="/characters", tags=["characters"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(encounters.router, prefix="/encounters", tags=["encounters"])

# Root health check
@api_router.get("/health", tags=["health"])
async def health_check():
    """Application health check endpoint."""
    return {
        "status": "healthy",
        "application": "dm_helper",
        "version": "1.0.0",
        "services": {
            "chat": "available",
            "dice": "available", 
            "characters": "available",
            "knowledge": "available",
            "encounters": "available"
        }
    } 