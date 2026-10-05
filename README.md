# Interview Coach

Interview Coach helps prepare for job interviews using a resume, a job description URL, and optional spoken interview answers. It has a FastAPI backend and a Streamlit UI.

## What It Does

- Scrapes job descriptions from URLs.
- Extracts text from resume PDFs.
- Generates JD + resume interview questions.
- Scores resume fit against a JD.
- Suggests missing skills and resume improvements.
- Generates tailored interview prep.
- Writes cover letters, recruiter messages, and LinkedIn DMs.
- Transcribes voice answers with Groq `whisper-large-v3` at temperature `0`.
- Stops live microphone recordings after 600 ms of detected silence.
- Evaluates interview answers and suggests better responses.
- Downloads generated outputs as Markdown, PDF, and JSON where applicable.
- Saves output history in SQLite.
- Runs persistent interview sessions with saved answers, feedback, scores, and progress.
- Handles bad JD URLs, empty scraped pages, missing API keys, and Groq failures with clearer messages.

## Local Setup

Use Python 3.12. The project folder and recommended GitHub repository name are
`interview-coach`; the app is displayed as **Interview Coach**. Run all commands
from the project root.

### Windows (PowerShell)

```powershell
cd D:\project\interview-coach
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Use your own project location in the `cd` command. If `.env` already exists,
keep it instead of copying over it.

### macOS / Linux

```bash
cd /path/to/interview-coach
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

If `.env` already exists, keep it instead of copying over it. Edit `.env` and set
`GROQ_API_KEY` to your Groq API key. Question generation, analysis, writing,
answer evaluation, and voice transcription require this key. Add
`SERPER_API_KEY` only if you use the optional search helper in
`scrap/web_search.py`.

### Start the App

On Windows, start Streamlit:

```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

To use the API, run this in a separate terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --reload
```

On macOS/Linux, use `python` in place of `.\.venv\Scripts\python.exe` after
activating the virtual environment. The UI uses shared services directly and
can run independently of the API.

- Streamlit UI: http://localhost:8501
- API documentation: http://localhost:8000/docs
- API health: http://localhost:8000/health

Application logs appear in the terminal that runs each service. Changes to
`config.py` require a service restart.

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

## Streamlit App

The Streamlit UI is the easiest way to use the project. After completing local
setup, activate the virtual environment before using the commands below. On
Windows, you can instead use `.\.venv\Scripts\python.exe` in place of `python`.

```bash
python -m streamlit run streamlit_app.py
```

Open:

```text
http://localhost:8501
```

If the port is busy:

```bash
python -m streamlit run streamlit_app.py --server.port 8502
```

### Streamlit Workflows

| Tab | Purpose |
| --- | --- |
| Analyze Fit | Resume vs JD match score, matched skills, missing skills, improvement suggestions |
| Questions | JD + resume interview questions |
| Interview Prep | Likely questions, resume-based answers, weak areas, project explanations |
| Resume Optimizer | Rewritten bullets, ATS keywords, missing project/skill suggestions |
| Application Writer | Cover letter, recruiter message, LinkedIn DM |
| Voice Practice | Record or paste answer, get score, feedback, better answer |
| Interview Sessions | Practice one question at a time, resume saved sessions, and compare progress |
| History | View saved outputs |

Most generated Streamlit outputs include download buttons:

| Output | Download Formats |
| --- | --- |
| Questions | Markdown, PDF |
| Match Analysis | Markdown, PDF, JSON |
| Interview Prep | Markdown, PDF, JSON |
| Application Messages | Markdown, PDF, JSON |
| Resume Improvements | Markdown, PDF, JSON |
| Voice Evaluation | Markdown, PDF, JSON |

### Streamlit Flow Details

#### Analyze Fit

1. Enter a job description URL.
2. Upload a resume PDF.
3. Click `Analyze Match`.
4. The app extracts JD text and resume text.
5. Groq compares both documents.
6. The app displays:
   - role fit score
   - summary
   - matched skills
   - missing skills
   - improvement suggestions
7. Download the result as Markdown, PDF, or JSON.
8. If saving is enabled, output is saved under:

```text
data/match/
```

#### Questions

1. Choose a question source:
   - `JD + Resume`
   - `Resume only`
   - `JD only`
   - `Text only`
2. Provide the required input:
   - JD URL
   - resume PDF
   - pasted text
3. Click `Generate Questions`.
4. The app generates interview questions for the selected source.
5. Download the questions as Markdown or PDF.
6. If saving is enabled, output is saved under:

```text
data/question/
```

#### Interview Prep

