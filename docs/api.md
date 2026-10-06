# API Reference

[Back to README](../README.md)

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

## Answer-Based Session Follow-Ups

Create an interview session with follow-ups enabled:

```json
{"title": "Python practice", "questions": ["Describe a project you built."], "role_context": "Python developer", "followups_enabled": true}
```

Send this body to `POST /sessions`. The option defaults to false for API clients.
Submit answers to `POST /sessions/{session_id}/answers` using `answer_text` and
`expected_question_index`, as described in the [usage guide](usage.md#interview-sessions).
When enabled, a planned answer inserts one generated follow-up as the next question.
Answering it returns to the planned sequence. Session responses include
`current_question_is_followup` and a `followups` list containing each generated
question's index, parent index, and reason. The questions and metadata persist
across reloads. The session-wide cap is `MAX_SESSION_FOLLOWUPS` (default: 10).

Malformed or repeated generated questions return `502` without saving the answer
or advancing progress. Stale submissions return `409`. Generation and evaluation
run outside the database transaction; answer saving and question insertion are atomic.
