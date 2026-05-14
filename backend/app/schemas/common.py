from typing import Literal

from pydantic import BaseModel, Field

ClaimType = Literal[
    "problem",
    "method_overview",
    "key_module",
    "algorithm_formula",
    "data_construction",
    "training_detail",
    "evaluation_protocol",
    "main_result",
    "limitation",
    "reproducibility",
    "other",
]


class EvidenceRef(BaseModel):
    claim_type: ClaimType = "other"
    page: str = ""
    section: str = ""
    chunk_id: str = ""
    quote: str = ""


class MissingItem(BaseModel):
    category: str
    item: str
    severity: str = Field(default="medium")
    evidence_or_reason: str = ""
    suggested_action: str = ""
