"""Application settings shared by the API, services, and Streamlit UI.

Edit these values before starting the application. API keys remain in .env.
Relative output paths are resolved from the working directory.
"""

from pathlib import Path

# Input and output locations.
PDF_PATH = "upload/Amit_Resume_DS.pdf"
DATA_PATH = Path("data")
TEXT_PATH = (DATA_PATH / "text").as_posix()
QUESTION = (DATA_PATH / "question").as_posix()
JSON_PATH = (DATA_PATH / "json").as_posix()
MATCH_PATH = (DATA_PATH / "match").as_posix()
PREP_PATH = (DATA_PATH / "prep").as_posix()
APPLICATIONS_PATH = (DATA_PATH / "applications").as_posix()
RESUME_IMPROVEMENTS_PATH = (DATA_PATH / "resume_improvements").as_posix()
TRANSCRIPT_PATH = (DATA_PATH / "transcript").as_posix()
VOICE_PRACTICE_PATH = (DATA_PATH / "voice_practice").as_posix()
ANALYSIS_PATH = (DATA_PATH / "analysis").as_posix()
HISTORY_PATH = (DATA_PATH / "history").as_posix()
DB_PATH = Path(HISTORY_PATH) / "interview_coach.db"

# Chat generation. Preserve separate settings for questions and structured prompts.
CHAT_MODEL = "openai/gpt-oss-20b"
QUESTION_TEMPERATURE = 1
QUESTION_MAX_COMPLETION_TOKENS = 1024
PROMPT_TEMPERATURE = 0.2
PROMPT_MAX_COMPLETION_TOKENS = 2048
CHAT_TOP_P = 1
CHAT_STOP = None

# Speech-to-text settings. Run with: python -m voice.groq_voice_text
VOICE_AUDIO_PATH = Path(__file__).resolve().parent / "voice" / "audio.m4a"
VOICE_MODEL = "whisper-large-v3"
VOICE_LANGUAGE = None  # Optional ISO language code, such as "en" or "hi".
VOICE_PROMPT = None  # Optional context to improve recognition.
VOICE_RESPONSE_FORMAT = "verbose_json"  # json, text, srt, verbose_json, or vtt.
VOICE_TEMPERATURE = 0
VOICE_TRANSLATE = False  # Translate to English instead of transcribing.

# Live microphone recording.
RECORDING_SILENCE_SECONDS = 0.6
RECORDING_SAMPLE_RATE = 16000
RECORDING_AUTO_START = False

# Upload limits (MiB) and bounded API file reads.
MAX_RESUME_UPLOAD_MB = 10
MAX_AUDIO_UPLOAD_MB = 25
MAX_RESUME_UPLOAD_BYTES = MAX_RESUME_UPLOAD_MB * 1024 * 1024
MAX_AUDIO_UPLOAD_BYTES = MAX_AUDIO_UPLOAD_MB * 1024 * 1024
UPLOAD_READ_CHUNK_BYTES = 64 * 1024

# Structured application logs are written as JSON to stderr.
LOG_LEVEL = "INFO"

# Network requests: SDK retries are bounded and scraping retries only GET requests.
GROQ_TIMEOUT_SECONDS = 45
GROQ_MAX_RETRIES = 2
HTTP_CONNECT_TIMEOUT_SECONDS = 5
HTTP_READ_TIMEOUT_SECONDS = 30
HTTP_MAX_RETRIES = 2
HTTP_RETRY_BACKOFF_SECONDS = 0.5
HTTP_RETRY_BACKOFF_MAX_SECONDS = 2

# Conservative UTF-8 size budget for the complete formatted chat prompt.
MAX_CHAT_PROMPT_BYTES = 64 * 1024
CHAT_MAX_COMPLETION_TOKENS = 8192
CHAT_COMPLETION_EXPANSIONS = 2

# SQLite and interview sessions.
SQLITE_BUSY_TIMEOUT_SECONDS = 10
MAX_SESSION_QUESTIONS = 50
MAX_SESSION_ANSWER_CHARACTERS = 20000

# Maximum generated follow-ups per session (one per planned question).
MAX_SESSION_FOLLOWUPS = 10
