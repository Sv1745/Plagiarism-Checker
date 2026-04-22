from __future__ import annotations

import re
from pathlib import Path

import fitz


def _normalize_extracted_text(text: str) -> str:
    # Join words split by PDF line-wrap hyphenation, then collapse noisy whitespace.
    text = text.replace('-\n', '')
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def read_file_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix == '.pdf':
        text_parts: list[str] = []
        doc = fitz.open(file_path)
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return _normalize_extracted_text(' '.join(text_parts))

    with open(file_path, 'rb') as handle:
        return _normalize_extracted_text(handle.read().decode(errors='ignore'))
