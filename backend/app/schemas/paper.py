from pydantic import BaseModel


class PaperResponse(BaseModel):
    id: str
    title: str | None = None
    filename: str
    file_path: str
    file_size: int
    created_at: str


class RunResponse(BaseModel):
    id: str
    paper_id: str
    status: str
    current_step: str | None = None
    progress_percent: int = 0
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str
