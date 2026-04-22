# Plagiarism Intelligence Suite

Cloud-ready full-stack plagiarism analysis app with:
- Upload of an input paper (`.pdf`, `.txt`, `.md`)
- Online search for relevant papers via Semantic Scholar + arXiv
- Auto-download of candidate PDFs to VM storage
- Semantic plagiarism checks using sentence-transformer embeddings
- Gemini-powered rewrite of flagged sentences
- Automatic temporary-file cleanup after each run

## Architecture

- `backend/`: FastAPI service and analysis pipeline
- `frontend/`: Static web app (Nginx)
- `data/jobs/`: Temporary processing space (auto cleaned)
- `scripts/cleanup_jobs.sh`: Manual cleanup script

## Quick Start (Docker)

1. Create env file:
```bash
cp backend/.env.example backend/.env
```
2. Add your Gemini key in `backend/.env`.
3. Start:
```bash
docker compose up --build
```
4. Open frontend at `http://localhost:5173`
5. API docs at `http://localhost:8000/docs`

## Local Dev (without Docker)

Backend:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:
```bash
cd frontend
python -m http.server 5173
```

If backend runs on another host, set this before loading UI:
```html
<script>window.PLAG_API_BASE = "https://your-backend-domain";</script>
```

## Cloud Hosting Notes

### Backend (VM, ECS, GCP Cloud Run, Railway, Render)
- Deploy `backend/` container.
- Provide env vars from `.env.example`.
- Ensure outbound internet access for paper APIs + PDF download.
- Persist `/app/data` only if you want audit logs; otherwise ephemeral storage is enough.

### Frontend (Cloudflare Pages, Vercel, Netlify, VM Nginx)
- Deploy `frontend/` as static site.
- Point `window.PLAG_API_BASE` to backend URL.

### Oracle VM (Permanent self-hosted)
- Production-ready Oracle VM deployment files are in `deploy/oracle/`.
- Start with: `deploy/oracle/ORACLE_VM_DEPLOY.md`

## Cleanup Strategy

- Automatic: each request deletes its own temporary job folder (`AUTO_CLEANUP=true`).
- Manual fallback:
```bash
./scripts/cleanup_jobs.sh data/jobs
```
- Optional cron (every hour):
```bash
0 * * * * /bin/bash /path/to/project/scripts/cleanup_jobs.sh /path/to/project/data/jobs
```

## Important Considerations

- Rewriting should be reviewed by a human for factual fidelity and citation integrity.
- Similarity score is semantic, not a legal plagiarism verdict.
- For large papers, inference is CPU/GPU intensive; use worker queues for scale.

## API

### `POST /api/analyze`
Multipart form:
- `file`: uploaded paper
- `candidate_limit` (optional, default from env)
- `threshold` (optional, default from env)

Returns:
- Overall similarity
- Plagiarism percentage
- Originality score
- Candidate paper list with similarity
- Flagged sentences
- Rewritten document text
