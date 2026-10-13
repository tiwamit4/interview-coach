"""Optional browser checks: run with Playwright and its Chromium browser installed.

python -m pip install playwright
python -m playwright install chromium
python tests/browser_live_recorder.py

Recognition responses are mocked; real browser media capture and Streamlit's
iframe messaging are exercised. No speech-provider service is contacted.
"""

import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/harness":
            html = b'<html><body><script>window.messages=[];window.addEventListener("message",e=>{if(e.data.isStreamlitMessage)window.messages.push(e.data)});</script><iframe src="/index.html" allow="microphone" style="width:800px;height:400px"></iframe></body></html>'
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html)
        else:
            super().do_GET()


MOCK = """
window.SpeechRecognition = class {
  constructor() { window.recognitionInstance = this; }
  start() { if (this.onstart) this.onstart(); }
  stop() { if (this.onend) this.onend(); }
  abort() {}
};
window.webkitSpeechRecognition = undefined;
"""


def run():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        partial(Handler, directory=str(ROOT / "frontend/streamlit_ui/live_recorder")),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            launch = {
                "headless": True,
                "args": [
                    "--use-fake-ui-for-media-stream",
                    "--use-fake-device-for-media-stream",
                ],
            }
            if os.environ.get("INTERVIEW_BROWSER_EXECUTABLE"):
                launch["executable_path"] = os.environ["INTERVIEW_BROWSER_EXECUTABLE"]
            browser = playwright.chromium.launch(**launch)
            try:
                for mode in ("live", "unsupported", "recognition_error"):
                    context = browser.new_context(permissions=["microphone"])
                    context.add_init_script(
                        MOCK
                        if mode != "unsupported"
                        else "window.SpeechRecognition=undefined;window.webkitSpeechRecognition=undefined;"
                    )
                    page = context.new_page()
                    page.goto(f"http://127.0.0.1:{server.server_port}/harness")
                    frame = page.frames[1]
                    frame.wait_for_selector("#record")
                    frame.evaluate(
                        """() => window.dispatchEvent(new MessageEvent('message', {
                        source: window.parent, data: {type: 'streamlit:render', args: {
                            label: 'Record answer', language: 'en-US', sample_rate: 16000,
                            silence_seconds: 30, max_seconds: 30, start_timeout: 30,
                            energy_threshold: 0.01, max_bytes: 1024 * 1024, auto_start: false
                        }}
                    }))"""
                    )
                    frame.locator("#record").click()
                    page.wait_for_function(
                        "window.messages.some(m=>m.value?.status==='recording')"
                    )
                    if mode == "live":
                        frame.evaluate("""() => {
                          const result = [{transcript:'I built a Python API'}]; result.isFinal=false;
                          window.recognitionInstance.onresult({results:[result]});
                        }""")
                        assert (
                            frame.locator("#transcript").inner_text()
                            == "I built a Python API"
                        )
                        assert frame.locator("#record").inner_text() == "Stop recording"
                        assert not page.evaluate(
                            "window.messages.some(m=>m.value?.status==='complete')"
                        )
                        frame.evaluate("""() => {
                          const result = [{transcript:'I built and tested a Python API.'}]; result.isFinal=true;
                          window.recognitionInstance.onresult({results:[result]});
                        }""")
                        assert (
                            frame.locator("#transcript").inner_text()
                            == "I built and tested a Python API."
                        )
                    elif mode == "recognition_error":
                        frame.evaluate(
                            "window.recognitionInstance.onerror({error:'network'})"
                        )
                        assert (
                            "unavailable" in frame.locator("#transcript").inner_text()
                        )
                        assert frame.locator("#record").inner_text() == "Stop recording"
                    else:
                        assert (
                            "no live preview" in frame.locator("#status").inner_text()
                        )
                    page.wait_for_timeout(500)
                    frame.locator("#record").click()
                    page.wait_for_function(
                        "window.messages.some(m=>m.value?.status==='complete')"
                    )
                    result = page.evaluate(
                        "window.messages.find(m=>m.value?.status==='complete').value"
                    )
                    assert result["audio"]
                    assert result["filename"] == "live_recording.webm"
                    if mode == "live":
                        assert result["preview"] == "I built and tested a Python API."
                    context.close()
                    print(f"Browser recorder check passed: {mode}")
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    run()
