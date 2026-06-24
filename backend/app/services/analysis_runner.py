from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Sequence
from concurrent.futures import Future, ThreadPoolExecutor
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
    renew_analysis_job_lease,
    update_run_status,
)

logger = logging.getLogger(__name__)

MISSING_JOB_ERROR_MESSAGE = "Analysis job was not found."
_analysis_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()
_submitted_futures: dict[str, Future[None]] = {}
_futures_lock = threading.Lock()


@dataclass(frozen=True)
class AnalysisRunRequest:
    paper_id: str
    run_id: str
    pdf_path: str
    model_name: str | None


def start_analysis_dispatcher() -> ThreadPoolExecutor:
    global _analysis_executor
    with _executor_lock:
        if _analysis_executor is None:
            workers = max(1, get_settings().analysis_max_workers)
            _analysis_executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="paper2repo-analysis")
        return _analysis_executor


def stop_analysis_dispatcher() -> None:
    global _analysis_executor
    with _executor_lock:
        executor = _analysis_executor
        _analysis_executor = None
    if executor is not None:
        executor.shutdown(wait=True, cancel_futures=True)
    with _futures_lock:
        _submitted_futures.clear()


def submit_analysis(paper_id: str, run_id: str, pdf_path: str, model_name: str | None) -> Future[None]:
    with _futures_lock:
        existing = _submitted_futures.get(run_id)
        if existing is not None and not existing.done():
            return existing
        executor = start_analysis_dispatcher()
        future = executor.submit(run_analysis_background, paper_id, run_id, pdf_path, model_name)
        _submitted_futures[run_id] = future

    def forget_completed(completed: Future[None]) -> None:
        _forget_future(run_id, completed)

    future.add_done_callback(forget_completed)
    return future


def submit_batch_analysis(tasks: Sequence[AnalysisRunRequest]) -> list[Future[None]]:
    return [submit_analysis(task.paper_id, task.run_id, task.pdf_path, task.model_name) for task in tasks]


def run_analysis_background(paper_id: str, run_id: str, pdf_path: str, model_name: str | None) -> None:
    def record_progress(current_step: str, progress_percent: int) -> None:
        if is_analysis_cancel_requested(run_id):
            raise RuntimeError("Analysis canceled.")
        renew_analysis_job_lease(run_id)
        update_run_status(
            run_id,
            "running",
            current_step=current_step,
            progress_percent=progress_percent,
        )

    while True:
        try:
            claim_status = claim_analysis_job(run_id)
            if claim_status in {"completed", "busy"}:
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
                _mark_run_canceled(run_id)
                return
            update_run_status(run_id, "running", current_step="queued", progress_percent=0)
            run_analysis(
                paper_id=paper_id,
                run_id=run_id,
                pdf_path=pdf_path,
                model_name=model_name,
                progress_callback=record_progress,
            )
            if is_analysis_cancel_requested(run_id):
                raise RuntimeError("Analysis canceled.")
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
            if str(exc) == "Analysis canceled.":
                logger.info("Analysis canceled for run %s", run_id)
            else:
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
                    _mark_run_canceled(run_id)
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


def start_recoverable_analysis_jobs() -> int:
    submitted = 0
    for job in list_recoverable_analysis_jobs():
        paper = get_paper(job["paper_id"])
        run = get_run(job["run_id"])
        if not paper or not run:
            fail_analysis_job(job["run_id"], "Paper or run record was not found during recovery.")
            continue
        submit_analysis(
            job["paper_id"],
            job["run_id"],
            paper["file_path"],
            run.get("model_name"),
        )
        submitted += 1
    return submitted


async def recover_analysis_jobs_forever() -> None:
    interval = max(5, get_settings().analysis_recovery_interval_seconds)
    while True:
        await asyncio.sleep(interval)
        try:
            start_recoverable_analysis_jobs()
        except Exception:
            logger.exception("Periodic analysis job recovery failed")


def _mark_run_canceled(run_id: str) -> None:
    update_run_status(
        run_id,
        "failed",
        error_message="Analysis canceled.",
        completed=True,
        current_step="failed",
    )


def _forget_future(run_id: str, future: Future[None]) -> None:
    with _futures_lock:
        if _submitted_futures.get(run_id) is future:
            _submitted_futures.pop(run_id, None)
