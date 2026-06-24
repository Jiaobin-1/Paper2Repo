from __future__ import annotations

import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.agents.graph import run_analysis
from app.core.config import get_settings
from app.core.database import (
    claim_analysis_job,
    complete_analysis_job,
    fail_analysis_job,
    get_paper,
    get_run,
    is_analysis_cancel_requested,
    list_recoverable_analysis_jobs,
    update_run_status,
)

logger = logging.getLogger(__name__)

MISSING_JOB_ERROR_MESSAGE = "Analysis job was not found."
_recovery_executor: ThreadPoolExecutor | None = None


@dataclass(frozen=True)
class AnalysisRunRequest:
    paper_id: str
    run_id: str
    pdf_path: str
    model_name: str | None


def run_analysis_background(paper_id: str, run_id: str, pdf_path: str, model_name: str | None) -> None:
    def record_progress(current_step: str, progress_percent: int) -> None:
        if is_analysis_cancel_requested(run_id):
            raise RuntimeError("Analysis canceled.")
        update_run_status(
            run_id,
            "running",
            current_step=current_step,
            progress_percent=progress_percent,
        )

    while True:
        try:
            claim_status = claim_analysis_job(run_id)
            if claim_status == "completed":
                return
            if claim_status == "missing":
                update_run_status(
                    run_id,
                    "failed",
                    error_message=MISSING_JOB_ERROR_MESSAGE,
                    completed=True,
                    current_step="failed",
                )
                return
            if claim_status == "canceled":
                update_run_status(
                    run_id,
                    "failed",
                    error_message="Analysis canceled.",
                    completed=True,
                    current_step="failed",
                )
                return
            update_run_status(run_id, "running", current_step="queued", progress_percent=0)
            run_analysis(
                paper_id=paper_id,
                run_id=run_id,
                pdf_path=pdf_path,
                model_name=model_name,
                progress_callback=record_progress,
            )
            update_run_status(
                run_id,
                "completed",
                completed=True,
                current_step="completed",
                progress_percent=100,
            )
            complete_analysis_job(run_id)
            return
        except Exception as exc:
            logger.exception("Analysis failed for run %s", run_id)
            try:
                job_status = fail_analysis_job(run_id, str(exc))
                if job_status == "pending":
                    update_run_status(
                        run_id,
                        "pending",
                        error_message=str(exc),
                        current_step="queued",
                        progress_percent=0,
                    )
                    continue
                if job_status == "canceled":
                    update_run_status(
                        run_id,
                        "failed",
                        error_message="Analysis canceled.",
                        completed=True,
                        current_step="failed",
                    )
                else:
                    update_run_status(
                        run_id,
                        "failed",
                        error_message=str(exc),
                        completed=True,
                        current_step="failed",
                    )
                return
            except Exception:
                logger.exception("Failed to update run status after error for run %s", run_id)
                return


def start_recoverable_analysis_jobs() -> None:
    global _recovery_executor
    jobs = list_recoverable_analysis_jobs()
    if not jobs:
        return
    settings = get_settings()
    if _recovery_executor is None:
        _recovery_executor = ThreadPoolExecutor(max_workers=max(1, settings.analysis_max_workers))
    for job in jobs:
        paper = get_paper(job["paper_id"])
        run = get_run(job["run_id"])
        if not paper:
            fail_analysis_job(job["run_id"], "Paper record was not found during recovery.")
            continue
        _recovery_executor.submit(
            run_analysis_background,
            job["paper_id"],
            job["run_id"],
            paper["file_path"],
            run.get("model_name") if run else None,
        )


def run_batch_analysis(tasks: Sequence[AnalysisRunRequest]) -> None:
    max_workers = max(1, get_settings().analysis_max_workers)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                run_analysis_background,
                task.paper_id,
                task.run_id,
                task.pdf_path,
                task.model_name,
            )
            for task in tasks
        ]
        for future in futures:
            try:
                future.result()
            except Exception:
                logger.exception("Batch analysis task failed")
