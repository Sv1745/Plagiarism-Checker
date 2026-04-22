from __future__ import annotations

import os
import uuid
from pathlib import Path


BASE_JOBS_DIR = Path('data/jobs')


def make_job_dirs() -> tuple[str, Path, Path, Path]:
    job_id = uuid.uuid4().hex
    job_dir = BASE_JOBS_DIR / job_id
    input_dir = job_dir / 'input'
    candidates_dir = job_dir / 'candidates'
    output_dir = job_dir / 'output'

    input_dir.mkdir(parents=True, exist_ok=True)
    candidates_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    return job_id, input_dir, candidates_dir, output_dir


def safe_filename(name: str) -> str:
    clean = ''.join(ch for ch in name if ch.isalnum() or ch in {'-', '_', '.'}).strip('.')
    return clean or 'uploaded_file.txt'


def ensure_data_dir() -> None:
    os.makedirs(BASE_JOBS_DIR, exist_ok=True)
