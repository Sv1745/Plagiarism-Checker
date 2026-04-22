const defaultApiBase =
  window.location.port === '5173'
    ? 'http://localhost:8000'
    : `${window.location.protocol}//${window.location.host}`;
const API_BASE = window.PLAG_API_BASE || defaultApiBase;

const form = document.getElementById('analyze-form');
const statusEl = document.getElementById('status');
const resultsEl = document.getElementById('results');
const copyBtn = document.getElementById('copy-btn');

const overallEl = document.getElementById('overall');
const plagEl = document.getElementById('plag');
const origEl = document.getElementById('orig');
const papersEl = document.getElementById('papers');
const sentencesEl = document.getElementById('sentences');
const correctedEl = document.getElementById('corrected');

function setStatus(message, options = {}) {
  const { error = false, loading = false } = options;
  statusEl.classList.remove('hidden');
  statusEl.classList.toggle('status-loading', loading);

  if (loading) {
    statusEl.innerHTML = `
      <div class="status-line">
        <span class="status-spinner" aria-hidden="true"></span>
        <span class="status-message">${message}</span>
        <span class="status-dots" aria-hidden="true"><span></span><span></span><span></span></span>
      </div>
      <div class="status-track" aria-hidden="true">
        <span class="status-bar"></span>
      </div>
    `;
  } else {
    statusEl.textContent = message;
  }

  statusEl.style.borderColor = error ? 'rgba(190,30,30,0.35)' : 'rgba(31,42,33,0.2)';
  statusEl.style.background = error ? '#ffeceb' : '#f8f9ed';
}

function showResults(data) {
  resultsEl.classList.remove('hidden');

  overallEl.textContent = `${data.overall_similarity.toFixed(2)}%`;
  plagEl.textContent = `${data.plagiarism_percent.toFixed(2)}%`;
  origEl.textContent = `${data.originality_score.toFixed(2)}%`;

  papersEl.innerHTML = data.candidate_papers.length
    ? data.candidate_papers
        .map(
          (paper) => `
        <article class="paper-item">
          <strong>${paper.title}</strong>
          <div>${paper.source} • Similarity ${paper.similarity.toFixed(2)}%</div>
          <a href="${paper.paper_url || paper.pdf_url}" target="_blank" rel="noreferrer">Open source</a>
        </article>
      `
        )
        .join('')
    : '<p>No downloadable candidate papers were found for this run.</p>';

  sentencesEl.innerHTML = data.plagiarized_sentences.length
    ? data.plagiarized_sentences
        .slice(0, 40)
        .map(
          (item) => `
        <article class="sentence-item">
          <div><strong>Match:</strong> ${(item.best_match_similarity * 100).toFixed(1)}%</div>
          <p><strong>Your sentence:</strong> ${item.original}</p>
          <p><strong>Matched sentence:</strong> ${item.matched_sentence}</p>
          <div>
            <strong>Source:</strong> ${item.matched_paper_title} (${item.matched_paper_source})
            • <a href="${item.matched_paper_url || item.matched_paper_pdf_url}" target="_blank" rel="noreferrer">Open paper</a>
          </div>
        </article>
      `
        )
        .join('')
    : '<p>No high-confidence sentence overlap detected.</p>';

  correctedEl.textContent = data.corrected_text;
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const submitButton = document.getElementById('analyze-btn');
  const formData = new FormData(form);

  setStatus('Running search, downloading papers, and analyzing semantic similarity...', {
    loading: true,
  });
  resultsEl.classList.add('hidden');
  submitButton.disabled = true;

  try {
    const response = await fetch(`${API_BASE}/api/analyze`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      throw new Error(errorPayload.detail || 'Request failed');
    }

    const data = await response.json();
    showResults(data);
    setStatus('Analysis finished. Review flagged sentences and revised text below.');
  } catch (error) {
    setStatus(`Analysis failed: ${error.message}`, { error: true });
  } finally {
    submitButton.disabled = false;
  }
});

copyBtn.addEventListener('click', async () => {
  const text = correctedEl.textContent.trim();
  if (!text) return;
  await navigator.clipboard.writeText(text);
  setStatus('Revised text copied to clipboard.');
});
