from pydantic import BaseModel, Field


class StorageAreaSummary(BaseModel):
    path: str
    file_count: int = Field(ge=0)
    byte_count: int = Field(ge=0)


class StorageCleanupCandidate(BaseModel):
    area: str
    path: str
    byte_count: int = Field(ge=0)
    age_hours: float = Field(ge=0)
    reason: str


class StorageSummaryResponse(BaseModel):
    uploads: StorageAreaSummary
    reports: StorageAreaSummary
    database: StorageAreaSummary
    total_bytes: int = Field(ge=0)
    orphan_file_count: int = Field(ge=0)
    orphan_bytes: int = Field(ge=0)
    cleanup_min_age_hours: int = Field(ge=0)
    cleanup_candidates: list[StorageCleanupCandidate]


class StorageCleanupResponse(BaseModel):
    dry_run: bool
    deleted_file_count: int = Field(ge=0)
    deleted_bytes: int = Field(ge=0)
    skipped_file_count: int = Field(ge=0)
    candidates: list[StorageCleanupCandidate]
