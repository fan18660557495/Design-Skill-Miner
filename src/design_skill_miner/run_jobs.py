from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from threading import Lock, Thread
from typing import Any
from uuid import uuid4


JobState = str


@dataclass
class JobRecord:
    run_id: str
    status: JobState
    stage: str
    message: str
    created_at: str
    updated_at: str
    target: str = "draft"
    error: str | None = None
    result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_JOBS: dict[str, JobRecord] = {}
_LOCK = Lock()


def create_job(*, target: str, message: str) -> JobRecord:
    now = _now()
    job = JobRecord(
        run_id=uuid4().hex,
        status="queued",
        stage="queued",
        message=message,
        created_at=now,
        updated_at=now,
        target=target,
    )
    with _LOCK:
        _JOBS[job.run_id] = job
    return job


def update_job(
    run_id: str,
    *,
    status: str | None = None,
    stage: str | None = None,
    message: str | None = None,
    error: str | None = None,
    result: dict[str, Any] | None = None,
) -> JobRecord:
    with _LOCK:
        job = _JOBS[run_id]
        if status is not None:
            job.status = status
        if stage is not None:
            job.stage = stage
        if message is not None:
            job.message = message
        if error is not None:
            job.error = error
        if result is not None:
            job.result = result
        job.updated_at = _now()
        return job


def get_job(run_id: str) -> JobRecord | None:
    with _LOCK:
        job = _JOBS.get(run_id)
        if job is None:
            return None
        return JobRecord(**job.to_dict())


def start_background_job(run_id: str, target: Any) -> None:
    thread = Thread(target=target, name=f"design-skill-miner-job-{run_id}", daemon=True)
    thread.start()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
