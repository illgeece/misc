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
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of the knowledge service."""
        try:
            
            vector_health = self.vector_store.health_check()
            stats = self.get_knowledge_stats()
            
            return {
                "status": "healthy" if vector_health.get("status") == "healthy" else "unhealthy",
                "vector_store": vector_health,
                "knowledge_stats": stats,
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