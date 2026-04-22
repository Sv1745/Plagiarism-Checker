from __future__ import annotations

import shutil
from pathlib import Path


def cleanup_job_dir(job_dir: Path) -> None:
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
