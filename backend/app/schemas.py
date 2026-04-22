from pydantic import BaseModel


class CandidatePaper(BaseModel):
    title: str
    source: str
    paper_url: str
    pdf_url: str
    similarity: float


class PlagiarizedSentence(BaseModel):
    original: str
    best_match_similarity: float
    matched_sentence: str
    matched_paper_title: str
    matched_paper_source: str
    matched_paper_url: str
    matched_paper_pdf_url: str


class AnalysisResponse(BaseModel):
    overall_similarity: float
    plagiarism_percent: float
    originality_score: float
    candidate_papers: list[CandidatePaper]
    plagiarized_sentences: list[PlagiarizedSentence]
    corrected_text: str
