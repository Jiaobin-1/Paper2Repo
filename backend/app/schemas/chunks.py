from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    chunk_index: int = Field(..., ge=0)
    page_start: int = Field(..., ge=1)
    page_end: int = Field(..., ge=1)
    section_title: str | None = None
    token_estimate: int = Field(default=0, ge=0)


class PaperChunk(BaseModel):
    content: str
    metadata: ChunkMetadata


class ChunkedPaper(BaseModel):
    chunks: list[PaperChunk]
    chunk_count: int = Field(..., ge=0)


class RetrievedChunk(BaseModel):
    content: str
    metadata: ChunkMetadata
    score: float = Field(..., ge=0)
    matched_terms: list[str] = Field(default_factory=list)
