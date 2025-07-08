"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.config import get_settings
from app.api.routes import api_router
from app.services.background_tasks import lifespan


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "DM Helper API",
            "version": settings.api_version,
            "status": "running"
        }
    
    @app.get("/health")
    async def health_check():
        """Comprehensive health check endpoint."""
        try:
            from app.services.background_tasks import background_task_manager
            from app.services.knowledge_service import knowledge_service
            from app.services.llm_service import llm_service
            
            # Get health status from all services
            background_health = background_task_manager.health_check()
            knowledge_health = knowledge_service.health_check()
            llm_health = llm_service.health_check()
            
            # Determine overall health
            all_healthy = all([
                background_health.get("status") == "healthy",
                knowledge_health.get("status") == "healthy",
                llm_health.get("status") == "healthy"
            ])
            
            return {
                "status": "healthy" if all_healthy else "degraded",
                "services": {
                    "background_tasks": background_health,
                    "knowledge": knowledge_health,
                    "llm": llm_health
                },
                "api": {
                    "status": "healthy",
                    "version": settings.api_version
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "api": {
                    "status": "healthy",
                    "version": settings.api_version
                }
            }
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    ) 