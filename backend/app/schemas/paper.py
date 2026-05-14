from pydantic import BaseModel


class PaperResponse(BaseModel):
    id: str
    title: str | None = None
    filename: str
    file_path: str
    file_size: int
    created_at: str
    arxiv_id: str | None = None


class RunResponse(BaseModel):
    id: str
    paper_id: str
    status: str
    model_name: str | None = None
    current_step: str | None = None
    progress_percent: int = 0
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str
    updated_at: str


class RunListItemResponse(RunResponse):
    paper_title: str | None = None
    paper_filename: str


class BatchUploadResponse(BaseModel):
    papers: list[PaperResponse]


class BatchStartResponse(BaseModel):
    batch_id: str
    runs: list[RunResponse]


class BatchStatusResponse(BaseModel):
    batch_id: str
    runs: list[RunListItemResponse]
