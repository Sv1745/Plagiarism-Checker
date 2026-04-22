from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import feedparser
import requests


@dataclass
class PaperCandidate:
    title: str
    source: str
    paper_url: str
    pdf_url: str


class PaperSearchService:
    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def find_candidates(self, query: str, limit: int = 5) -> list[PaperCandidate]:
        candidates: list[PaperCandidate] = []
        seen_pdf_urls: set[str] = set()
        source_results = [
            self._semantic_scholar(query, limit=limit),
            self._openalex(query, limit=limit),
            self._arxiv(query, limit=limit),
        ]

        # Round-robin merge avoids one source (often arXiv) crowding out others.
        idx = 0
        while len(candidates) < limit:
            added_any = False
            for batch in source_results:
                if idx >= len(batch):
                    continue
                item = batch[idx]
                if item.pdf_url and item.pdf_url not in seen_pdf_urls:
                    seen_pdf_urls.add(item.pdf_url)
                    candidates.append(item)
                    added_any = True
                    if len(candidates) >= limit:
                        break
            if not added_any and all(idx >= len(batch) for batch in source_results):
                break
            idx += 1

        return candidates

    def download_paper(self, paper: PaperCandidate, target_dir: Path) -> Path | None:
        try:
            response = requests.get(paper.pdf_url, timeout=self.timeout)
            response.raise_for_status()
        except Exception:
            return None

        fname = ''.join(ch for ch in paper.title if ch.isalnum() or ch in {' ', '_', '-'})
        fname = (fname.strip().replace(' ', '_')[:60] or 'paper') + '.pdf'
        file_path = target_dir / fname
        file_path.write_bytes(response.content)
        return file_path

    def find_arxiv_by_id(self, arxiv_id: str) -> PaperCandidate | None:
        url = f'https://export.arxiv.org/api/query?id_list={quote(arxiv_id)}'
        try:
            feed = feedparser.parse(url)
        except Exception:
            return None

        if not feed.entries:
            return None

        entry = feed.entries[0]
        pdf_url = ''
        for link in entry.get('links', []):
            if link.get('type') == 'application/pdf':
                pdf_url = link.get('href', '')
                break

        if not pdf_url:
            return None

        return PaperCandidate(
            title=entry.get('title', 'Untitled'),
            source='arXiv',
            paper_url=entry.get('id', ''),
            pdf_url=pdf_url,
        )

    def _semantic_scholar(self, query: str, limit: int = 5) -> list[PaperCandidate]:
        url = (
            'https://api.semanticscholar.org/graph/v1/paper/search'
            f'?query={quote(query)}&limit={limit}&fields=title,url,openAccessPdf'
        )
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json().get('data', [])
        except Exception:
            return []

        papers: list[PaperCandidate] = []
        for entry in data:
            pdf_obj = entry.get('openAccessPdf') or {}
            pdf_url = pdf_obj.get('url', '')
            if not pdf_url:
                continue
            papers.append(
                PaperCandidate(
                    title=entry.get('title', 'Untitled'),
                    source='Semantic Scholar',
                    paper_url=entry.get('url', ''),
                    pdf_url=pdf_url,
                )
            )
        return papers

    def _arxiv(self, query: str, limit: int = 5) -> list[PaperCandidate]:
        url = (
            'https://export.arxiv.org/api/query'
            f'?search_query=all:{quote(query)}&start=0&max_results={limit}'
        )
        try:
            feed = feedparser.parse(url)
        except Exception:
            return []

        papers: list[PaperCandidate] = []
        for entry in feed.entries:
            pdf_url = ''
            for link in entry.get('links', []):
                if link.get('type') == 'application/pdf':
                    pdf_url = link.get('href', '')
                    break

            if not pdf_url:
                continue

            papers.append(
                PaperCandidate(
                    title=entry.get('title', 'Untitled'),
                    source='arXiv',
                    paper_url=entry.get('id', ''),
                    pdf_url=pdf_url,
                )
            )

        return papers

    def _openalex(self, query: str, limit: int = 5) -> list[PaperCandidate]:
        url = (
            'https://api.openalex.org/works'
            f'?search={quote(query)}&filter=open_access.is_oa:true'
            f'&per-page={limit}&sort=relevance_score:desc'
        )
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json().get('results', [])
        except Exception:
            return []

        papers: list[PaperCandidate] = []
        for entry in data:
            open_access = entry.get('open_access') or {}
            best_oa = open_access.get('oa_url') or ''
            primary_location = entry.get('primary_location') or {}
            pdf_url = ''

            # Prefer explicit PDF in the best OA location when available.
            if isinstance(primary_location.get('pdf_url'), str):
                pdf_url = primary_location.get('pdf_url') or ''
            if not pdf_url and best_oa.lower().endswith('.pdf'):
                pdf_url = best_oa
            if not pdf_url:
                continue

            papers.append(
                PaperCandidate(
                    title=entry.get('display_name', 'Untitled'),
                    source='OpenAlex',
                    paper_url=entry.get('id', ''),
                    pdf_url=pdf_url,
                )
            )
        return papers
