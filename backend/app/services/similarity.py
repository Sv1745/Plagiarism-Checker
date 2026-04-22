from __future__ import annotations

import re
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class SentenceMatch:
    sentence: str
    score: float


@dataclass
class CorpusSentence:
    sentence: str
    paper_title: str
    paper_source: str
    paper_url: str
    paper_pdf_url: str


@dataclass
class EvidenceMatch:
    original_sentence: str
    matched_sentence: str
    score: float
    paper_title: str
    paper_source: str
    paper_url: str
    paper_pdf_url: str


def split_sentences(text: str) -> list[str]:
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p and p.strip()]


def _normalize_sentence(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class SimilarityEngine:
    """Lightweight similarity using TF-IDF cosine scores."""

    @staticmethod
    def doc_similarity_percent(text_a: str, text_b: str) -> float:
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), min_df=1)
        matrix = vectorizer.fit_transform([text_a, text_b])
        return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0] * 100)

    @staticmethod
    def sentence_matches(source_text: str, corpus_text: str, threshold: float = 0.72) -> list[SentenceMatch]:
        source_sentences = split_sentences(source_text)
        corpus_sentences = split_sentences(corpus_text)

        if not source_sentences or not corpus_sentences:
            return []

        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), min_df=1)
        joined = source_sentences + corpus_sentences
        vectors = vectorizer.fit_transform(joined)

        source_vectors = vectors[: len(source_sentences)]
        corpus_vectors = vectors[len(source_sentences) :]

        sim_matrix = cosine_similarity(source_vectors, corpus_vectors)

        flagged: list[SentenceMatch] = []
        for idx, row in enumerate(sim_matrix):
            score = float(max(row))
            if score >= threshold and len(source_sentences[idx].split()) > 6:
                flagged.append(SentenceMatch(sentence=source_sentences[idx], score=score))

        return flagged

    @staticmethod
    def sentence_matches_with_evidence(
        source_text: str,
        corpus_entries: list[CorpusSentence],
        threshold: float = 0.72,
    ) -> list[EvidenceMatch]:
        source_sentences = split_sentences(source_text)
        clean_corpus = [entry for entry in corpus_entries if entry.sentence.strip()]

        if not source_sentences or not clean_corpus:
            return []

        corpus_sentences = [entry.sentence for entry in clean_corpus]
        # Pass 1: exact normalized sentence hit (fast and robust for copied text from PDF sources).
        exact_index: dict[str, CorpusSentence] = {}
        for entry in clean_corpus:
            norm = _normalize_sentence(entry.sentence)
            if norm and norm not in exact_index:
                exact_index[norm] = entry

        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), min_df=1)
        joined = source_sentences + corpus_sentences
        vectors = vectorizer.fit_transform(joined)

        source_vectors = vectors[: len(source_sentences)]
        corpus_vectors = vectors[len(source_sentences) :]
        sim_matrix = cosine_similarity(source_vectors, corpus_vectors)

        matches: list[EvidenceMatch] = []
        seen_source_sentences: set[str] = set()
        for idx, row in enumerate(sim_matrix):
            best_idx = int(row.argmax())
            score = float(row[best_idx])
            original_sentence = source_sentences[idx]
            if len(original_sentence.split()) <= 6:
                continue

            exact_hit = exact_index.get(_normalize_sentence(original_sentence))
            if exact_hit:
                if original_sentence in seen_source_sentences:
                    continue
                seen_source_sentences.add(original_sentence)
                matches.append(
                    EvidenceMatch(
                        original_sentence=original_sentence,
                        matched_sentence=exact_hit.sentence,
                        score=1.0,
                        paper_title=exact_hit.paper_title,
                        paper_source=exact_hit.paper_source,
                        paper_url=exact_hit.paper_url,
                        paper_pdf_url=exact_hit.paper_pdf_url,
                    )
                )
                continue

            if score < threshold:
                continue

            best_entry = clean_corpus[best_idx]
            if original_sentence in seen_source_sentences:
                continue
            seen_source_sentences.add(original_sentence)
            matches.append(
                EvidenceMatch(
                    original_sentence=original_sentence,
                    matched_sentence=best_entry.sentence,
                    score=score,
                    paper_title=best_entry.paper_title,
                    paper_source=best_entry.paper_source,
                    paper_url=best_entry.paper_url,
                    paper_pdf_url=best_entry.paper_pdf_url,
                )
            )

        return matches
