# Interview Coach

Prepare for interviews using your resume and a job description. Built with
FastAPI, Bun + React, Groq, and SQLite. The original Streamlit UI is also available.

## Features

- Generate questions and interview preparation plans.
- Compare resume fit, improve resume bullets, and draft application messages.
- Record answers with a live transcript preview, then review the final text before scoring.
- Save interview sessions with answer-based follow-up questions and resumable progress.
- Track score trends, recurring feedback, and topics needing practice.
- Download results as Markdown, PDF, or JSON where supported.

## Code Layout

```text
streamlit_app.py   Streamlit launcher
frontend/web/     Bun + React frontend
frontend/streamlit_ui/  Original Streamlit UI
backend/    FastAPI entry point, routes, shared services, models, config, and CLI
tests/     API, service, UI, and optional browser checks
docs/      Usage, API, configuration, and development guides
data/      Local generated output and SQLite history (ignored by Git)
```

The Streamlit frontend imports shared backend services directly; it can run
without the API server. Run launch and test commands from the repository root.
The root `requirements.txt` installs the Python backend and Streamlit dependencies.
The Bun frontend has its own `package.json` and `bun.lock`.

## Bun Frontend

Start FastAPI from the project root:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.api:app --reload
```

Set your Groq key in the root `.env`. In another terminal:

```powershell
cd frontend/web
bun install
bun run dev
```

Open http://localhost:5173. See [Bun frontend guide](frontend/web/README.md) for
production builds, tests, Docker, and configuration.

## Streamlit Setup

Use Python 3.12 and run these commands from the `interview-coach` project folder.

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m streamlit run streamlit_app.py
```

Keep an existing `.env` instead of copying over it. Before starting Streamlit,
set `GROQ_API_KEY` in `.env` to your Groq API key. `SERPER_API_KEY` is optional
and only needed for the web search helper.

Open the UI at http://localhost:8501. The UI runs independently of the API.

## API

Start the API in another terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.api:app --reload
```

On macOS/Linux, use `python -m uvicorn backend.api:app --reload` with the virtual
environment activated. Open http://localhost:8000/docs for interactive API docs.

## Docker

Set `GROQ_API_KEY` in `.env`, then run:

```bash
docker compose up --build -d --wait
docker compose logs -f
```

The default stack starts Bun on http://localhost:3000 and FastAPI on
http://localhost:8000. To also start the preserved Streamlit UI on port 8501:

```powershell
docker compose --profile streamlit up --build -d --wait
```

View logs with `docker compose logs -f`. Stop services while keeping data with
`docker compose --profile streamlit down`. Saved data persists in the shared Docker
volume; adding `-v` to `down` deletes it.

## Configuration and Tests

Edit [backend/config.py](backend/config.py) for model settings, upload limits, recording settings,
timeouts, and output paths; restart services after changes. Generated files and
SQLite history/session data live in `data/`. Application logs appear in the
terminal. Local secrets, uploads, and generated data are excluded from Git.

Run tests with the virtual environment activated (on Windows, replace `python`
with `.\.venv\Scripts\python.exe`):

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Tests mock external services and need no API keys. GitHub Actions runs them on
Python 3.12 on Windows and Linux for pushes and pull requests.

## Documentation

- [Usage guide](docs/usage.md): tabs, downloads, and interview sessions.
- [API reference](docs/api.md): endpoints, request examples, and session API.
- [Configuration and storage](docs/configuration.md): settings and output folders.
- [Development and operations](docs/development.md): Docker, reliability, logging, tests, and project structure.
