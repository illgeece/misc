"""Background task manager for long-running services."""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Manager for background tasks and services."""
    
    def __init__(self):
        self.settings = get_settings()
        self.tasks: Dict[str, asyncio.Task] = {}
        self.services: Dict[str, Any] = {}
        self.is_running = False
        self.startup_time: Optional[datetime] = None
    
    async def startup(self) -> Dict[str, Any]:
        """Start all background services."""
        if self.is_running:
            return {
                "status": "already_running",
                "message": "Background services are already running"
            }
        
        logger.info("Starting background services...")
        self.startup_time = datetime.now()
        results = {}
        
        try:
            # Start file watcher if enabled
            if self.settings.watch_file_changes:
                await self._start_file_watcher()
                results["file_watcher"] = "started"
            else:
                results["file_watcher"] = "disabled"
            
            self.is_running = True
            
            logger.info("Background services started successfully")
            return {
                "status": "success",
                "message": "Background services started",
                "services": results,
                "startup_time": self.startup_time.isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to start background services: {e}")
            return {
                "status": "error",
                "message": f"Failed to start background services: {str(e)}",
                "services": results
            }
    
    async def shutdown(self) -> Dict[str, Any]:
        """Stop all background services."""
        if not self.is_running:
            return {
                "status": "not_running",
                "message": "Background services are not running"
            }
        
        logger.info("Stopping background services...")
        results = {}
        
        try:
            # Stop file watcher
            await self._stop_file_watcher()
            results["file_watcher"] = "stopped"
            
            # Cancel any remaining tasks
            for task_name, task in self.tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    results[task_name] = "cancelled"
            
            self.tasks.clear()
            self.services.clear()
            self.is_running = False
            
            logger.info("Background services stopped successfully")
            return {
                "status": "success",
                "message": "Background services stopped",
                "services": results
            }
        
        except Exception as e:
            logger.error(f"Error stopping background services: {e}")
            return {
                "status": "error",
                "message": f"Error stopping background services: {str(e)}",
                "services": results
            }
    
    async def _start_file_watcher(self):
        """Start the file watcher service."""
        try:
            from app.services.file_watcher import file_watcher_service
            
            result = await file_watcher_service.start_watching()
            
            if result["status"] in ["started", "already_running"]:
                self.services["file_watcher"] = file_watcher_service
                logger.info("File watcher service started successfully")
            else:
                logger.error(f"Failed to start file watcher: {result['message']}")
                raise RuntimeError(f"File watcher startup failed: {result['message']}")
        
        except Exception as e:
            logger.error(f"Error starting file watcher: {e}")
            raise
    
    async def _stop_file_watcher(self):
        """Stop the file watcher service."""
        try:
            if "file_watcher" in self.services:
                file_watcher_service = self.services["file_watcher"]
                result = await file_watcher_service.stop_watching()
                
                if result["status"] in ["stopped", "not_running"]:
                    del self.services["file_watcher"]
                    logger.info("File watcher service stopped successfully")
                else:
                    logger.warning(f"File watcher stop result: {result['message']}")
        
        except Exception as e:
            logger.error(f"Error stopping file watcher: {e}")
    
    async def restart_file_watcher(self) -> Dict[str, Any]:
        """Restart the file watcher service."""
        try:
            logger.info("Restarting file watcher service...")
            
            # Stop current watcher
            await self._stop_file_watcher()
            
            # Start new watcher
            await self._start_file_watcher()
            
            return {
                "status": "success",
                "message": "File watcher restarted successfully"
            }
        
        except Exception as e:
            logger.error(f"Failed to restart file watcher: {e}")
            return {
                "status": "error",
                "message": f"Failed to restart file watcher: {str(e)}"
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all background services."""
        services_status = {}
        
        # File watcher status
        if "file_watcher" in self.services:
            try:
                file_watcher = self.services["file_watcher"]
                services_status["file_watcher"] = file_watcher.get_status()
            except Exception as e:
                services_status["file_watcher"] = {"error": str(e)}
        else:
            services_status["file_watcher"] = {"status": "not_running"}
        
        # Task status
        tasks_status = {}
        for task_name, task in self.tasks.items():
            tasks_status[task_name] = {
                "done": task.done(),
                "cancelled": task.cancelled(),
                "exception": str(task.exception()) if task.done() and task.exception() else None
            }
        
        return {
            "is_running": self.is_running,
            "startup_time": self.startup_time.isoformat() if self.startup_time else None,
            "services": services_status,
            "tasks": tasks_status,
            "total_services": len(self.services),
            "total_tasks": len(self.tasks)
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all background services."""
        overall_health = True
        issues = []
        service_health = {}
        
        try:
            # Check if manager is running when it should be
            if self.settings.watch_file_changes and not self.is_running:
                overall_health = False
                issues.append("Background task manager should be running but is stopped")
            
            # Check file watcher health
            if "file_watcher" in self.services:
                try:
                    file_watcher = self.services["file_watcher"]
                    watcher_health = file_watcher.health_check()
                    service_health["file_watcher"] = watcher_health
                    
                    if watcher_health["status"] != "healthy":
                        overall_health = False
                        issues.extend(watcher_health.get("issues", []))
                
                except Exception as e:
                    overall_health = False
                    issues.append(f"File watcher health check failed: {str(e)}")
                    service_health["file_watcher"] = {"status": "unhealthy", "error": str(e)}
            elif self.settings.watch_file_changes:
                overall_health = False
                issues.append("File watcher should be running but is not started")
                service_health["file_watcher"] = {"status": "not_running"}
            
            # Check for failed tasks
            for task_name, task in self.tasks.items():
                if task.done() and not task.cancelled() and task.exception():
                    overall_health = False
                    issues.append(f"Task {task_name} failed: {task.exception()}")
            
            return {
                "status": "healthy" if overall_health else "unhealthy",
                "issues": issues,
                "services": service_health,
                "manager_running": self.is_running,
                "file_watching_enabled": self.settings.watch_file_changes
            }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "issues": [f"Health check failed: {str(e)}"]
            }
    
    async def trigger_manual_refresh(self) -> Dict[str, Any]:
        """Manually trigger a knowledge base refresh."""
        try:
            from app.services.knowledge_service import knowledge_service
            
            logger.info("Triggering manual knowledge base refresh...")
            result = await knowledge_service.auto_refresh_indexes()
            
            return {
                "status": "success",
                "message": "Manual refresh completed",
                "refresh_result": result
            }
        
        except Exception as e:
            logger.error(f"Manual refresh failed: {e}")
            return {
                "status": "error",
                "message": f"Manual refresh failed: {str(e)}"
            }


# Global background task manager instance
background_task_manager = BackgroundTaskManager()


@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan context manager for background services."""
    # Startup
    logger.info("Application startup: initializing background services")
    startup_result = await background_task_manager.startup()
    
    if startup_result["status"] == "error":
        logger.error(f"Failed to start background services: {startup_result['message']}")
        # Continue anyway, some services might still work
    else:
        logger.info("Background services started successfully")
    
    yield
    
    # Shutdown
    logger.info("Application shutdown: stopping background services")
    shutdown_result = await background_task_manager.shutdown()
    
    if shutdown_result["status"] == "error":
        logger.error(f"Error during background services shutdown: {shutdown_result['message']}")
    else:
        logger.info("Background services stopped successfully") 