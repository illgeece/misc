"""Document processing service for extracting and chunking text from various file types."""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib
from datetime import datetime

import pdfplumber
import yaml
# from unstructured.partition.auto import partition
# from unstructured.chunking.title import chunk_by_title

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Represents a chunk of processed document text."""
    content: str
    source_file: str
    chunk_id: str
    page_number: Optional[int] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # Generate chunk ID if not provided
        if not self.chunk_id:
            content_hash = hashlib.md5(self.content.encode()).hexdigest()[:8]
            self.chunk_id = f"{Path(self.source_file).stem}_{content_hash}"


@dataclass
class ProcessedDocument:
    """Represents a fully processed document."""
    source_file: str
    file_type: str
    chunks: List[DocumentChunk]
    total_chunks: int
    processing_time_ms: int
    file_size_bytes: int
    last_modified: datetime
    content_hash: str


class DocumentProcessor:
    """Service for processing various document types into searchable chunks."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.supported_extensions = {'.pdf', '.md', '.txt', '.yaml', '.yml'}
    
    def is_supported(self, file_path: str) -> bool:
        """Check if the file type is supported."""
        return Path(file_path).suffix.lower() in self.supported_extensions
    
    def get_file_hash(self, file_path: str) -> str:
        """Generate a hash of the file content for change detection."""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def process_document(self, file_path: str) -> ProcessedDocument:
        """Process a document into chunks."""
        start_time = datetime.now()
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not self.is_supported(file_path):
            raise ValueError(f"Unsupported file type: {Path(file_path).suffix}")
        
        # Get file metadata
        file_stat = os.stat(file_path)
        file_size = file_stat.st_size
        last_modified = datetime.fromtimestamp(file_stat.st_mtime)
        content_hash = self.get_file_hash(file_path)
        
        # Extract text based on file type
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            chunks = self._process_pdf(file_path)
        elif file_ext == '.md':
            chunks = self._process_markdown(file_path)
        elif file_ext == '.txt':
            chunks = self._process_text(file_path)
        elif file_ext in ['.yaml', '.yml']:
            chunks = self._process_yaml(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {file_ext}")
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ProcessedDocument(
            source_file=file_path,
            file_type=file_ext[1:],  # Remove the dot
            chunks=chunks,
            total_chunks=len(chunks),
            processing_time_ms=int(processing_time),
            file_size_bytes=file_size,
            last_modified=last_modified,
            content_hash=content_hash
        )
    
    def _process_pdf(self, file_path: str) -> List[DocumentChunk]:
        """Process PDF file using pdfplumber."""
        chunks = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text and text.strip():
                        # Split page text into smaller chunks if needed
                        page_chunks = self._split_text_into_chunks(
                            text, 
                            file_path, 
                            page_number=page_num
                        )
                        chunks.extend(page_chunks)
                        
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            raise RuntimeError(f"Failed to process PDF: {e}")
        
        return chunks
    
    def _process_markdown(self, file_path: str) -> List[DocumentChunk]:
        """Process Markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple markdown processing (without unstructured for now)
            return self._split_text_into_chunks(content, file_path)
            
        except Exception as e:
            logger.error(f"Error processing Markdown {file_path}: {e}")
            raise RuntimeError(f"Failed to process Markdown: {e}")
    
    def _process_text(self, file_path: str) -> List[DocumentChunk]:
        """Process plain text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self._split_text_into_chunks(content, file_path)
            
        except Exception as e:
            logger.error(f"Error processing text file {file_path}: {e}")
            raise RuntimeError(f"Failed to process text file: {e}")
    
    def _process_yaml(self, file_path: str) -> List[DocumentChunk]:
        """Process YAML file (like character templates)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Convert YAML to readable text
            content = self._yaml_to_text(data, Path(file_path).stem)
            
            return self._split_text_into_chunks(content, file_path)
            
        except Exception as e:
            logger.error(f"Error processing YAML {file_path}: {e}")
            raise RuntimeError(f"Failed to process YAML: {e}")
    
    def _yaml_to_text(self, data: Dict[str, Any], filename: str) -> str:
        """Convert YAML data to readable text format."""
        lines = [f"# {filename.replace('_', ' ').title()}"]
        
        def process_item(key: str, value: Any, indent: int = 0) -> List[str]:
            prefix = "  " * indent
            
            if isinstance(value, dict):
                result = [f"{prefix}{key.replace('_', ' ').title()}:"]
                for k, v in value.items():
                    result.extend(process_item(k, v, indent + 1))
                return result
            elif isinstance(value, list):
                result = [f"{prefix}{key.replace('_', ' ').title()}:"]
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            result.extend(process_item(k, v, indent + 1))
                    else:
                        result.append(f"{prefix}  - {item}")
                return result
            else:
                return [f"{prefix}{key.replace('_', ' ').title()}: {value}"]
        
        for key, value in data.items():
            lines.extend(process_item(key, value))
        
        return "\n".join(lines)
    
    def _split_text_into_chunks(
        self, 
        text: str, 
        file_path: str, 
        page_number: Optional[int] = None
    ) -> List[DocumentChunk]:
        """Split text into overlapping chunks."""
        chunks = []
        words = text.split()
        
        if len(words) <= self.chunk_size:
            # Text is small enough to be a single chunk
            chunk = DocumentChunk(
                content=text,
                source_file=file_path,
                chunk_id="",
                page_number=page_number
            )
            chunks.append(chunk)
        else:
            # Split into overlapping chunks
            start = 0
            chunk_num = 0
            
            while start < len(words):
                end = min(start + self.chunk_size, len(words))
                chunk_words = words[start:end]
                chunk_text = " ".join(chunk_words)
                
                chunk = DocumentChunk(
                    content=chunk_text,
                    source_file=file_path,
                    chunk_id=f"{Path(file_path).stem}_chunk_{chunk_num}",
                    page_number=page_number,
                    metadata={"chunk_index": chunk_num}
                )
                chunks.append(chunk)
                
                # Move start position with overlap
                start += self.chunk_size - self.chunk_overlap
                chunk_num += 1
        
        return chunks
    
    def process_directory(self, directory_path: str) -> List[ProcessedDocument]:
        """Process all supported documents in a directory recursively."""
        documents = []
        directory = Path(directory_path)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        # Find all supported files
        for file_path in directory.rglob("*"):
            if file_path.is_file() and self.is_supported(str(file_path)):
                try:
                    logger.info(f"Processing {file_path}")
                    doc = self.process_document(str(file_path))
                    documents.append(doc)
                    logger.info(f"Successfully processed {file_path} -> {doc.total_chunks} chunks")
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    continue
        
        return documents


# Global instance
document_processor = DocumentProcessor() 