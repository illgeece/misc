"""Main API router."""

from fastapi import APIRouter
from app.api.endpoints import chat, characters, knowledge, dice

# Create the main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(characters.router, prefix="/characters", tags=["characters"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(dice.router, prefix="/dice", tags=["dice"]) 