1. Enter a job description URL.
2. Upload a resume PDF.
3. Click `Generate Interview Prep`.
4. The app extracts both texts and generates:
   - likely interview questions
   - suggested answers based on resume evidence
   - weak areas to revise
   - project explanations to prepare
5. Download the prep plan as Markdown, PDF, or JSON.
6. If saving is enabled, output is saved under:

```text
data/prep/
```

#### Resume Optimizer

1. Enter a job description URL.
2. Upload a resume PDF.
3. Click `Improve Resume for JD`.
4. The app generates:
   - rewritten resume bullets
   - suggested ATS keywords
   - ATS optimization suggestions
   - missing project or skill suggestions
5. Download the suggestions as Markdown, PDF, or JSON.
6. If saving is enabled, output is saved under:

```text
data/resume_improvements/
```

#### Application Writer

1. Enter a job description URL.
2. Upload a resume PDF.
3. Click `Generate Application Messages`.
4. The app generates:
   - customized cover letter
   - short recruiter message
   - LinkedIn DM message
5. Download the messages as Markdown, PDF, or JSON.
6. If saving is enabled, output is saved under:

```text
data/applications/
```

#### Voice Practice

1. Enter an interview question.
2. Optionally enter a JD URL for role context.
3. Choose answer input:
   - record speech
   - paste text
   Live recording starts when you click the microphone and stops automatically
   after 600 ms of detected silence. Click again to record a new answer.
4. Click `Evaluate Answer`.
5. If audio is recorded, the app transcribes it first using Groq Whisper.
6. The app evaluates the answer and displays:
   - answer score
   - feedback
   - strengths
   - improvements
   - better answer
7. Download the evaluation as Markdown, PDF, or JSON.
8. If saving is enabled, output is saved under:

```text
data/voice_practice/
```

#### History

1. Choose how many saved items to show.
2. Select a history item.
3. The app displays the saved JSON payload.
4. History is stored in:

```text
data/history/interview_coach.db
```

### Interview Sessions

Open `Interview Sessions` and expand `Start a new session`. Enter a title and one
question per line; you can paste questions generated by the Questions tab. Add
optional role context, then click `Start Session`.

Select a saved session to continue. Paste or record an answer and click
`Submit Answer`. The app evaluates and saves it before advancing to the next
question. The latest feedback and all previous answers remain available after
reloading the app. A progress table compares answered questions, average scores,
and completion status across sessions. Sessions use the configured history
database, including the existing Docker data volume.

Session API endpoints:

| Endpoint | Purpose |
| --- | --- |
| `POST /sessions` | Create a session from a title, questions, and optional `role_context` |
| `GET /sessions` | List session progress and average scores |
| `GET /sessions/{session_id}` | Get the current question and saved answers |
| `POST /sessions/{session_id}/answers` | Evaluate an answer and advance one question |

Example request bodies:

```json
{"title": "Python practice", "questions": ["Explain your latest Python project.", "How did you test it?"], "role_context": "Python developer"}
```

```json
{"answer_text": "I built and tested a document extraction pipeline.", "expected_question_index": 0}
```

Question indices start at zero. Submit the `current_question_index` returned by
the session. Duplicate or stale answers return `409`, missing sessions return
`404`, and invalid inputs return `422`. Failed evaluation leaves the question
and saved progress unchanged. Audio answers can also be transcribed using
`/voice/run` before submitting the resulting text to the session API.

## FastAPI

Run the API from the project root with the virtual environment activated:

```bash
python -m uvicorn api:app --reload
```

Open docs:

```text
http://127.0.0.1:8000/docs
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Primary API Endpoints

These are the recommended APIs to use in new code.

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Check server status |
| `POST /questions` | Flexible question generation from JD, resume, text, or JD + resume |
| `POST /run` | Main text workflow endpoint |
| `POST /voice/run` | Main voice workflow endpoint |
| `POST /extract/jd-resume` | Extract JD + resume text into JSON |
| `GET /history` | List saved history |
| `GET /history/{item_id}` | Get one saved history item |

## Swagger Docs

FastAPI docs are available at:

```text
http://127.0.0.1:8000/docs
```

If some older APIs appear in Swagger, they are compatibility endpoints. Prefer the primary APIs above.

To hide compatibility APIs from Swagger, add `include_in_schema=False` to those
route decorators in `api_backend/routes/`:

```python
@router.post("/jd/questions", deprecated=True, include_in_schema=False)
def generate_jd_questions(...):
    ...
