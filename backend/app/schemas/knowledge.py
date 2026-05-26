"""
Knowledge Base Schemas
Request/response models for knowledge base management
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class KnowledgeUploadRequest(BaseModel):
    """Schema for knowledge base upload (multipart form data)"""

    title: str = Field(..., min_length=2, max_length=200, description="Document title")
    description: Optional[str] = Field(None, max_length=1000, description="Document description")
    tags: Optional[List[str]] = Field(default_factory=list, description="Document tags")
    # file will be handled separately as UploadFile in FastAPI

    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags"""
        if v and len(v) > 20:
            raise ValueError('Maximum 20 tags allowed')
        if v and any(len(tag) > 50 for tag in v):
            raise ValueError('Each tag must be at most 50 characters')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Product FAQ Document",
                "description": "Frequently asked questions about our products",
                "tags": ["faq", "products", "support"]
            }
        }


class KnowledgeUpdateRequest(BaseModel):
    """Schema for updating knowledge base entry"""

    title: Optional[str] = Field(None, min_length=2, max_length=200, description="Document title")
    description: Optional[str] = Field(None, max_length=1000, description="Document description")
    tags: Optional[List[str]] = Field(None, description="Document tags")

    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags"""
        if v is not None:
            if len(v) > 20:
                raise ValueError('Maximum 20 tags allowed')
            if any(len(tag) > 50 for tag in v):
                raise ValueError('Each tag must be at most 50 characters')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated Product FAQ",
                "tags": ["faq", "products", "support", "updated"]
            }
        }


class KnowledgeChunkResponse(BaseModel):
    """Response schema for a knowledge chunk"""

    chunk_index: int = Field(..., description="Chunk index in document")
    text: str = Field(..., description="Chunk text content")
    score: Optional[float] = Field(None, description="Relevance score (for search results)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Chunk metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "chunk_index": 0,
                "text": "Our product offers industry-leading features including...",
                "score": 0.89,
                "metadata": {
                    "char_count": 512,
                    "token_count_estimate": 128
                }
            }
        }


class KnowledgeResponse(BaseModel):
    """Response schema for knowledge base entry"""

    id: str = Field(..., description="Knowledge entry ID")
    company_id: int = Field(..., description="Company ID")
    title: str = Field(..., description="Document title")
    description: Optional[str] = Field(None, description="Document description")
    tags: List[str] = Field(default_factory=list, description="Document tags")

    # Document metadata
    filename: str = Field(..., description="Original filename")
    file_format: str = Field(..., description="File format (pdf, txt, docx, csv)")
    file_size: int = Field(..., description="File size in bytes")

    # Processing info
    num_chunks: int = Field(..., description="Number of chunks created")
    total_chars: int = Field(..., description="Total characters in document")

    # Timestamps
    created_at: datetime = Field(..., description="Upload timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Optional: Include chunks in response
    chunks: Optional[List[KnowledgeChunkResponse]] = Field(None, description="Document chunks")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439013",
                "company_id": "507f1f77bcf86cd799439012",
                "title": "Product FAQ Document",
                "description": "Frequently asked questions",
                "tags": ["faq", "products"],
                "filename": "product_faq.pdf",
                "file_format": "pdf",
                "file_size": 245678,
                "num_chunks": 25,
                "total_chars": 12500,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class KnowledgeListResponse(BaseModel):
    """Response schema for paginated knowledge list"""

    items: List[KnowledgeResponse] = Field(..., description="List of knowledge entries")
    total: int = Field(..., description="Total number of entries")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "507f1f77bcf86cd799439013",
                        "company_id": "507f1f77bcf86cd799439012",
                        "title": "Product FAQ",
                        "description": "Frequently asked questions",
                        "tags": ["faq"],
                        "filename": "product_faq.pdf",
                        "file_format": "pdf",
                        "file_size": 245678,
                        "num_chunks": 25,
                        "total_chars": 12500,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "total": 45,
                "page": 1,
                "page_size": 20,
                "total_pages": 3
            }
        }


class KnowledgeSearchRequest(BaseModel):
    """Schema for semantic search in knowledge base"""

    query: str = Field(..., min_length=3, max_length=500, description="Search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    score_threshold: Optional[float] = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0-1)"
    )
    tags: Optional[List[str]] = Field(None, description="Filter by tags")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "How do I reset my password?",
                "top_k": 5,
                "score_threshold": 0.7,
                "tags": ["faq", "support"]
            }
        }


class KnowledgeSearchResult(BaseModel):
    """Single search result with context"""

    knowledge_id: str = Field(..., description="Knowledge entry ID")
    title: str = Field(..., description="Document title")
    chunk: KnowledgeChunkResponse = Field(..., description="Matched chunk")

    class Config:
        json_schema_extra = {
            "example": {
                "knowledge_id": "507f1f77bcf86cd799439013",
                "title": "Product FAQ",
                "chunk": {
                    "chunk_index": 5,
                    "text": "To reset your password, click on 'Forgot Password'...",
                    "score": 0.92,
                    "metadata": {"char_count": 312}
                }
            }
        }


class KnowledgeSearchResponse(BaseModel):
    """Response schema for knowledge search"""

    query: str = Field(..., description="Original search query")
    results: List[KnowledgeSearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Number of results returned")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "How do I reset my password?",
                "results": [
                    {
                        "knowledge_id": "507f1f77bcf86cd799439013",
                        "title": "Product FAQ",
                        "chunk": {
                            "chunk_index": 5,
                            "text": "To reset your password...",
                            "score": 0.92,
                            "metadata": {"char_count": 312}
                        }
                    }
                ],
                "total_results": 3
            }
        }


class KnowledgeUploadResponse(BaseModel):
    """Response schema for successful knowledge upload"""

    knowledge: KnowledgeResponse = Field(..., description="Created knowledge entry")
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "knowledge": {
                    "id": "507f1f77bcf86cd799439013",
                    "company_id": "507f1f77bcf86cd799439012",
                    "title": "Product FAQ",
                    "filename": "faq.pdf",
                    "file_format": "pdf",
                    "file_size": 245678,
                    "num_chunks": 25,
                    "total_chars": 12500,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                },
                "message": "Document uploaded and processed successfully"
            }
        }


# Export schemas
__all__ = [
    "KnowledgeUploadRequest",
    "KnowledgeUpdateRequest",
    "KnowledgeChunkResponse",
    "KnowledgeResponse",
    "KnowledgeListResponse",
    "KnowledgeSearchRequest",
    "KnowledgeSearchResult",
    "KnowledgeSearchResponse",
    "KnowledgeUploadResponse"
]
