# Development and Operations

[Back to README](../README.md)

## Docker

Requires Docker Engine and Docker Compose. Set `GROQ_API_KEY` in the root `.env`,
then build and start the default Bun + FastAPI stack:

```powershell
docker compose up --build -d --wait
```

- Bun frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- API health through Bun: http://localhost:3000/api/health

Streamlit is optional. To start it as well on port 8501:

```powershell
docker compose --profile streamlit up --build -d --wait
```

Stop any local process using port 8501 before enabling that profile. Bun connects
to FastAPI over the internal Compose network and exposes a same-origin `/api`
proxy to the browser. Ports bind to localhost. All three image targets run as
non-root users, and the API image does not install Streamlit.

API and optional Streamlit share the `app-data` Docker volume for generated files
and SQLite history. The Bun container stores no application data. Existing files
in your local `data/` directory are not imported automatically. Source `.env`,
local uploads, recordings, and generated data are excluded from images. Compose
passes API keys only to Python containers at runtime.

```powershell
docker compose ps
docker compose logs -f api web
docker compose --profile streamlit down
```

Stopping preserves the data volume; `down -v` deletes it. Health checks verify
server availability without contacting Groq or checking its credentials. Browser
recording works on localhost; remote microphone access requires HTTPS.

## Error Handling

The app now returns clearer errors for common failure modes:

| Case | Behavior |
| --- | --- |
| Bad JD URL | Shows a message asking for a valid `http://` or `https://` URL |
| JD page cannot be fetched | Reports the fetch problem or HTTP status |
| JD page has no usable text | Suggests using a public JD URL or pasted JD text |
| Missing `GROQ_API_KEY` | Explains that the key must be added to `.env` |
| Groq API failure | Reports a service failure and suggests checking key, quota, and network |
| Invalid AI result | Reports the result type and invalid fields before saving or displaying it |
| Oversized upload | Returns `413` from the API or shows a size-limit error in Streamlit |
| Oversized chat input | Returns `400` or asks the user to shorten the documents before contacting Groq |
| Truncated AI response | Retries with a larger output budget, then reports a clear error if the configured cap is reached |

FastAPI maps expected errors to more useful statuses: bad JD URLs return `400`, empty scraped pages return `422`, and Groq service failures return `502`.

Structured AI output is validated by shared Pydantic models for match analysis,
interview preparation, application messages, resume improvements, and voice
evaluation. All expected fields are required; nested items and types are checked,
text must be nonblank, and scores must be integers from 0 to 100. Empty lists are
allowed, while unexpected fields are rejected. Plain question responses must
contain nonblank text.

Invalid results return `502` from the API and a clear error in Streamlit. They are
not saved or passed to result renderers. Validation checks the output structure;
it does not establish whether AI statements are factually correct.

## Reliability

Async API routes offload scraping, document parsing, Groq requests, file writes,
and history writes to worker threads. A slow generation request does not block
the event loop or health checks.

SQLite connections commit successful transactions, roll back failed ones, and
close explicitly. WAL mode supports concurrent readers, and the configured busy
timeout handles overlapping writes. Session answer saves use a short atomic
transaction; Groq evaluation runs outside it. Concurrent submissions for the
same question cannot overwrite answers or advance twice.

Chat requests check the entire formatted prompt against a conservative UTF-8
byte budget before contacting Groq. Oversized inputs are rejected with a request
to select relevant sections; documents are not silently truncated or summarized.
The byte budget is an application limit, not a model tokenizer measurement.
When Groq reports an output-limit truncation, generation retries with a larger
completion budget up to the configured cap. Partial responses are not saved or
sent to result renderers.

Groq uses explicit timeouts and its SDK's bounded retries for temporary failures.
Scraping retries GET requests on connection failures and HTTP 429/500/502/503/504
with a bounded backoff. Authentication errors and other permanent failures are
not repeatedly retried. Web search POST requests use configured timeouts without
automatic retries.

Resume uploads default to a 10 MiB limit and audio uploads to 25 MiB. Streamlit
upload widgets use these limits, and shared extraction checks also cover live
recordings. The API checks each file's reported size and uses bounded reads to
enforce limits even when size metadata is absent or inaccurate. Limits apply to
individual files after multipart parsing.

Generated text and JSON files use UTF-8. Each save appends a unique identifier to
the filename and opens it exclusively, preserving existing outputs even when
multiple requests use the same source name. Failed writes remove their partial
file. JSON payloads, API responses, and history entries reference the actual
allocated output path.

Application activity and errors are logged as JSON to stderr, visible directly
in the terminal where you start the API or Streamlit UI, or through
`docker compose logs`. Logs include UTC timestamps, event names, error types,
operation or route details, and traceback locations. API errors share a request
identifier with the response's `X-Request-ID` header. Request bodies, API keys,
and raw exception messages are excluded from application log records. Unexpected
API errors return a generic JSON `500` response while diagnostic locations are
logged.

Keep `LOG_LEVEL = "INFO"` in `backend/config.py` to see completed API requests, upload
sizes, extraction and generation progress, validation, and saved output paths.
Set it to `"WARNING"` to show only warnings and errors. With Docker, follow the
terminal logs using `docker compose logs -f`.

