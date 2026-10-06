# Configuration and Storage

[Back to README](../README.md)

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
