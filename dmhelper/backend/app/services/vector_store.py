"""Vector store service using ChromaDB for semantic search."""

import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid

import chromadb
from chromadb.config import Settings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from app.core.config import get_settings
from app.services.document_processor import DocumentChunk

logger = logging.getLogger(__name__)


class VectorSearchResult:
    """Represents a search result from the vector store."""
    
    def __init__(self, chunk: DocumentChunk, score: float, distance: float):
        self.chunk = chunk
        self.score = score  # Similarity score (higher = more similar)
        self.distance = distance  # Vector distance (lower = more similar)
        self.source_file = chunk.source_file
        self.content = chunk.content
        self.metadata = chunk.metadata or {}


class VectorStore:
    """Service for storing and searching document chunks using vector embeddings."""
    
    def __init__(self):
        self.settings = get_settings()
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self._client = None
        self._collection = None
        self._document_vectors = None
        self._document_texts = []
        self._initialize_chroma()
    
    def _initialize_chroma(self):
        """Initialize ChromaDB client and collection."""
        try:
            # Ensure persist directory exists
            os.makedirs(self.settings.chroma_persist_directory, exist_ok=True)
            
            # Initialize ChromaDB client
            self._client = chromadb.PersistentClient(
                path=self.settings.chroma_persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            try:
                self._collection = self._client.get_collection(
                    name=self.settings.chroma_collection_name
                )
                logger.info(f"Loaded existing collection: {self.settings.chroma_collection_name}")
            except Exception:
                # Collection doesn't exist, create it
                self._collection = self._client.create_collection(
                    name=self.settings.chroma_collection_name,
                    metadata={"description": "DM Helper knowledge base"}
                )
                logger.info(f"Created new collection: {self.settings.chroma_collection_name}")
            
            # Rebuild TF-IDF vectorizer from existing documents if any exist
            self._rebuild_vectorizer_from_existing()
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise RuntimeError(f"Vector store initialization failed: {e}")
    
    def _rebuild_vectorizer_from_existing(self):
        """Rebuild the TF-IDF vectorizer from existing documents in ChromaDB."""
        try:
            # Get all existing documents
            existing_data = self._collection.get(include=["documents"])
            existing_docs = existing_data.get("documents", [])
            
            if not existing_docs:
                logger.info("No existing documents found - vectorizer will be fitted on first add")
                self._document_texts = []
                self._document_vectors = None
                return
            
            logger.info(f"Rebuilding TF-IDF vectorizer from {len(existing_docs)} existing documents")
            
            # Fit vectorizer on existing documents
            tfidf_matrix = self.vectorizer.fit_transform(existing_docs)
            
            # Store the state - ensure we use the same document order as in ChromaDB
            self._document_texts = existing_docs.copy()
            self._document_vectors = tfidf_matrix.toarray()
            
            logger.info(f"Vectorizer rebuilt with vocabulary size: {len(self.vectorizer.vocabulary_)}")
            logger.info(f"Document vectors shape: {self._document_vectors.shape}")
            
        except Exception as e:
            logger.error(f"Failed to rebuild vectorizer from existing documents: {e}")
            # Reset state on failure
            self._document_texts = []
            self._document_vectors = None
            # Continue anyway - vectorizer will be fitted on next add
    
    def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        """Add document chunks to the vector store."""
        if not chunks:
            return 0
        
        try:
            # Prepare data for ChromaDB
            documents = []
            metadatas = []
            ids = []
            
            for chunk in chunks:
                # Ensure unique ID
                chunk_id = chunk.chunk_id or str(uuid.uuid4())
                
                # Prepare metadata
                metadata = {
                    "source_file": chunk.source_file,
                    "chunk_id": chunk_id,
                    "added_at": datetime.now().isoformat(),
                    **chunk.metadata
                }
                
                # Add optional fields if present
                if chunk.page_number:
                    metadata["page_number"] = chunk.page_number
                if chunk.start_line:
                    metadata["start_line"] = chunk.start_line
                if chunk.end_line:
                    metadata["end_line"] = chunk.end_line
                
                documents.append(chunk.content)
                metadatas.append(metadata)
                ids.append(chunk_id)
            
            # Generate TF-IDF embeddings
            logger.info(f"Generating TF-IDF embeddings for {len(documents)} chunks...")

            # Fit or transform using the TF-IDF vectorizer
            if not self._document_texts:
                # First time – fit the vectorizer on the incoming documents
                tfidf_matrix = self.vectorizer.fit_transform(documents)
                embeddings = tfidf_matrix.toarray().tolist()
                self._document_texts = documents.copy()
                self._document_vectors = tfidf_matrix.toarray()
            else:
                # Vectorizer is already fitted – transform only, keeping dimension constant
                tfidf_matrix = self.vectorizer.transform(documents)
                embeddings = tfidf_matrix.toarray().tolist()
                # Append to stored texts/vectors for future operations
                self._document_texts.extend(documents)
                if self._document_vectors is not None:
                    self._document_vectors = np.vstack([self._document_vectors, tfidf_matrix.toarray()])
                else:
                    self._document_vectors = tfidf_matrix.toarray()
            
            # Add to collection
            self._collection.add(
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
                ids=ids
            )
            
            logger.info(f"Successfully added {len(chunks)} chunks to vector store")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Failed to add chunks to vector store: {e}")
            raise RuntimeError(f"Vector store add operation failed: {e}")
    
    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar chunks using semantic similarity."""
        try:
            # Check if we have any documents
            if not self._document_texts or self._document_vectors is None:
                logger.info("No documents in vector store for search")
                return []
            
            # Generate query embedding using TF-IDF
            query_tfidf = self.vectorizer.transform([query]).toarray()
            
            # Calculate cosine similarity with all documents
            similarities = cosine_similarity(query_tfidf, self._document_vectors)[0]
            
            # Get top similar documents
            top_indices = np.argsort(similarities)[::-1]
            
            # Build results directly from our cached document texts and vectors
            search_results = []
            
            # Get metadata for all documents from ChromaDB (to maintain consistency)
            all_docs = self._collection.get(include=["documents", "metadatas"])
            
            # Create a mapping from document content to metadata
            doc_to_metadata = {}
            if all_docs['documents'] and all_docs['metadatas']:
                for doc, metadata in zip(all_docs['documents'], all_docs['metadatas']):
                    doc_to_metadata[doc] = metadata
            
            for idx in top_indices:
                if len(search_results) >= limit:
                    break
                    
                if idx < len(self._document_texts) and similarities[idx] > min_score:
                    doc_content = self._document_texts[idx]
                    similarity_score = similarities[idx]
                    distance = 1.0 - similarity_score
                    
                    # Get metadata for this document
                    metadata = doc_to_metadata.get(doc_content, {})
                    
                    # Reconstruct DocumentChunk
                    chunk = DocumentChunk(
                        content=doc_content,
                        source_file=metadata.get("source_file", "unknown"),
                        chunk_id=metadata.get("chunk_id", str(uuid.uuid4())),
                        page_number=metadata.get("page_number"),
                        start_line=metadata.get("start_line"),
                        end_line=metadata.get("end_line"),
                        metadata=metadata
                    )
                    
                    search_results.append(VectorSearchResult(
                        chunk=chunk,
                        score=similarity_score,
                        distance=distance
                    ))
            
            logger.info(f"Search for '{query}' returned {len(search_results)} results")
            return search_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise RuntimeError(f"Vector search operation failed: {e}")
    
    def search_by_source(
        self,
        query: str,
        source_files: List[str],
        limit: int = 5
    ) -> List[VectorSearchResult]:
        """Search within specific source files."""
        filter_metadata = {"source_file": {"$in": source_files}}
        return self.search(query, limit=limit, filter_metadata=filter_metadata)
    
    def get_chunks_by_source(self, source_file: str) -> List[DocumentChunk]:
        """Get all chunks from a specific source file."""
        try:
            results = self._collection.get(
                where={"source_file": source_file},
                include=["documents", "metadatas"]
            )
            
            chunks = []
            if results['documents']:
                for doc, metadata in zip(results['documents'], results['metadatas']):
                    chunk = DocumentChunk(
                        content=doc,
                        source_file=metadata.get("source_file", source_file),
                        chunk_id=metadata.get("chunk_id", str(uuid.uuid4())),
                        page_number=metadata.get("page_number"),
                        start_line=metadata.get("start_line"),
                        end_line=metadata.get("end_line"),
                        metadata=metadata
                    )
                    chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get chunks by source: {e}")
            return []
    
    def delete_by_source(self, source_file: str) -> int:
        """Delete all chunks from a specific source file."""
        try:
            # Get IDs of chunks to delete
            results = self._collection.get(
                where={"source_file": source_file},
                include=["metadatas"]
            )
            
            if not results['ids']:
                return 0
            
            ids_to_delete = results['ids']
            self._collection.delete(ids=ids_to_delete)
            
            logger.info(f"Deleted {len(ids_to_delete)} chunks from {source_file}")
            return len(ids_to_delete)
            
        except Exception as e:
            logger.error(f"Failed to delete chunks from {source_file}: {e}")
            return 0
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store collection."""
        try:
            count_result = self._collection.count()
            
            # Get unique source files
            all_results = self._collection.get(include=["metadatas"])
            source_files = set()
            
            if all_results['metadatas']:
                for metadata in all_results['metadatas']:
                    if 'source_file' in metadata:
                        source_files.add(metadata['source_file'])
            
            return {
                "total_chunks": count_result,
                "unique_sources": len(source_files),
                "source_files": list(source_files),
                "collection_name": self.settings.chroma_collection_name,
                "embedding_model": self.settings.embedding_model
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                "total_chunks": 0,
                "unique_sources": 0,
                "source_files": [],
                "error": str(e)
            }
    
    def clear_collection(self) -> bool:
        """Clear all data from the collection."""
        try:
            # Delete the collection and recreate it
            try:
                self._client.delete_collection(name=self.settings.chroma_collection_name)
            except Exception:
                pass  # Collection might not exist
                
            self._collection = self._client.create_collection(
                name=self.settings.chroma_collection_name,
                metadata={"description": "DM Helper knowledge base"}
            )
            
            # Reset local vectors
            self._document_vectors = None
            self._document_texts = []
            
            logger.info("Successfully cleared vector store collection")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False
    
    def get_all_sources(self) -> List[str]:
        """Get list of all source files in the collection."""
        try:
            stats = self.get_collection_stats()
            return stats.get("source_files", [])
        except Exception as e:
            logger.error(f"Failed to get all sources: {e}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the vector store is healthy."""
        try:
            stats = self.get_collection_stats()
            
            return {
                "status": "healthy",
                "total_chunks": stats.get("total_chunks", 0),
                "unique_sources": stats.get("unique_sources", 0),
                "collection_name": self.settings.chroma_collection_name,
                "persist_directory": self.settings.chroma_persist_directory
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "collection_name": self.settings.chroma_collection_name,
                "persist_directory": self.settings.chroma_persist_directory
            }


# Global instance
vector_store = VectorStore() 