```

To group APIs into sections in Swagger, add tags:

```python
@router.post("/questions", tags=["Questions"])
@router.post("/run", tags=["Main"])
@router.post("/voice/run", tags=["Voice"])
@router.get("/history", tags=["History"])
```

## `POST /questions`

Use this when you only want interview questions. It accepts one flexible input endpoint.

| Input | Output |
| --- | --- |
| `resume` only | Resume-based questions |
| `jd_url` only | JD-based questions |
| `text` only | Text-based questions |
| `resume` + `jd_url` | Targeted JD + resume questions |

Resume only:

```bash
curl -X POST http://127.0.0.1:8000/questions \
  -F "resume=@upload/Amit_Resume_DS.pdf"
```

JD only:

```bash
curl -X POST http://127.0.0.1:8000/questions \
  -F "jd_url=https://careers.qualcomm.com/careers/job/446718764455"
```

JD + resume:

```bash
curl -X POST http://127.0.0.1:8000/questions \
  -F "jd_url=https://careers.qualcomm.com/careers/job/446718764455" \
  -F "resume=@upload/Amit_Resume_DS.pdf"
```

Text only:

```bash
curl -X POST http://127.0.0.1:8000/questions \
  -F "text=Paste resume or job description text here"
```

## `POST /run`

Use this for most text-based features.

### Supported Tasks

| Task | Required Inputs | Output |
| --- | --- | --- |
| `jd_questions` | `jd_url` | Questions from JD |
| `resume_questions` | `resume` or `text` | Questions from resume |
| `jd_resume_questions` | `jd_url`, `resume` | Questions from JD + resume |
| `match_score` | `jd_url`, `resume` | Fit score, matched skills, missing skills |
| `interview_prep` | `jd_url`, `resume` | Likely questions, answers, weak areas |
| `cover_letter` | `jd_url`, `resume` | Cover letter and messages |
| `resume_improvement` | `jd_url`, `resume` | Bullet rewrites, ATS keywords, gaps |
| `full_analysis` | `jd_url`, `resume` | Match score, interview prep, resume improvements |

### Examples

Match score:

```bash
curl -X POST http://127.0.0.1:8000/run \
  -F "task=match_score" \
  -F "jd_url=https://careers.qualcomm.com/careers/job/446718764455" \
  -F "resume=@upload/Amit_Resume_DS.pdf" \
  -F "save_output=true"
```

JD + resume questions:

```bash
curl -X POST http://127.0.0.1:8000/run \
  -F "task=jd_resume_questions" \
  -F "jd_url=https://careers.qualcomm.com/careers/job/446718764455" \
  -F "resume=@upload/Amit_Resume_DS.pdf"
```

Resume questions from pasted text:

```bash
curl -X POST http://127.0.0.1:8000/run \
  -F "task=resume_questions" \
  -F "text=Paste resume text here"
```

Full analysis:

```bash
curl -X POST http://127.0.0.1:8000/run \
  -F "task=full_analysis" \
  -F "jd_url=https://careers.qualcomm.com/careers/job/446718764455" \
  -F "resume=@upload/Amit_Resume_DS.pdf"
```

## `POST /voice/run`

Use this for voice transcription and voice interview practice.

### Supported Tasks

| Task | Required Inputs | Output |
| --- | --- | --- |
| `transcribe` | `audio` | Transcript |
| `evaluate_answer` | `question`, plus `answer_text` or `answer_audio` | Score, feedback, better answer |

### Examples

Transcribe audio:

```bash
curl -X POST http://127.0.0.1:8000/voice/run \
  -F "task=transcribe" \
  -F "audio=@voice/audio.m4a"
```

Evaluate pasted answer:

```bash
curl -X POST http://127.0.0.1:8000/voice/run \
  -F "task=evaluate_answer" \
  -F "question=Tell me about a machine learning project." \
  -F "answer_text=I built a sentiment analysis pipeline using TF-IDF and SVM."
```

Evaluate audio answer:

```bash
curl -X POST http://127.0.0.1:8000/voice/run \
  -F "task=evaluate_answer" \
  -F "question=Tell me about a machine learning project." \
  -F "answer_audio=@answer.wav"
```

## Extract JD + Resume

```bash
curl -X POST http://127.0.0.1:8000/extract/jd-resume \
  -F "jd_url=https://careers.qualcomm.com/careers/job/446718764455" \
  -F "resume=@upload/Amit_Resume_DS.pdf"
