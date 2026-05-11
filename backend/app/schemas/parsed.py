from pydantic import BaseModel, Field


class PageText(BaseModel):
    page_number: int = Field(..., ge=1)
    text: str


class SectionCandidate(BaseModel):
    title: str
    page_number: int = Field(..., ge=1)
    level: int = Field(default=1, ge=1, le=6)


class ParsedPaper(BaseModel):
    raw_text: str
    page_texts: list[PageText]
    section_candidates: list[SectionCandidate]
    page_count: int = Field(..., ge=0)
