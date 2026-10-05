"""FastAPI application entry point. Run with uvicorn api:app."""

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api_backend.middleware import RequestLoggingMiddleware
from api_backend.routes import (
    analysis,
    extraction,
    health,
    history,
    questions,
    voice,
    workflows,
    sessions,
)

load_dotenv()

app = FastAPI(title="Interview Coach API")
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    headers = {}
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        headers["X-Request-ID"] = request_id
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong. Please try again."},
        headers=headers,
    )


app.include_router(health.router)
app.include_router(questions.router)
app.include_router(workflows.router)
app.include_router(voice.router)
app.include_router(extraction.router)
app.include_router(analysis.router)
app.include_router(history.router)
app.include_router(sessions.router)
