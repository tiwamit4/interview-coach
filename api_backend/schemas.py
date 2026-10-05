"""Request models for JSON API endpoints."""

from pydantic import BaseModel, HttpUrl


class JobDescriptionRequest(BaseModel):
    url: HttpUrl
    save_output: bool = True


class TextRequest(BaseModel):
    text: str
    save_output: bool = False
    output_name: str | None = None
