from pydantic import BaseModel, Field


class PageText(BaseModel):
    page_number: int = Field(..., ge=1)
    text: str
    extraction_method: str = "native"
    tables: list[str] = Field(default_factory=list)
    formulas: list[str] = Field(default_factory=list)


class SectionCandidate(BaseModel):
    title: str
    page_number: int = Field(..., ge=1)
    level: int = Field(default=1, ge=1, le=6)


class ParsedPaper(BaseModel):
    raw_text: str
    page_texts: list[PageText]
    section_candidates: list[SectionCandidate]
    page_count: int = Field(..., ge=0)
    ocr_page_count: int = Field(default=0, ge=0)
    table_count: int = Field(default=0, ge=0)
    formula_count: int = Field(default=0, ge=0)
