"""Optional end-to-end checks for the Bun frontend using Playwright.

Build first with `bun run build` in frontend/web. Install Playwright separately.
Uses an isolated API database and mocked generation responses; no Groq calls.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from result_fixtures import result_for_prompt
from backend.prompts.prompt import (
    COVER_LETTER_PROMPT,
    INTERVIEW_PREP_PROMPT,
    MATCH_SCORE_PROMPT,
    RESUME_IMPROVEMENT_PROMPT,
    VOICE_ANSWER_EVALUATION_PROMPT,
)

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "frontend/web"
CONFIG = {
    "max_resume_upload_bytes": 10 * 1024 * 1024,
    "max_audio_upload_bytes": 25 * 1024 * 1024,
    "recording_silence_seconds": 30,
    "recording_max_seconds": 120,
    "recording_start_timeout_seconds": 30,
    "recording_energy_threshold": 0.01,
    "live_transcription_language": "en-US",
    "max_session_questions": 50,
    "max_session_answer_characters": 20000,
}


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait(url, process):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Test server stopped unexpectedly")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError("Server startup timeout")


def run():
    bun = os.environ.get("INTERVIEW_BUN_EXECUTABLE") or shutil.which("bun")
    if not bun:
        raise RuntimeError("Bun is required")
    processes = []
    with tempfile.TemporaryDirectory(
        prefix="interview-bun-browser-", ignore_cleanup_errors=True
    ) as temporary:
        temporary = Path(temporary)
        api_port, web_port = port(), port()
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        with (temporary / "servers.log").open("w") as log:
            try:
                api_script = (
                    "from pathlib import Path; from backend import config; config.DB_PATH=Path("
                    + repr(str(temporary / "test.db"))
                    + "); from backend.utils import history; history.DB_PATH=config.DB_PATH; from backend.api import app; import uvicorn; uvicorn.run(app,host='127.0.0.1',port="
                    + str(api_port)
                    + ",log_level='warning')"
                )
                processes.append(
                    subprocess.Popen(
                        [sys.executable, "-B", "-c", api_script],
                        cwd=ROOT,
                        stdout=log,
                        stderr=log,
                        creationflags=flags,
                    )
                )
                wait(f"http://127.0.0.1:{api_port}/health", processes[-1])
                processes.append(
                    subprocess.Popen(
                        [bun, "server.ts"],
                        cwd=WEB,
                        env=os.environ
                        | {
                            "PORT": str(web_port),
                            "BACKEND_URL": f"http://127.0.0.1:{api_port}",
                        },
                        stdout=log,
                        stderr=log,
                        creationflags=flags,
                    )
                )
                origin = f"http://127.0.0.1:{web_port}"
                wait(origin, processes[-1])
                with urllib.request.urlopen(origin + "/api/health") as response:
                    assert json.load(response) == {"status": "ok"}
                with urllib.request.urlopen(origin + "/api/ui-config") as response:
                    assert "max_audio_upload_bytes" in json.load(response)
                body = json.dumps(
                    {"title": "Proxy check", "questions": ["A test question"]}
                ).encode()
                request = urllib.request.Request(
                    origin + "/api/sessions",
                    data=body,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request) as response:
                    assert response.status == 201
                    created = json.load(response)
                with urllib.request.urlopen(origin + "/api/sessions") as response:
                    assert json.load(response)["items"][0]["id"] == created["id"]
                boundary = "proxy-check-boundary"
                form = (
                    "--"
                    + boundary
                    + '\r\nContent-Disposition: form-data; name="task"\r\n\r\nunsupported\r\n--'
                    + boundary
                    + "--\r\n"
                ).encode()
                request = urllib.request.Request(
                    origin + "/api/voice/run",
                    data=form,
                    headers={
                        "Content-Type": "multipart/form-data; boundary=" + boundary
                    },
                )
                try:
                    urllib.request.urlopen(request)
                    raise AssertionError("Expected invalid-task response")
                except urllib.error.HTTPError as error:
                    assert error.code == 400
                    assert error.headers.get("X-Request-ID")
                    assert "Unsupported voice task" in json.load(error)["detail"]
                print(
                    "Production Bun server and real FastAPI GET/JSON/multipart proxy checks passed."
                )
                match = result_for_prompt(MATCH_SCORE_PROMPT)
                prep = result_for_prompt(INTERVIEW_PREP_PROMPT)
                resume = result_for_prompt(RESUME_IMPROVEMENT_PROMPT)
                application = result_for_prompt(COVER_LETTER_PROMPT)
                evaluation = result_for_prompt(
                    VOICE_ANSWER_EVALUATION_PROMPT, "My corrected answer"
                )
                stored = {
                    "id": "session-test",
                    "title": "Browser practice",
                    "questions": ["Describe your project"],
                    "role_context": "Python developer",
                    "current_question_index": 0,
                    "current_question": "Describe your project",
                    "status": "active",
                    "total_questions": 1,
                    "answered_questions": 0,
                    "average_score": None,
                    "followups_enabled": True,
                    "current_question_is_followup": False,
                    "followups": [],
                    "answers": [],
                    "created_at": "2026-10-13T10:00:00+00:00",
                    "updated_at": "2026-10-13T10:00:00+00:00",
                }
                state = {
                    "created": False,
                    "calls": [],
                    "answers": [],
                    "transcriptions": 0,
                }
                progress = {
                    "summary": {
                        "sessions": 1,
                        "completed_sessions": 1,
                        "answers": 2,
                        "average_score": 80,
                        "score_change": None,
                        "trend_window": 5,
                        "practice_score_target": 70,
                    },
                    "score_trend": [
                        {"date": "2026-10-12", "average_score": 65, "answer_count": 1},
                        {"date": "2026-10-13", "average_score": 95, "answer_count": 1},
                    ],
                    "session_scores": [
                        {
                            "session_id": "session-test",
                            "title": "Browser practice",
                            "answer_count": 2,
                            "average_score": 80,
                        }
                    ],
                    "recurring_weaknesses": [
                        {
                            "theme": "Examples and measurable outcomes",
                            "answer_count": 2,
                            "session_count": 1,
                            "examples": ["Add measurable outcomes"],
                        }
                    ],
                    "topics": [
                        {
                            "topic": "Python",
                            "answer_count": 2,
                            "average_score": 65,
                            "needs_practice": True,
                            "reasons": ["Average score below 70/100"],
                            "suggestions": ["Add an example"],
                            "practice_questions": [
                                {
                                    "question": "Describe your Python project",
                                    "score": 65,
                                }
                            ],
                        }
                    ],
                }

                def handle(route):
                    req = route.request
                    path = req.url.split("/api", 1)[1].split("?", 1)[0]
                    state["calls"].append(path)
                    if path == "/ui-config":
                        payload = CONFIG
                    elif path == "/questions":
                        payload = {
                            "questions": "1. Explain Python.\n2. How do you test an API?",
                            "output_path": None,
                        }
                    elif path == "/run":
                        payload = {
                            "match_analysis": match,
                            "interview_prep": prep,
                            "resume_improvements": resume,
                            "application_messages": application,
                            "output_path": None,
                        }
                    elif path == "/voice/run":
                        if b'name="task"\r\n\r\ntranscribe' in (
                            req.post_data_buffer or b""
                        ):
                            state["transcriptions"] += 1
                            payload = {"transcript": "Original transcript"}
                        else:
                            state["voice_body"] = req.post_data or ""
                            payload = {"evaluation": evaluation}
                    elif path == "/sessions" and req.method == "POST":
                        data = req.post_data_json
                        state["created"] = True
                        stored.update(
                            title=data["title"],
                            questions=data["questions"],
                            current_question=data["questions"][0],
                            total_questions=len(data["questions"]),
                        )
                        payload = stored
                    elif path == "/sessions":
                        payload = {"items": [stored] if state["created"] else []}
                    elif path.endswith("/answers"):
                        data = req.post_data_json
                        state["answers"].append(data)
                        index = data["expected_question_index"]
                        stored["answers"].append(
                            {
                                "question_index": index,
                                "question": stored["questions"][index],
                                "answer_text": data["answer_text"],
                                "evaluation": evaluation,
                                "created_at": "2026-10-13T10:01:00+00:00",
                            }
                        )
                        if index == 0:
                            stored["questions"].insert(
                                1, "How did you validate your project?"
                            )
                            stored["followups"] = [
                                {
                                    "question_index": 1,
                                    "parent_question_index": 0,
                                    "reason": "Explore the validation method.",
                                }
                            ]
                            stored["total_questions"] += 1
                        stored["current_question_index"] = index + 1
                        stored["answered_questions"] = index + 1
                        stored["average_score"] = 90
                        stored["status"] = (
                            "completed"
                            if index + 1 >= len(stored["questions"])
                            else "active"
                        )
                        stored["current_question"] = (
                            None
                            if stored["status"] == "completed"
                            else stored["questions"][index + 1]
                        )
                        stored["current_question_is_followup"] = index == 0
                        payload = {"session": stored}
                    elif path.startswith("/sessions/"):
                        payload = stored
                    elif path == "/progress":
                        payload = progress
                    elif path == "/history":
                        payload = {
                            "items": [
                                {
                                    "id": 1,
                                    "event_type": "match_score",
                                    "title": "Saved Python role",
                                    "created_at": "2026-10-13T10:00:00+00:00",
                                }
                            ]
                        }
                    elif path == "/history/1":
                        payload = {
                            "id": 1,
                            "title": "Saved Python role",
                            "payload": {"match_analysis": match},
                        }
                    else:
                        route.fulfill(
                            status=404, json={"detail": "Unexpected test request"}
                        )
                        return
                    route.fulfill(json=payload)

                with sync_playwright() as playwright:
                    launch = {
                        "headless": True,
                        "args": [
                            "--use-fake-ui-for-media-stream",
                            "--use-fake-device-for-media-stream",
                        ],
                    }
                    if os.environ.get("INTERVIEW_BROWSER_EXECUTABLE"):
                        launch["executable_path"] = os.environ[
                            "INTERVIEW_BROWSER_EXECUTABLE"
                        ]
                    browser = playwright.chromium.launch(**launch)
                    context = browser.new_context(
                        viewport={"width": 1440, "height": 1100},
                        permissions=["microphone"],
                    )
                    context.add_init_script(
                        "window.SpeechRecognition=class {constructor(){window.testRecognition=this}start(){}stop(){}abort(){}};window.webkitSpeechRecognition=undefined;"
                    )
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.route("**/api/**", handle)
                    page.goto(origin)
                    page.get_by_text("Backend connected", exact=True).wait_for()
                    nav = page.get_by_role("navigation")
                    cases = [
                        ("Analyze fit", "Analyze my fit"),
                        ("Interview prep", "Create my prep plan"),
                        ("Resume optimizer", "Improve my resume"),
                        ("Application writer", "Draft my application"),
                        ("Full analysis", "Generate full analysis"),
                    ]
                    for name, action in cases:
                        nav.get_by_role("button", name=name, exact=True).click()
                        form = page.locator("form:visible")
                        form.locator('input[type="url"]').fill(
                            "https://example.com/job"
                        )
                        form.locator('input[type="file"]').set_input_files(
                            {
                                "name": "resume.pdf",
                                "mimeType": "application/pdf",
                                "buffer": b"test resume",
                            }
                        )
                        form.get_by_role("button", name=action, exact=True).click()
                        page.get_by_role(
                            "heading", name="Your results", exact=True
                        ).wait_for()
                        if name == "Analyze fit":
                            page.screenshot(
                                path=str(
                                    Path(os.environ.get("TEMP", str(temporary)))
                                    / "interview-coach-bun-desktop.png"
                                ),
                                full_page=True,
                            )
                    print("All document workflows and combined results passed.")
                    nav.get_by_role("button", name="Questions", exact=True).click()
                    form = page.locator("form:visible")
                    form.locator("select").select_option(label="Pasted text")
                    form.locator("textarea").fill("My Python project")
                    form.get_by_role(
                        "button", name="Generate questions", exact=True
                    ).click()
                    page.locator(".prose:visible").filter(
                        has_text="1. Explain Python."
                    ).wait_for()
                    with page.expect_download() as downloaded:
                        page.get_by_role("button", name="JSON", exact=True).click()
                    assert downloaded.value.suggested_filename.endswith(".json")
                    nav.get_by_role("button", name="Voice practice", exact=True).click()
                    page.locator("form:visible textarea").first.fill(
                        "Describe your project"
                    )
                    page.get_by_role(
                        "button", name="Record your answer", exact=True
                    ).click()
                    page.get_by_role(
                        "button", name="Stop recording", exact=True
                    ).wait_for()
                    page.evaluate(
                        "const result=[{transcript:'I built a Python API'}]; result.isFinal=false; window.testRecognition.onresult({results:[result]})"
                    )
                    page.get_by_text("I built a Python API", exact=True).wait_for()
                    assert not page.get_by_role(
                        "button", name="Evaluate my answer", exact=True
                    ).is_enabled()
                    page.wait_for_timeout(600)
                    page.get_by_role(
                        "button", name="Stop recording", exact=True
                    ).click()
                    answer = page.get_by_label("Your answer", exact=True)
                    answer.wait_for()
                    page.wait_for_function(
                        "document.querySelector('.answer-input textarea').value === 'Original transcript'"
                    )
                    answer.fill("My corrected answer")
                    page.get_by_role(
                        "button", name="Evaluate my answer", exact=True
                    ).click()
                    page.get_by_text("Why this score?", exact=True).wait_for()
                    assert "My corrected answer" in state["voice_body"]
                    assert state["transcriptions"] == 1
                    print(
                        "Live preview, final transcript correction, and grounded voice feedback passed."
                    )
                    nav.get_by_role(
                        "button", name="Interview sessions", exact=True
                    ).click()
                    page.get_by_label("Session title", exact=True).fill(
                        "Browser practice"
                    )
                    page.get_by_label("Questions, one per line", exact=True).fill(
                        "Describe your project"
                    )
                    page.get_by_role("button", name="Start session", exact=True).click()
                    page.get_by_role(
                        "heading", name="Question 1 of 1", exact=True
                    ).wait_for()
                    page.get_by_label("Your answer", exact=True).fill("First answer")
                    page.get_by_role("button", name="Submit answer", exact=True).click()
                    page.get_by_text(
                        "How did you validate your project?", exact=True
                    ).wait_for()
                    page.get_by_label("Your answer", exact=True).fill(
                        "Follow-up answer"
                    )
                    page.get_by_role("button", name="Submit answer", exact=True).click()
                    page.get_by_role(
                        "heading", name="Practice complete", exact=True
                    ).wait_for()
                    assert [
                        item["expected_question_index"] for item in state["answers"]
                    ] == [0, 1]
                    nav.get_by_role("button", name="Progress", exact=True).click()
                    page.get_by_role(
                        "heading", name="Your score trend", exact=True
                    ).wait_for()
                    page.get_by_role("cell", name="Python", exact=True).wait_for()
                    nav.get_by_role("button", name="History", exact=True).click()
                    page.get_by_role(
                        "button", name="Saved Python role", exact=False
                    ).click()
                    page.get_by_role(
                        "heading", name="Your results", exact=True
                    ).wait_for()
                    print(
                        "Sessions with follow-up progression, progress charts, and history passed."
                    )
                    page.set_viewport_size({"width": 390, "height": 844})
                    page.get_by_role(
                        "button", name="Open navigation", exact=True
                    ).click()
                    nav.get_by_role("button", name="Analyze fit", exact=True).click()
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= innerWidth"
                    )
                    page.screenshot(
                        path=str(
                            Path(os.environ.get("TEMP", str(temporary)))
                            / "interview-coach-bun-mobile.png"
                        ),
                        full_page=True,
                    )
                    assert not errors, errors
                    context.close()
                    browser.close()
                    print(
                        "Mobile navigation, layout overflow, and browser-console checks passed."
                    )
            finally:
                for process in reversed(processes):
                    if process.poll() is not None:
                        continue
                    if os.name == "nt":
                        subprocess.run(
                            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                    else:
                        process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()


if __name__ == "__main__":
    run()
