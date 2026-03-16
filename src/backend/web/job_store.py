"""Thread-safe in-memory job tracking for pipeline runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Lock


TERMINAL_STATUSES = {"succeeded", "failed"}


@dataclass(slots=True)
class JobRecord:
    """In-memory representation of one pipeline execution request."""

    job_id: str
    status: str
    delete_last_file: bool
    config_path: str | None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    result: dict | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        """Serialize job record for API responses."""

        return {
            "job_id": self.job_id,
            "status": self.status,
            "delete_last_file": self.delete_last_file,
            "config_path": self.config_path,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "result": self.result,
            "error": self.error,
        }


class InMemoryJobStore:
    """Small in-memory store suitable for single-process deployment."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[str, JobRecord] = {}
        self._counter = 0

    def create_job(self, *, delete_last_file: bool, config_path: str | None) -> JobRecord:
        with self._lock:
            self._counter += 1
            job_id = f"job-{self._counter:04d}"
            record = JobRecord(
                job_id=job_id,
                status="queued",
                delete_last_file=delete_last_file,
                config_path=config_path,
            )
            self._jobs[job_id] = record
            return record

    def get_job(self, job_id: str) -> JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            return JobRecord(**asdict(record))

    def mark_running(self, job_id: str) -> JobRecord:
        return self._update(job_id=job_id, status="running", error=None)

    def mark_succeeded(self, job_id: str, result: dict) -> JobRecord:
        return self._update(job_id=job_id, status="succeeded", result=result, error=None)

    def mark_failed(self, job_id: str, error: str) -> JobRecord:
        return self._update(job_id=job_id, status="failed", error=error, result=None)

    def _update(self, job_id: str, **changes) -> JobRecord:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"Unknown job_id: {job_id}")
            record = self._jobs[job_id]
            for key, value in changes.items():
                setattr(record, key, value)
            record.updated_at = datetime.now(timezone.utc)
            return JobRecord(**asdict(record))
