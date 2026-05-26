"""
Knowledge Base Database Model
Pydantic model for knowledge_bases collection
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.database.models.user import PyObjectId


class KnowledgeMetadata(BaseModel):
    """Metadata for knowledge base entry"""

    file_type: str = Field(..., pattern="^(pdf|txt|docx|csv|xlsx)$")
    file_name: str
    chunk_index: int = Field(..., ge=0)
    total_chunks: int = Field(..., ge=1)
    file_size_bytes: Optional[int] = None


class KnowledgeBaseBase(BaseModel):
    """Base knowledge base model with common fields"""

    company_id: int = Field(...)
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    vector_id: str = Field(...)  # ID in Qdrant
    metadata: KnowledgeMetadata

    class Config:
        json_encoders = {PyObjectId: str}
        populate_by_name = True


class KnowledgeBaseCreate(KnowledgeBaseBase):
    """Knowledge base creation model"""

    pass


class KnowledgeBaseInDB(KnowledgeBaseBase):
    """Knowledge base model as stored in database"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {PyObjectId: str}
        populate_by_name = True
        arbitrary_types_allowed = True


class KnowledgeBaseResponse(BaseModel):
    """Knowledge base model for API responses"""

    id: str
    company_id: str
    title: str
    content: str
    vector_id: str
    metadata: KnowledgeMetadata
    created_at: datetime

    @classmethod
    def from_db(cls, knowledge: KnowledgeBaseInDB) -> "KnowledgeBaseResponse":
        """
        Create KnowledgeBaseResponse from database model

        Args:
            knowledge: Knowledge base entry from database

        Returns:
            KnowledgeBaseResponse instance
        """
        return cls(
            id=str(knowledge.id),
            company_id=knowledge.company_id,
            title=knowledge.title,
            content=knowledge.content,
            vector_id=knowledge.vector_id,
            metadata=knowledge.metadata,
            created_at=knowledge.created_at,
        )


class KnowledgeSearchResult(BaseModel):
    """Knowledge base search result with similarity score"""

    id: str
    company_id: str
    title: str
    content: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    metadata: KnowledgeMetadata


# Export models
__all__ = [
    "KnowledgeMetadata",
    "KnowledgeBaseBase",
    "KnowledgeBaseCreate",
    "KnowledgeBaseInDB",
    "KnowledgeBaseResponse",
    "KnowledgeSearchResult",
]
