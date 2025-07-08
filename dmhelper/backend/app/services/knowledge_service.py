"""Knowledge service for indexing and searching campaign documents."""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from app.core.config import get_settings
from app.services.document_processor import document_processor, ProcessedDocument
from app.services.vector_store import vector_store, VectorSearchResult

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Service for managing campaign knowledge through document indexing and retrieval."""
    
    def __init__(self):
        self.settings = get_settings()
        self.document_processor = document_processor
        self.vector_store = vector_store
    
    async def index_campaign_documents(self) -> Dict[str, Any]:
        """Index all documents in the campaign directory."""
        try:
            campaign_dir = self.settings.campaign_root_dir
            
            if not Path(campaign_dir).exists():
                logger.warning(f"Campaign directory not found: {campaign_dir}")
                return {
                    "status": "warning",
                    "message": f"Campaign directory not found: {campaign_dir}",
                    "indexed_documents": 0,
                    "total_chunks": 0
                }
            
            logger.info(f"Starting indexing of campaign documents in {campaign_dir}")
            start_time = datetime.now()
            
            # Process all documents in the campaign directory
            processed_docs = self.document_processor.process_directory(campaign_dir)
            
            if not processed_docs:
                return {
                    "status": "success",
                    "message": "No supported documents found to index",
                    "indexed_documents": 0,
                    "total_chunks": 0,
                    "processing_time_ms": 0
                }
            
            # Add all chunks to vector store (disabled for now)
            all_chunks = []
            for doc in processed_docs:
                all_chunks.extend(doc.chunks)
            
            chunks_added = self.vector_store.add_chunks(all_chunks)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result = {
                "status": "success",
                "message": f"Successfully indexed {len(processed_docs)} documents",
                "indexed_documents": len(processed_docs),
                "total_chunks": chunks_added,
                "processing_time_ms": int(processing_time),
                "documents": [
                    {
                        "file": doc.source_file,
                        "type": doc.file_type,
                        "chunks": doc.total_chunks,
                        "size_bytes": doc.file_size_bytes
                    }
                    for doc in processed_docs
                ]
            }
            
            logger.info(f"Indexing complete: {len(processed_docs)} documents, {chunks_added} chunks")
            return result
            
        except Exception as e:
            logger.error(f"Failed to index campaign documents: {e}")
            return {
                "status": "error",
                "message": f"Indexing failed: {str(e)}",
                "indexed_documents": 0,
                "total_chunks": 0
            }
    
    async def index_single_file(self, file_path: str) -> Dict[str, Any]:
        """Index a single document file."""
        try:
            logger.info(f"Indexing single file: {file_path}")
            
            # Process the document
            processed_doc = self.document_processor.process_document(file_path)
            
            # Remove existing chunks from this file
            deleted_chunks = self.vector_store.delete_by_source(file_path)
            if deleted_chunks > 0:
                logger.info(f"Removed {deleted_chunks} existing chunks from {file_path}")
            
            # Add new chunks
            chunks_added = self.vector_store.add_chunks(processed_doc.chunks)
            
            return {
                "status": "success",
                "message": f"Successfully indexed {Path(file_path).name}",
                "file": file_path,
                "chunks_added": chunks_added,
                "chunks_replaced": deleted_chunks,
                "processing_time_ms": processed_doc.processing_time_ms
            }
            
        except Exception as e:
            logger.error(f"Failed to index file {file_path}: {e}")
            return {
                "status": "error",
                "message": f"Failed to index file: {str(e)}",
                "file": file_path,
                "chunks_added": 0
            }
    
    async def search_knowledge(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.3,
        source_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Search the knowledge base for relevant information."""
        try:
            logger.info(f"Searching knowledge base for: '{query}'")
            start_time = datetime.now()
            
            # Perform vector search
            if source_filter:
                results = self.vector_store.search_by_source(
                    query=query,
                    source_files=source_filter,
                    limit=limit
                )
            else:
                results = self.vector_store.search(
                    query=query,
                    limit=limit,
                    min_score=min_score
                )
            
            search_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.content,
                    "source": Path(result.source_file).name,
                    "source_path": result.source_file,
                    "score": round(result.score, 3),
                    "page_number": result.chunk.page_number,
                    "metadata": result.metadata
                })
            
            return {
                "query": query,
                "results": formatted_results,
                "total_results": len(formatted_results),
                "search_time_ms": int(search_time),
                "min_score": min_score
            }
            
        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            return {
                "query": query,
                "results": [],
                "total_results": 0,
                "search_time_ms": 0,
                "error": str(e)
            }
    
    def get_context_for_query(
        self,
        query: str,
        max_context_length: int = 2000
    ) -> str:
        """Get relevant context for a query, formatted for LLM consumption."""
        try:
            # Search for relevant chunks
            results = self.vector_store.search(
                query=query,
                limit=5,
                min_score=0.3
            )
            
            if not results:
                return ""
            
            # Build context string
            context_parts = []
            current_length = 0
            
            for result in results:
                source_name = Path(result.source_file).name
                content = result.content.strip()
                
                # Format context piece
                context_piece = f"[Source: {source_name}]\n{content}\n"
                
                # Check if adding this piece would exceed max length
                if current_length + len(context_piece) > max_context_length:
                    break
                
                context_parts.append(context_piece)
                current_length += len(context_piece)
            
            return "\n---\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Failed to get context for query: {e}")
            return ""
    
    def get_source_files(self) -> List[Dict[str, Any]]:
        """Get list of all indexed source files."""
        try:
            stats = self.vector_store.get_collection_stats()
            source_files = []
            
            for file_path in stats.get("source_files", []):
                chunks = self.vector_store.get_chunks_by_source(file_path)
                
                source_files.append({
                    "filename": Path(file_path).name,
                    "filepath": file_path,
                    "file_type": Path(file_path).suffix[1:] if Path(file_path).suffix else "unknown",
                    "chunk_count": len(chunks),
                    "indexed": True
                })
            
            return source_files
            
        except Exception as e:
            logger.error(f"Failed to get source files: {e}")
            return []
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the knowledge base."""
        try:
            
            vector_stats = self.vector_store.get_collection_stats()
            
            # Get file type breakdown
            file_types = {}
            for file_path in vector_stats.get("source_files", []):
                ext = Path(file_path).suffix[1:] if Path(file_path).suffix else "unknown"
                file_types[ext] = file_types.get(ext, 0) + 1
            
            return {
                "total_chunks": vector_stats.get("total_chunks", 0),
                "unique_sources": vector_stats.get("unique_sources", 0),
                "file_types": file_types,
                "embedding_model": vector_stats.get("embedding_model", "unknown"),
                "collection_name": vector_stats.get("collection_name", "unknown"),
                "campaign_directory": self.settings.campaign_root_dir
            }
            
        except Exception as e:
            logger.error(f"Failed to get knowledge stats: {e}")
            return {
                "total_chunks": 0,
                "unique_sources": 0,
                "file_types": {},
                "error": str(e)
            }
    
    async def clear_knowledge_base(self) -> Dict[str, Any]:
        """Clear all indexed knowledge."""
        try:
            success = self.vector_store.clear_collection()
            
            if success:
                return {
                    "status": "success",
                    "message": "Knowledge base cleared successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to clear knowledge base"
                }
                
        except Exception as e:
            logger.error(f"Failed to clear knowledge base: {e}")
            return {
                "status": "error",
                "message": f"Clear operation failed: {str(e)}"
            }
    
    async def index_file_with_change_detection(self, file_path: str) -> Dict[str, Any]:
        """Index a file with intelligent change detection."""
        try:
            logger.info(f"Indexing file with change detection: {file_path}")
            
            # Check if file exists
            if not Path(file_path).exists():
                logger.warning(f"File no longer exists: {file_path}")
                return {
                    "status": "warning",
                    "message": f"File no longer exists: {file_path}",
                    "file": file_path,
                    "action": "skipped"
                }
            
            # Get current file hash
            current_hash = self.document_processor.get_file_hash(file_path)
            
            # Check if file is already indexed and unchanged
            existing_chunks = self.vector_store.get_chunks_by_source(file_path)
            
            if existing_chunks:
                # Get stored hash from metadata
                stored_hash = existing_chunks[0].metadata.get("file_hash")
                
                if stored_hash == current_hash:
                    logger.info(f"File unchanged, skipping re-indexing: {file_path}")
                    return {
                        "status": "success",
                        "message": f"File unchanged, skipped re-indexing",
                        "file": file_path,
                        "action": "skipped",
                        "reason": "no_changes"
                    }
            
            # File is new or changed, proceed with indexing
            return await self.index_single_file(file_path)
            
        except Exception as e:
            logger.error(f"Failed to index file with change detection {file_path}: {e}")
            return {
                "status": "error",
                "message": f"Failed to index file: {str(e)}",
                "file": file_path,
                "action": "failed"
            }
    
    async def auto_refresh_indexes(self) -> Dict[str, Any]:
        """Automatically refresh indexes by scanning for changes in the campaign directory."""
        try:
            logger.info("Starting automatic index refresh")
            start_time = datetime.now()
            
            campaign_dir = Path(self.settings.campaign_root_dir)
            if not campaign_dir.exists():
                return {
                    "status": "warning",
                    "message": f"Campaign directory not found: {campaign_dir}",
                    "refreshed_files": 0,
                    "skipped_files": 0,
                    "errors": 0
                }
            
            # Get all currently indexed files
            indexed_sources = set(self.vector_store.get_all_sources())
            
            # Get all files that should be indexed
            current_files = set()
            for file_path in campaign_dir.rglob("*"):
                if file_path.is_file() and self.document_processor.is_supported(str(file_path)):
                    current_files.add(str(file_path))
            
            # Files to remove (no longer exist)
            files_to_remove = indexed_sources - current_files
            
            # Files to check for changes
            files_to_check = current_files
            
            results = {
                "refreshed_files": 0,
                "skipped_files": 0,
                "removed_files": 0,
                "errors": 0,
                "operations": []
            }
            
            # Remove deleted files
            for file_path in files_to_remove:
                try:
                    deleted_count = self.vector_store.delete_by_source(file_path)
                    results["removed_files"] += 1
                    results["operations"].append({
                        "file": file_path,
                        "action": "removed",
                        "chunks_deleted": deleted_count
                    })
                    logger.info(f"Removed {deleted_count} chunks for deleted file: {file_path}")
                except Exception as e:
                    logger.error(f"Error removing deleted file {file_path}: {e}")
                    results["errors"] += 1
            
            # Check and update existing/new files
            for file_path in files_to_check:
                try:
                    result = await self.index_file_with_change_detection(file_path)
                    
                    if result["action"] == "skipped":
                        results["skipped_files"] += 1
                    elif result["status"] == "success":
                        results["refreshed_files"] += 1
                    elif result["status"] == "error":
                        results["errors"] += 1
                    
                    results["operations"].append({
                        "file": file_path,
                        "action": result["action"],
                        "status": result["status"],
                        "chunks": result.get("chunks_added", 0)
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    results["errors"] += 1
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "status": "success",
                "message": f"Index refresh completed",
                "processing_time_ms": int(processing_time),
                **results
            }
            
        except Exception as e:
            logger.error(f"Auto refresh failed: {e}")
            return {
                "status": "error",
                "message": f"Auto refresh failed: {str(e)}",
                "refreshed_files": 0,
                "skipped_files": 0,
                "errors": 1
            }
    
    def get_file_watcher_status(self) -> Dict[str, Any]:
        """Get status information about file watching."""
        try:
            # Import here to avoid circular imports
            from app.services.file_watcher import file_watcher_service
            
            watcher_status = file_watcher_service.get_status()
            watcher_health = file_watcher_service.health_check()
            
            return {
                "file_watching_enabled": self.settings.watch_file_changes,
                "watcher_service": watcher_status,
                "watcher_health": watcher_health
            }
        except Exception as e:
            return {
                "file_watching_enabled": self.settings.watch_file_changes,
                "watcher_service": {"error": str(e)},
                "watcher_health": {"status": "unhealthy", "error": str(e)}
            }

    def health_check(self) -> Dict[str, Any]:
        """Check the health of the knowledge service."""
        try:
            
            vector_health = self.vector_store.health_check()
            stats = self.get_knowledge_stats()
            watcher_status = self.get_file_watcher_status()
            
            return {
                "status": "healthy" if vector_health.get("status") == "healthy" else "unhealthy",
                "vector_store": vector_health,
                "knowledge_stats": stats,
                "file_watcher": watcher_status,
                "campaign_directory": self.settings.campaign_root_dir,
                "campaign_directory_exists": Path(self.settings.campaign_root_dir).exists()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "campaign_directory": self.settings.campaign_root_dir
            }


# Global instance
knowledge_service = KnowledgeService() 