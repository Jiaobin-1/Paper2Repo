from pydantic import BaseModel, Field


class SectionInfo(BaseModel):
    title: str
    page_number: int = Field(..., ge=1)
    level: int = Field(default=1, ge=1, le=6)


class PaperMetadata(BaseModel):
    title: str = "Untitled Paper"
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    keywords: list[str] = Field(default_factory=list)
    sections: list[SectionInfo] = Field(default_factory=list)
