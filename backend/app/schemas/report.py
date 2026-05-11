from pydantic import BaseModel


class MarkdownReport(BaseModel):
    title: str
    content: str
    file_path: str | None = None
    created_at: str | None = None


class PersistResult(BaseModel):
    paper_id: str
    run_id: str
    status: str
    report_path: str | None = None
