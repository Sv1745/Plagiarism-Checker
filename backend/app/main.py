from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import AnalysisResponse
from app.services.cleanup import cleanup_job_dir
from app.services.paper_search import PaperSearchService
from app.services.pipeline import run_analysis
from app.services.rewrite import Rewriter
from app.services.similarity import SimilarityEngine
from app.utils.files import ensure_data_dir, make_job_dirs, safe_filename


ensure_data_dir()
similarity_engine = SimilarityEngine()
paper_search = PaperSearchService()
rewriter = Rewriter(api_key=settings.gemini_api_key, model_name=settings.gemini_model)

app = FastAPI(title='Plagiarism Intelligence API', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, '*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/api/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/api/analyze', response_model=AnalysisResponse)
async def analyze_document(
    file: UploadFile = File(...),
    candidate_limit: int = Form(default=settings.max_candidate_papers),
    threshold: float = Form(default=settings.similarity_threshold),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail='Missing filename in upload.')

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {'.pdf', '.txt', '.md'}:
        raise HTTPException(status_code=400, detail='Only .pdf, .txt, and .md are supported.')

    _, input_dir, candidate_dir, output_dir = make_job_dirs()
    job_root = input_dir.parent

    target = input_dir / safe_filename(file.filename)
    with open(target, 'wb') as out:
        shutil.copyfileobj(file.file, out)

    try:
        result = run_analysis(
            input_file=target,
            similarity_engine=similarity_engine,
            paper_search_service=paper_search,
            rewriter=rewriter,
            candidate_dir=candidate_dir,
            threshold=threshold,
            candidate_limit=candidate_limit,
            input_filename=file.filename,
        )

        corrected_path = output_dir / 'corrected_document.txt'
        corrected_path.write_text(result['corrected_text'], encoding='utf-8')

        return AnalysisResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Analysis failed: {exc}')
    finally:
        if settings.auto_cleanup:
            cleanup_job_dir(job_root)


@app.get('/')
def root() -> dict[str, str]:
    return {'message': 'Plagiarism Intelligence API is running.', 'docs': '/docs'}
