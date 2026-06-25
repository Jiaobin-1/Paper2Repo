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
from app.services.usage_tracking import track_llm_usage

logger = logging.getLogger(__name__)

MISSING_JOB_ERROR_MESSAGE = "Analysis job was not found."
_analysis_executor: ThreadPoolExecutor | None = None
_submission_slots: threading.BoundedSemaphore | None = None
_executor_lock = threading.Lock()
_submitted_futures: dict[str, Future[None]] = {}
_futures_lock = threading.RLock()


@dataclass(frozen=True)
class AnalysisRunRequest:
    paper_id: str
    run_id: str
    pdf_path: str
    model_name: str | None


class AnalysisQueueFullError(RuntimeError):
    pass


def start_analysis_dispatcher() -> ThreadPoolExecutor:
    global _analysis_executor, _submission_slots
    with _executor_lock:
        if _analysis_executor is None:
            settings = get_settings()
            workers = max(1, settings.analysis_max_workers)
            queued_jobs = max(0, settings.analysis_max_queued_jobs)
            _analysis_executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="paper2repo-analysis")
            _submission_slots = threading.BoundedSemaphore(workers + queued_jobs)
        return _analysis_executor


def stop_analysis_dispatcher() -> None:
    global _analysis_executor, _submission_slots
    with _executor_lock:
        executor = _analysis_executor
        _analysis_executor = None
    if executor is not None:
        executor.shutdown(wait=True, cancel_futures=True)
    with _futures_lock:
        _submitted_futures.clear()
    _submission_slots = None


def submit_analysis(paper_id: str, run_id: str, pdf_path: str, model_name: str | None) -> Future[None]:
    with _futures_lock:
        existing = _submitted_futures.get(run_id)
        if existing is not None and not existing.done():
            return existing
        executor = start_analysis_dispatcher()
        _acquire_submission_slots(1)
        try:
            future = executor.submit(run_analysis_background, paper_id, run_id, pdf_path, model_name)
        except Exception:
            _release_submission_slot()
            raise
        _submitted_futures[run_id] = future
        _register_completion_callback(run_id, future)

    return future


def submit_batch_analysis(tasks: Sequence[AnalysisRunRequest]) -> list[Future[None]]:
    if not tasks:
        return []
    new_futures: list[tuple[str, Future[None]]] = []
    results: list[Future[None]] = []
    with _futures_lock:
        executor = start_analysis_dispatcher()
        new_tasks = [task for task in tasks if not _active_future(task.run_id)]
        _acquire_submission_slots(len(new_tasks))
        try:
            for task in tasks:
                existing = _active_future(task.run_id)
                if existing is not None:
                    results.append(existing)
                    continue
                future = executor.submit(
                    run_analysis_background,
                    task.paper_id,
                    task.run_id,
                    task.pdf_path,
                    task.model_name,
                )
                _submitted_futures[task.run_id] = future
                new_futures.append((task.run_id, future))
                results.append(future)
                _register_completion_callback(task.run_id, future)
        except Exception:
            for _ in range(len(new_tasks) - len(new_futures)):
                _release_submission_slot()
            raise

    return results


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
            with track_llm_usage(run_id):
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
        try:
            submit_analysis(
                job["paper_id"],
                job["run_id"],
                paper["file_path"],
                run.get("model_name"),
            )
        except AnalysisQueueFullError:
            break
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
            _release_submission_slot()


def _register_completion_callback(run_id: str, future: Future[None]) -> None:
    def forget_completed(completed: Future[None]) -> None:
        _forget_future(run_id, completed)

    future.add_done_callback(forget_completed)


def _active_future(run_id: str) -> Future[None] | None:
    future = _submitted_futures.get(run_id)
    return future if future is not None and not future.done() else None


def _acquire_submission_slots(count: int) -> None:
    if count <= 0:
        return
    slots = _submission_slots
    if slots is None:
        raise RuntimeError("Analysis dispatcher is not initialized.")
    acquired = 0
    for _ in range(count):
        if slots.acquire(blocking=False):
            acquired += 1
            continue
        for _ in range(acquired):
            slots.release()
        raise AnalysisQueueFullError("Analysis queue is full. Please retry later.")


def _release_submission_slot() -> None:
    slots = _submission_slots
    if slots is not None:
        slots.release()
