from __future__ import annotations

import re
from pathlib import Path

from app.schemas import CandidatePaper, PlagiarizedSentence
from app.services.paper_search import PaperSearchService
from app.services.rewrite import Rewriter
from app.services.similarity import CorpusSentence, SimilarityEngine, split_sentences
from app.services.text_extractor import read_file_text


def _search_query_from_text(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if lines:
        titleish = max(lines[:8], key=len)
        if len(titleish.split()) >= 6:
            return titleish[:300]

    tokens = text.split()
    return ' '.join(tokens[:45])


def _extract_arxiv_id(input_filename: str, text: str) -> str | None:
    patterns = [
        r'(\d{4}\.\d{4,5}(?:v\d+)?)',
        r'arxiv:\s*(\d{4}\.\d{4,5}(?:v\d+)?)',
    ]
    haystack = f'{input_filename} {text[:4000]}'
    for pattern in patterns:
        match = re.search(pattern, haystack, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def run_analysis(
    input_file: Path,
    similarity_engine: SimilarityEngine,
    paper_search_service: PaperSearchService,
    rewriter: Rewriter,
    candidate_dir: Path,
    threshold: float,
    candidate_limit: int,
    input_filename: str,
) -> dict:
    input_text = read_file_text(input_file)

    candidates = []
    seen_pdf_urls: set[str] = set()

    # If input appears to be an arXiv paper, force-include the exact arXiv record first.
    arxiv_id = _extract_arxiv_id(input_filename=input_filename, text=input_text)
    if arxiv_id:
        exact_arxiv = paper_search_service.find_arxiv_by_id(arxiv_id)
        if exact_arxiv and exact_arxiv.pdf_url:
            candidates.append(exact_arxiv)
            seen_pdf_urls.add(exact_arxiv.pdf_url)

    query = _search_query_from_text(input_text)
    for candidate in paper_search_service.find_candidates(query=query, limit=candidate_limit):
        if candidate.pdf_url in seen_pdf_urls:
            continue
        seen_pdf_urls.add(candidate.pdf_url)
        candidates.append(candidate)
        if len(candidates) >= candidate_limit:
            break

    evidence_corpus: list[CorpusSentence] = []
    paper_scores: list[CandidatePaper] = []

    for candidate in candidates:
        pdf_path = paper_search_service.download_paper(candidate, candidate_dir)
        if not pdf_path:
            continue

        candidate_text = read_file_text(pdf_path)
        if not candidate_text.strip():
            continue

        for sentence in split_sentences(candidate_text):
            evidence_corpus.append(
                CorpusSentence(
                    sentence=sentence,
                    paper_title=candidate.title,
                    paper_source=candidate.source,
                    paper_url=candidate.paper_url,
                    paper_pdf_url=candidate.pdf_url,
                )
            )

        doc_sim = similarity_engine.doc_similarity_percent(input_text, candidate_text)
        paper_scores.append(
            CandidatePaper(
                title=candidate.title,
                source=candidate.source,
                paper_url=candidate.paper_url,
                pdf_url=candidate.pdf_url,
                similarity=doc_sim,
            )
        )

    paper_scores.sort(key=lambda p: p.similarity, reverse=True)

    matches = similarity_engine.sentence_matches_with_evidence(
        source_text=input_text,
        corpus_entries=evidence_corpus,
        threshold=threshold,
    )

    plagiarized_sentences = [
        PlagiarizedSentence(
            original=m.original_sentence,
            best_match_similarity=m.score,
            matched_sentence=m.matched_sentence,
            matched_paper_title=m.paper_title,
            matched_paper_source=m.paper_source,
            matched_paper_url=m.paper_url,
            matched_paper_pdf_url=m.paper_pdf_url,
        )
        for m in matches
    ]

    all_source_sentences = split_sentences(input_text)
    total_sentence_count = max(len(all_source_sentences), 1)

    rewritten_map: dict[str, str] = {}
    for m in matches:
        rewritten_map[m.original_sentence] = rewriter.rewrite(m.original_sentence)

    corrected_text = input_text
    for old_sentence, new_sentence in rewritten_map.items():
        corrected_text = corrected_text.replace(old_sentence, new_sentence)

    overall_similarity = paper_scores[0].similarity if paper_scores else 0.0
    plagiarism_percent = (len(matches) / total_sentence_count) * 100
    originality_score = max(0.0, 100 - plagiarism_percent)

    return {
        'overall_similarity': overall_similarity,
        'plagiarism_percent': plagiarism_percent,
        'originality_score': originality_score,
        'candidate_papers': paper_scores,
        'plagiarized_sentences': plagiarized_sentences,
        'corrected_text': corrected_text,
    }