## Project Structure

```text
backend/
  api.py                   FastAPI app and router registration
  api_backend/             HTTP routes, request models, middleware, and adapters
  services/                Shared extraction, generation, validation, sessions, and progress
  utils/                   Database, history, HTTP, Groq, uploads, and logs
  jd/  resume/  voice/      Job description, resume, and speech extraction
  prompts/                 Prompt templates
  scrap/                   Optional Serper web search helper
  config.py                Shared models, paths, limits, and recording settings
  errors.py                Application errors
  main.py                  Standalone document workflow
  requirements.txt         Backend dependencies
frontend/
  streamlit_ui/            Feature tabs, components, theme, exports, and recorder
    live_recorder/         Browser recording assets; no build step required
  requirements.txt         Streamlit dependency
streamlit_app.py           Streamlit launcher
tests/                     Integration, service, UI, and optional browser checks
docs/                      Detailed guides
requirements.txt           Installs frontend and backend dependencies
requirements-dev.txt       Development/test dependencies
.env.example               Safe API-key placeholder for local setup
Dockerfile  compose.yaml   Shared image and service launch configuration
data/                      Generated files and SQLite history (ignored by Git)
```

## Automated Tests

Install test dependencies and run the suite from the project root with the
virtual environment activated (or use `.\.venv\Scripts\python.exe` on Windows):

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Tests use mocked external services and do not require API keys. They cover API
and UI workflows, result validation, upload limits, file integrity, concurrency,
database cleanup, provider retries, input/output budgets, and persistent sessions.

`.github/workflows/tests.yml` runs the suite on Python 3.12 on Windows and Linux
for every GitHub push and pull request. The workflow becomes active when this
project is committed and pushed to a GitHub repository.

## Live Recorder Browser Checks

The recorder frontend lives in `frontend/streamlit_ui/live_recorder/` and uses browser
MediaRecorder, Web Audio, and speech recognition APIs. There is no frontend build
step or CDN dependency. Python validates returned audio before final transcription.
The normal unit suite tests decoding limits, transcript caching, corrections,
stale-answer prevention, and transcription retries.

Optional browser checks use Playwright with a fake microphone and mocked speech
results. They verify live interim/final transcript updates before recording stops,
audio transfer through iframe messages, missing recognition support, and recognition
errors. They do not assess an actual speech provider's accuracy.

```bash
python -m pip install playwright
python -m playwright install chromium
python tests/browser_live_recorder.py
```

To use an installed compatible browser instead, set `INTERVIEW_BROWSER_EXECUTABLE`
to its executable path. Manually test real microphone recognition in your target
browser before deployment.


## Package Boundaries

Backend code uses explicit `backend.*` imports and does not import the frontend.
Frontend code uses `frontend.streamlit_ui.*` for presentation and `backend.*` for
shared services. Streamlit still calls those services in-process; this directory
split does not require HTTP calls or a frontend framework migration.

Run from the repository root:

```bash
python -m uvicorn backend.api:app --reload
python -m streamlit run streamlit_app.py
python -m backend.main
python -m backend.voice.groq_voice_text
```

`data/`, `upload/`, and `.env` remain at the repository root. The configured voice
sample path now resolves inside `backend/voice/`. Existing local data is retained.

## Bun + React Frontend

The new browser app is in `frontend/web/`. It calls FastAPI over HTTP through a
same-origin `/api` proxy. Vite handles development and a small Bun server handles
production static files and proxying. The Streamlit UI remains available unchanged.
The proxy allows long model requests to complete; backend SDK timeouts still apply.
API keys are read only by Python. UI upload/recording limits are read from `/ui-config`.

See [the Bun frontend guide](../frontend/web/README.md) for setup, production,
Docker, and tests. The root Compose file starts `web` on port 3000 and API on port 8000.
The `streamlit` profile adds the preserved UI on port 8501. Frontend package versions are pinned in `bun.lock`.

Run the optional full-app browser checks after a production build:

```powershell
python -m pip install playwright
python -m playwright install chromium
python tests/browser_bun_frontend.py
```

Bun must be on PATH (or set `INTERVIEW_BUN_EXECUTABLE`). For an installed compatible
browser, set `INTERVIEW_BROWSER_EXECUTABLE`. Checks use isolated temporary database
state and mock generation, recording recognition, and transcription responses.
They exercise all workflows, voice corrections, session progression, charts,
history, downloads, mobile navigation, and console errors without Groq requests.


## Docker Targets and Startup

The root Dockerfile builds a backend-only `api` target and a `streamlit` target
that adds the Python UI. `frontend/web/Dockerfile` builds the React assets with
Bun, then serves them from a smaller Bun runtime image. All services run as
non-root users. The API and optional Streamlit UI share the named `app-data`
volume; source `.env`, uploads, recordings, and generated files are excluded
from build contexts. Compose injects the configured Groq key only into Python.

```powershell
docker compose up --build -d --wait
docker compose --profile streamlit up --build -d --wait
docker compose --profile streamlit down
```

The first command starts Bun and FastAPI. The second additionally starts Streamlit.
Bun waits for the API health check before starting. Health checks verify server
availability and do not consume Groq credits or validate provider credentials.
