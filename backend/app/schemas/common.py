from pydantic import BaseModel, Field


class EvidenceRef(BaseModel):
    claim: str = ""
    page: str = ""
    section: str = ""
    quote: str = ""
    role: str = "other"


class MissingItem(BaseModel):
    category: str
    item: str
    severity: str = Field(default="medium")
    evidence_or_reason: str = ""
    suggested_action: str = ""
