import os

import requests
from dotenv import load_dotenv

import config
from errors import ConfigurationError

load_dotenv()

SERPER_URL = "https://google.serper.dev/search"


def search_web(query, num=5):
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ConfigurationError(
            "SERPER_API_KEY is missing. Add it to your .env file before using web search."
        )
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty.")

    payload = {
        "q": query,
        "num": num,
        "web": True,
    }
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            SERPER_URL,
            json=payload,
            headers=headers,
            timeout=(
                config.HTTP_CONNECT_TIMEOUT_SECONDS,
                config.HTTP_READ_TIMEOUT_SECONDS,
            ),
        )
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            "Web search took too long to respond. Try again later."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            "Web search failed. Check your API key, quota, and network."
        ) from exc

    return response.json().get("organic", [])


def main():
    results = search_web("Apple job description for software engineer questions", num=5)
    for result in results:
        print(f"Title: {result.get('title')}")
        print(f"Link: {result.get('link')}")
        print(f"Snippet: {result.get('snippet')}")
        print("-" * 50)


if __name__ == "__main__":
    main()