```

## History

```bash
curl http://127.0.0.1:8000/history
curl http://127.0.0.1:8000/history/1
```

History is stored in:

```text
data/history/interview_coach.db
```

## Application Configuration

Edit `config.py` before starting the API or UI, and restart the services after
changing settings. API keys remain in `.env`.

| Settings | Purpose |
| --- | --- |
| `CHAT_MODEL` | Groq chat model used by both API and UI |
| `QUESTION_TEMPERATURE`, `QUESTION_MAX_COMPLETION_TOKENS` | Generation settings for the basic question helper |
| `PROMPT_TEMPERATURE`, `PROMPT_MAX_COMPLETION_TOKENS` | Generation settings for named prompts, including structured output and combined questions |
| `CHAT_TOP_P`, `CHAT_STOP` | Sampling and stop sequences shared by chat requests |
| `DATA_PATH` and output folder constants | Root and individual folders for generated files |
| `DB_PATH` | SQLite history database location |
| `RECORDING_SILENCE_SECONDS`, `RECORDING_SAMPLE_RATE`, `RECORDING_AUTO_START` | Microphone silence threshold, sample rate, and automatic start |
| `MAX_RESUME_UPLOAD_MB`, `MAX_AUDIO_UPLOAD_MB` | Resume and audio upload limits in MiB (defaults: 10 and 25) |
| `UPLOAD_READ_CHUNK_BYTES` | Maximum chunk size for bounded API file reads |
| `LOG_LEVEL` | Structured application log level |
| `GROQ_TIMEOUT_SECONDS`, `GROQ_MAX_RETRIES` | Groq timeout per attempt and SDK retry count |
| `HTTP_CONNECT_TIMEOUT_SECONDS`, `HTTP_READ_TIMEOUT_SECONDS`, `HTTP_MAX_RETRIES` | Scraping connection/read timeouts and retry count |
| `HTTP_RETRY_BACKOFF_SECONDS`, `HTTP_RETRY_BACKOFF_MAX_SECONDS` | Bounded delay between scraping retries |
| `MAX_CHAT_PROMPT_BYTES` | Maximum UTF-8 size of the complete formatted prompt (64 KiB by default) |
| `CHAT_MAX_COMPLETION_TOKENS`, `CHAT_COMPLETION_EXPANSIONS` | Maximum output budget and number of retries with a larger budget |
| `SQLITE_BUSY_TIMEOUT_SECONDS` | Time to wait for database write locks |
| `MAX_SESSION_QUESTIONS`, `MAX_SESSION_ANSWER_CHARACTERS` | Session question count and answer size limits |

All output folders and the database location derive from `DATA_PATH` by default.
You can override individual folder constants or `DB_PATH` independently. Relative
paths resolve from the working directory. The UI's save labels and recording
caption reflect the configured values. Changing an output location does not move
existing files.

### Speech-to-Text

The standalone voice script reads its settings from `config.py`; no command-line
arguments are needed. Set `VOICE_AUDIO_PATH` to your audio file and adjust
`VOICE_MODEL`, `VOICE_LANGUAGE`, `VOICE_PROMPT`, `VOICE_RESPONSE_FORMAT`, and
`VOICE_TEMPERATURE` as needed. Set `VOICE_TRANSLATE = True` to translate speech
to English.

Run from the project root:

```bash
python -m voice.groq_voice_text
```

These voice defaults also apply to the API and UI helpers. The UI can override
the language and context prompt for individual recordings. API keys stay in
`.env`.

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

## Files Excluded from Git

`.gitignore` excludes local `.env` files, virtual environments, uploaded resumes
in `upload/`, generated files in `data/` (including extracted JSON, history, and
session data), SQLite databases and their transaction sidecars, logs, and tooling
caches. The safe `.env.example` template remains available to commit.

Store local resumes in `upload/` and outputs in `data/`. If you configure other
output folders, add them to `.gitignore` too. Ignore rules do not remove files
already tracked by Git; check staged changes before publishing the repository.

## Output Folders

```text
data/question/              Generated questions
data/json/                  Extracted JD + resume JSON
data/match/                 Match score analysis
data/prep/                  Interview prep
data/applications/          Cover letters and messages
data/resume_improvements/   Resume optimizer output
data/transcript/            Audio transcripts
data/voice_practice/        Voice answer evaluations
data/analysis/              Full analysis output
data/history/               SQLite history database
```

## Deprecated Compatibility Endpoints

These endpoints still exist for compatibility, but `/run` and `/voice/run` are preferred:

```text
POST /jd/questions
POST /resume/questions
POST /text/resume/questions
POST /jd-resume/questions
POST /analyze/jd-resume-match
POST /prep/interview
POST /generate/cover-letter
POST /improve/resume
POST /voice/evaluate-answer
POST /analyze/jd-resume
```

## Notes

- Resume upload expects a PDF.
- JD extraction works best on pages with visible HTML or structured `JobPosting` data.
- Voice transcription uses Groq `whisper-large-v3`.
- LLM-based features require `GROQ_API_KEY`.
- Web search helper requires `SERPER_API_KEY`.
- PDF downloads are generated without extra dependencies.
- Generated files are saved under `data/` and ignored by git.
