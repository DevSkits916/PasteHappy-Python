from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _number(name: str, fallback: int) -> int:
    try:
        return int(os.environ.get(name, fallback))
    except (TypeError, ValueError):
        return fallback


@dataclass(frozen=True)
class Config:
    root: Path
    port: int
    data_path: Path
    profile_path: Path
    executable_path: str | None
    headless: bool
    default_job_delay: int
    max_jobs_per_run: int

    @classmethod
    def from_environment(cls, root: Path | None = None) -> "Config":
        project_root = (root or Path.cwd()).resolve()
        return cls(
            root=project_root,
            port=_number("PORT", 4173),
            data_path=(project_root / os.environ.get("QUEUE_DATA_PATH", "data/queue.json")).resolve(),
            profile_path=(project_root / os.environ.get("BROWSER_PROFILE_PATH", ".browser-profile")).resolve(),
            executable_path=os.environ.get("PLAYWRIGHT_EXECUTABLE_PATH") or None,
            headless=os.environ.get("PLAYWRIGHT_HEADLESS", "false").lower() == "true",
            default_job_delay=_number("DEFAULT_JOB_DELAY", 15000),
            max_jobs_per_run=_number("MAX_JOBS_PER_RUN", 10),
        )
