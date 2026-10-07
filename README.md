# Interview Coach

Prepare for interviews using your resume and a job description. Built with
FastAPI, Streamlit, Groq, and SQLite.

## Features

- Generate questions and interview preparation plans.
- Compare resume fit, improve resume bullets, and draft application messages.
- Practice spoken or written answers with a scoring rubric and quoted feedback.
- Save interview sessions with answer-based follow-up questions and resumable progress.
- Track score trends, recurring feedback, and topics needing practice.
- Download results as Markdown, PDF, or JSON where supported.

## Quick Start

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
.\.venv\Scripts\python.exe -m uvicorn api:app --reload
```

On macOS/Linux, use `python -m uvicorn api:app --reload` with the virtual
environment activated. Open http://localhost:8000/docs for interactive API docs.

## Docker

Set `GROQ_API_KEY` in `.env`, then run:

```bash
docker compose up --build -d --wait
docker compose logs -f
```

The UI uses port 8501 and the API uses port 8000. Saved data persists in the
shared Docker volume. `docker compose down` stops services and keeps saved data;
adding `-v` deletes it.

## Configuration and Tests

Edit [config.py](config.py) for model settings, upload limits, recording settings,
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
