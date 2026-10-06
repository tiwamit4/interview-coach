# Development and Operations

[Back to README](../README.md)

## Docker

Requires Docker Engine and Docker Compose. If you do not already have a `.env`
file, copy `.env.example` to `.env` and set `GROQ_API_KEY` to your Groq API key.
Your existing `.env` can be used as-is.

Build and start both services:

```bash
docker compose up --build -d --wait
```

- Streamlit UI: http://localhost:8501
- API docs: http://localhost:8000/docs
- API health: http://localhost:8000/health

The services bind to localhost. Both run as a non-root user and share the
`app-data` Docker volume for generated files and SQLite history. Existing files
in your local `data/` directory are not imported automatically. Upload resumes
through the UI or API; local resumes, generated output, and `.env` are excluded
from the image. Compose passes the API key at runtime.

The UI calls the application helpers directly, so either service can also run
independently:

```bash
docker compose up --build -d ui
docker compose up --build -d api
```

View status and logs:

```bash
docker compose ps
docker compose logs -f
```

Stop the services while keeping saved data:

```bash
docker compose down
```

`docker compose down -v` also deletes the saved data volume. Health checks verify
that each server responds; they do not check Groq credentials or model access.
Browser audio recording works on localhost; remote microphone access requires
HTTPS.

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

Keep `LOG_LEVEL = "INFO"` in `config.py` to see completed API requests, upload
sizes, extraction and generation progress, validation, and saved output paths.
Set it to `"WARNING"` to show only warnings and errors. With Docker, follow the
terminal logs using `docker compose logs -f`.

## Project Structure

```text
api.py                     FastAPI app and router registration
api_backend/schemas.py     API request models
api_backend/helpers.py     FastAPI upload and output adapters
api_backend/exceptions.py  Service error to HTTP error mapping
api_backend/routes/        Questions, workflows, voice, extraction, analysis, history, sessions, health
streamlit_app.py           Streamlit launcher
services/extraction.py     Shared job description, resume, and audio extraction
services/generation.py     Shared question generation, prompts, and JSON parsing
services/result_models.py  Pydantic contracts for structured AI results
services/files.py          Shared filenames and text/JSON file saving
services/uploads.py        Shared upload validation and bounded reads
services/sessions.py       Persistent interview sessions and answer progression
services/session_models.py Session request validation
utils/database.py          SQLite transactions, WAL, busy timeouts, and cleanup
utils/http_client.py       Scraping timeouts and GET retries
api_backend/middleware.py  Request correlation and failure logging
utils/logging_utils.py     JSON application logs
streamlit_ui/              Streamlit UI, components, theme, and exports
streamlit_ui/tabs/         Individual feature modules and stable tab exports
streamlit_ui/helpers.py    Streamlit validation and error adapters
jd/extract_text.py         Job description extraction
resume/extract_text.py     Resume PDF extraction
voice/groq_voice_text.py   Speech-to-text helpers
utils/groq_service.py      Groq chat helper
utils/history.py           SQLite history helper
prompts/prompt.py          Prompt templates
scrap/web_search.py        Reusable Serper web search helper
streamlit_ui/exports.py    Markdown and PDF export helpers
config.py                  Models, generation, output paths, history, and recording settings
tests/                     API, shared service, and Streamlit workflow checks
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
