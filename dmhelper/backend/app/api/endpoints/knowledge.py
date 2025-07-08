"""Knowledge API endpoints for document indexing and search."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
import tempfile
import os

from app.services.knowledge_service import knowledge_service

router = APIRouter()


class DocumentSource(BaseModel):
    """Document source model."""
    filename: str
    filepath: str
    file_type: str
    chunk_count: int
    indexed: bool


class SearchResult(BaseModel):
    """Search result model."""
    content: str
    source: str
    source_path: str
    score: float
    page_number: Optional[int] = None
    metadata: dict = {}


class SearchRequest(BaseModel):
    """Search request model."""
    query: str
    limit: int = 10
    min_score: float = 0.3
    source_filter: Optional[List[str]] = None


class SearchResponse(BaseModel):
    """Search response model."""
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: int
    min_score: float


@router.get("/sources", response_model=List[DocumentSource])
async def get_document_sources():
    """Get all indexed document sources."""
    try:
        sources = knowledge_service.get_source_files()
        return sources
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document sources: {str(e)}")


@router.post("/index")
async def index_documents():
    """
    Index all documents in the campaign folder.
    
    This endpoint will:
    1. Scan campaign_root for supported file types
    2. Extract text content from documents
    3. Split into chunks and generate embeddings
    4. Store in vector database with metadata
    """
    try:
        result = await knowledge_service.index_campaign_documents()
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document indexing failed: {str(e)}")


@router.post("/index/file")
async def index_file(file: UploadFile = File(...)):
    """Index a single uploaded file."""
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Index the temporary file
            result = await knowledge_service.index_single_file(temp_file_path)
            
            if result["status"] == "error":
                raise HTTPException(status_code=500, detail=result["message"])
            
            return result
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File indexing failed: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest):
    """
    Search the knowledge base using semantic similarity.
    
    Uses vector embeddings to find semantically similar content
    with optional filtering by source files.
    """
    try:
        result = await knowledge_service.search_knowledge(
            query=request.query,
            limit=request.limit,
            min_score=request.min_score,
            source_filter=request.source_filter
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Convert to response format
        search_results = []
        for res in result["results"]:
            search_results.append(SearchResult(
                content=res["content"],
                source=res["source"],
                source_path=res["source_path"],
                score=res["score"],
                page_number=res.get("page_number"),
                metadata=res.get("metadata", {})
            ))
        
        return SearchResponse(
            query=result["query"],
            results=search_results,
            total_results=result["total_results"],
            search_time_ms=result["search_time_ms"],
            min_score=result["min_score"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Knowledge search failed: {str(e)}")


@router.get("/search/suggestions")
async def get_search_suggestions(q: str):
    """Get search query suggestions based on indexed content."""
    try:
        # Generate basic suggestions based on common D&D topics
        base_suggestions = [
            f"{q} rules",
            f"{q} mechanics", 
            f"{q} lore",
            f"{q} spells",
            f"{q} abilities",
            f"{q} combat",
            f"{q} equipment"
        ]
        
        # Filter to most relevant suggestions
        relevant_suggestions = [s for s in base_suggestions if len(s) <= 50][:5]
        
        return {"suggestions": relevant_suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.delete("/index")
async def clear_index():
    """Clear the entire knowledge index."""
    try:
        result = await knowledge_service.clear_knowledge_base()
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear index: {str(e)}")


@router.post("/index/refresh")
async def refresh_index():
    """Refresh the index by re-processing all files."""
    try:
        # Clear existing index
        clear_result = await knowledge_service.clear_knowledge_base()
        if clear_result["status"] == "error":
            raise HTTPException(status_code=500, detail=f"Failed to clear index: {clear_result['message']}")
        
        # Re-index all documents
        index_result = await knowledge_service.index_campaign_documents()
        if index_result["status"] == "error":
            raise HTTPException(status_code=500, detail=f"Failed to re-index: {index_result['message']}")
        
        return {
            "message": "Index refreshed successfully",
            "indexed_documents": index_result.get("indexed_documents", 0),
            "total_chunks": index_result.get("total_chunks", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Index refresh failed: {str(e)}")


@router.get("/stats")
async def get_knowledge_stats():
    """Get statistics about the knowledge base."""
    try:
        stats = knowledge_service.get_knowledge_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge stats: {str(e)}")


@router.get("/health")
async def knowledge_health_check():
    """Check the health of the knowledge service."""
    try:
        health = knowledge_service.health_check()
        return health
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}") 