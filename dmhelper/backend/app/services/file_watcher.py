"""File watcher service for monitoring campaign directory changes."""

import asyncio
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from threading import Thread

from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
    FileDeletedEvent,
    FileMovedEvent,
    DirCreatedEvent,
    DirDeletedEvent,
    DirModifiedEvent,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CampaignFileEventHandler(FileSystemEventHandler):
    """Event handler for campaign directory file changes."""
    
    def __init__(self, file_watcher_service: 'FileWatcherService'):
        super().__init__()
        self.file_watcher = file_watcher_service
        self.supported_extensions = {'.pdf', '.md', '.txt', '.yaml', '.yml'}
    
    def _is_supported_file(self, file_path: str) -> bool:
        """Check if the file is a supported document type."""
        return Path(file_path).suffix.lower() in self.supported_extensions
    
    def _should_ignore(self, file_path: str) -> bool:
        """Check if the file should be ignored (temp files, hidden files, etc.)."""
        path = Path(file_path)
        
        # Ignore hidden files and directories
        if any(part.startswith('.') for part in path.parts):
            return True
        
        # Ignore temporary files
        if path.name.startswith('~') or path.name.endswith('.tmp'):
            return True
        
        # Ignore backup files
        if path.name.endswith('.bak') or path.name.endswith('.backup'):
            return True
        
        return False
    
    def on_created(self, event):
        """Handle file/directory creation events."""
        if isinstance(event, FileCreatedEvent):
            if self._should_ignore(event.src_path):
                return
            
            if self._is_supported_file(event.src_path):
                logger.info(f"New file detected: {event.src_path}")
                self.file_watcher.schedule_index_file(event.src_path, "created")
        
        elif isinstance(event, DirCreatedEvent):
            logger.info(f"New directory detected: {event.src_path}")
            # Don't index directories immediately, wait for files to be added
    
    def on_modified(self, event):
        """Handle file/directory modification events."""
        if isinstance(event, FileModifiedEvent):
            if self._should_ignore(event.src_path):
                return
            
            if self._is_supported_file(event.src_path):
                logger.info(f"File modified: {event.src_path}")
                self.file_watcher.schedule_index_file(event.src_path, "modified")
        
        elif isinstance(event, DirModifiedEvent):
            # Directory modifications are usually metadata changes, ignore
            pass
    
    def on_deleted(self, event):
        """Handle file/directory deletion events."""
        if isinstance(event, FileDeletedEvent):
            if self._should_ignore(event.src_path):
                return
            
            if self._is_supported_file(event.src_path):
                logger.info(f"File deleted: {event.src_path}")
                self.file_watcher.schedule_remove_file(event.src_path)
        
        elif isinstance(event, DirDeletedEvent):
            logger.info(f"Directory deleted: {event.src_path}")
            self.file_watcher.schedule_remove_directory(event.src_path)
    
    def on_moved(self, event):
        """Handle file/directory move/rename events."""
        if isinstance(event, FileMovedEvent):
            if self._should_ignore(event.src_path) and self._should_ignore(event.dest_path):
                return
            
            # Handle file moves as delete + create
            if self._is_supported_file(event.src_path):
                logger.info(f"File moved: {event.src_path} -> {event.dest_path}")
                self.file_watcher.schedule_remove_file(event.src_path)
            
            if self._is_supported_file(event.dest_path):
                self.file_watcher.schedule_index_file(event.dest_path, "moved")


