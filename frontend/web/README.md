# Interview Coach · Bun frontend

A React + TypeScript frontend managed and run with Bun. The original Streamlit UI
remains in `frontend/streamlit_ui/`, launched with root `streamlit_app.py`.

## Development

Start the API from the repository root:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.api:app --reload
```

Put `GROQ_API_KEY=your-key` in the repository root `.env`. Keys are read only by
the Python backend; do not put credentials in browser environment variables.

In a separate terminal:

```powershell
cd frontend/web
bun install
bun run dev
```

Open http://localhost:5173. Vite proxies `/api/*` to http://127.0.0.1:8000.
Set `BACKEND_URL` when launching Bun to use a different API origin. The API docs
link defaults to http://localhost:8000/docs; set `VITE_API_DOCS_URL` before building
if your browser should use another URL.

## Included workflows

- Resume/job fit analysis and skill gaps.
- Questions from a resume, job description, both, or pasted text.
- Interview preparation, resume optimization, and application messages.
- Full analysis combining fit, prep, and resume improvements.
- Voice recording with live browser preview, audio upload, editable Groq
  transcription, and quoted rubric feedback.
- Saved interview sessions with follow-ups, answer review, resume, and completion.
- Progress charts, repeated feedback, topic priorities, and targeted practice.
- Saved history with search and result review.
- JSON/Markdown downloads and browser printing to PDF.
- Light/dark appearance, mobile navigation, and accessible form/error states.

Upload and recording limits come from the backend's `/ui-config` endpoint. Live
preview uses browser speech recognition and may send audio to its provider.
Support depends on browser and permission; recording still works without preview.
Use HTTPS or localhost for microphone access. Only the final reviewed text is
sent for evaluation. Successful final transcription is not repeated on edits.
Changing away from Voice Practice or Sessions releases the microphone; unsubmitted
answers on those screens are not saved. Session progress persists on the backend.

File saving can be disabled, but the backend still adds generated responses and
transcriptions to history, matching existing API behavior. This app uses the
existing shared history/session database and has no user accounts.

## Build, run, and test

```powershell
bun run build
bun run start
bun test
```

Production uses Bun on http://localhost:3000 to serve `dist/` and proxy `/api/*`.
Set `BACKEND_URL`, `PORT`, or `HOST` in the server environment as needed. Production
builds require no CDN, frontend credentials, or frontend build tools at runtime.
`bun.lock` pins dependencies; use `bun install --frozen-lockfile` for reproducible
installs. `bun run build` includes TypeScript checking.

From the repository root, start the Bun frontend and backend:

```powershell
docker compose up --build -d --wait
```

- Bun frontend: http://localhost:3000
- FastAPI docs: http://localhost:8000/docs

The default stack contains only Bun and FastAPI. To include the preserved
Streamlit app at http://localhost:8501, run:

```powershell
docker compose --profile streamlit up --build -d --wait
```

The API image includes backend dependencies; the separate Streamlit target adds
its UI dependencies. Both Python services share the persistent `app-data` volume.
The Bun container holds no API key or application database. API keys are injected
into Python services at runtime. All ports bind to localhost.

```powershell
docker compose ps
docker compose logs -f api web
docker compose --profile streamlit down
```

Stopping keeps saved data. Adding `-v` to `down` deletes the data volume.