class FileWatcherService:
    """Service for watching campaign directory file changes and triggering re-indexing."""
    
    def __init__(self):
        self.settings = get_settings()
        self.observer: Optional[Observer] = None
        self.event_handler: Optional[CampaignFileEventHandler] = None
        self.is_running = False
        self.watch_path = self.settings.campaign_root_dir
        
        # Queue for processing file events
        self._event_queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Rate limiting to avoid too frequent re-indexing
        self._last_index_time: Dict[str, datetime] = {}
        self._index_cooldown_seconds = 2.0  # Wait 2 seconds between indexing same file
        
        # Statistics
        self.stats = {
            "files_created": 0,
            "files_modified": 0,
            "files_deleted": 0,
            "files_moved": 0,
            "directories_deleted": 0,
            "index_operations": 0,
            "delete_operations": 0,
            "last_event_time": None,
            "started_at": None,
            "errors": 0
        }
    
    def _should_rate_limit(self, file_path: str) -> bool:
        """Check if we should rate limit indexing for this file."""
        if file_path not in self._last_index_time:
            return False
        
        time_since_last = (datetime.now() - self._last_index_time[file_path]).total_seconds()
        return time_since_last < self._index_cooldown_seconds
    
    def schedule_index_file(self, file_path: str, event_type: str):
        """Schedule a file for indexing."""
        if self._should_rate_limit(file_path):
            logger.debug(f"Rate limiting indexing for {file_path}")
            return
        
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._event_queue.put(("index_file", file_path, event_type)),
                self._loop
            )
        self.stats["last_event_time"] = datetime.now().isoformat()
        
        if event_type == "created":
            self.stats["files_created"] += 1
        elif event_type == "modified":
            self.stats["files_modified"] += 1
        elif event_type == "moved":
            self.stats["files_moved"] += 1
    
    def schedule_remove_file(self, file_path: str):
        """Schedule a file for removal from index."""
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._event_queue.put(("remove_file", file_path, "deleted")),
                self._loop
            )
        self.stats["files_deleted"] += 1
        self.stats["last_event_time"] = datetime.now().isoformat()
    
    def schedule_remove_directory(self, dir_path: str):
        """Schedule a directory for removal from index."""
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._event_queue.put(("remove_directory", dir_path, "deleted")),
                self._loop
            )
        self.stats["directories_deleted"] += 1
        self.stats["last_event_time"] = datetime.now().isoformat()
    
    async def _process_events(self):
        """Process file system events from the queue."""
        while True:
            try:
                # Wait for events with timeout to check if we should stop
                try:
                    event_type, file_path, action = await asyncio.wait_for(
                        self._event_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    if not self.is_running:
                        break
                    continue
                
                logger.info(f"Processing {event_type} for {file_path} ({action})")
                
                # Import here to avoid circular imports
                from app.services.knowledge_service import knowledge_service
                
                if event_type == "index_file":
                    try:
                        # Update rate limiting
                        self._last_index_time[file_path] = datetime.now()
                        
                        # Index the file
                        result = await knowledge_service.index_single_file(file_path)
                        
                        if result["status"] == "success":
                            logger.info(f"Successfully indexed {file_path}")
                            self.stats["index_operations"] += 1
                        else:
                            logger.error(f"Failed to index {file_path}: {result.get('message', 'Unknown error')}")
                            self.stats["errors"] += 1
                    
                    except Exception as e:
                        logger.error(f"Error indexing file {file_path}: {e}")
                        self.stats["errors"] += 1
                
                elif event_type == "remove_file":
                    try:
                        # Import here to avoid circular imports
                        from app.services.vector_store import vector_store
                        
                        deleted_count = vector_store.delete_by_source(file_path)
                        logger.info(f"Removed {deleted_count} chunks for deleted file {file_path}")
                        self.stats["delete_operations"] += 1
                    
                    except Exception as e:
                        logger.error(f"Error removing file {file_path} from index: {e}")
                        self.stats["errors"] += 1
                
                elif event_type == "remove_directory":
                    try:
                        # Import here to avoid circular imports
                        from app.services.vector_store import vector_store
                        
                        # Remove all files under this directory
                        deleted_count = 0
                        all_sources = vector_store.get_all_sources()
                        
                        for source in all_sources:
                            if source.startswith(dir_path):
                                deleted_count += vector_store.delete_by_source(source)
                        
                        logger.info(f"Removed {deleted_count} chunks for deleted directory {dir_path}")
                        self.stats["delete_operations"] += 1
                    
                    except Exception as e:
                        logger.error(f"Error removing directory {dir_path} from index: {e}")
                        self.stats["errors"] += 1
                
                # Mark task as done
                self._event_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
                self.stats["errors"] += 1
    
    async def start_watching(self) -> Dict[str, Any]:
        """Start watching the campaign directory for changes."""
        if self.is_running:
            return {
                "status": "already_running",
                "message": "File watcher is already running",
                "watch_path": self.watch_path
            }
        
        try:
            # Ensure campaign directory exists
            campaign_path = Path(self.watch_path)
            if not campaign_path.exists():
                logger.warning(f"Campaign directory does not exist: {self.watch_path}")
                campaign_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created campaign directory: {self.watch_path}")
            
            # Set up event loop for background processing
            self._loop = asyncio.get_event_loop()
            
            # Create event handler and observer
            self.event_handler = CampaignFileEventHandler(self)
            self.observer = Observer()
            
            # Watch the campaign directory recursively
            self.observer.schedule(
                self.event_handler,
                self.watch_path,
                recursive=True
            )
            
            # Start the observer in a background thread
            self.observer.start()
            
            # Start event processing task
            self._processing_task = asyncio.create_task(self._process_events())
            
            self.is_running = True
            self.stats["started_at"] = datetime.now().isoformat()
            
            logger.info(f"File watcher started for: {self.watch_path}")
            
            return {
                "status": "started",
                "message": f"File watcher started successfully",
                "watch_path": self.watch_path,
                "recursive": True,
                "started_at": self.stats["started_at"]
            }
        
        except Exception as e:
            logger.error(f"Failed to start file watcher: {e}")
            return {
                "status": "error",
                "message": f"Failed to start file watcher: {str(e)}",
                "watch_path": self.watch_path
            }
    
    async def stop_watching(self) -> Dict[str, Any]:
        """Stop watching the campaign directory."""
        if not self.is_running:
            return {
                "status": "not_running",
                "message": "File watcher is not running"
            }
        
        try:
            # Stop the observer
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5.0)  # Wait up to 5 seconds
                self.observer = None
            
            # Stop event processing
            self.is_running = False
            if self._processing_task:
                self._processing_task.cancel()
                try:
                    await self._processing_task
                except asyncio.CancelledError:
                    pass
                self._processing_task = None
            
            # Clear event handler
            self.event_handler = None
            self._loop = None
            
            logger.info("File watcher stopped")
            
            return {
                "status": "stopped",
                "message": "File watcher stopped successfully",
                "final_stats": self.stats.copy()
            }
        
        except Exception as e:
            logger.error(f"Error stopping file watcher: {e}")
            return {
                "status": "error",
                "message": f"Error stopping file watcher: {str(e)}"
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the file watcher."""
        return {
            "is_running": self.is_running,
            "watch_path": self.watch_path,
            "watch_enabled": self.settings.watch_file_changes,
            "observer_alive": self.observer.is_alive() if self.observer else False,
            "processing_task_running": (
                self._processing_task and not self._processing_task.done()
            ) if self._processing_task else False,
            "queue_size": self._event_queue.qsize() if self._event_queue else 0,
            "stats": self.stats.copy()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the file watcher service."""
        try:
            status = self.get_status()
            
            # Check if watcher should be running but isn't
            should_be_running = self.settings.watch_file_changes
            is_healthy = True
            issues = []
            
            if should_be_running and not self.is_running:
                is_healthy = False
                issues.append("File watcher should be running but is stopped")
            
            if self.is_running and not status["observer_alive"]:
                is_healthy = False
                issues.append("Observer thread is not alive")
            
            if self.is_running and not status["processing_task_running"]:
                is_healthy = False
                issues.append("Event processing task is not running")
            
            # Check if campaign directory exists
            if not Path(self.watch_path).exists():
                is_healthy = False
                issues.append(f"Campaign directory does not exist: {self.watch_path}")
            
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "issues": issues,
                "watcher_status": status,
                "campaign_directory_exists": Path(self.watch_path).exists()
            }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "issues": [f"Health check failed: {str(e)}"]
            }


# Global file watcher service instance
file_watcher_service = FileWatcherService() 