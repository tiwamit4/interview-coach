"""
Scraping job descriptions from the web and extracting text from them.
"""

import json
import re
from html import unescape
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import urljoin, urlparse

import requests

from errors import EmptyJobDescriptionError, JobDescriptionFetchError
from utils.http_client import get_url

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from pdfminer.high_level import extract_text as extract_pdf_text
except ImportError:
    extract_pdf_text = None


# test_urls = [
#     "https://careers.qualcomm.com/careers/job/446718764455",
#     "https://jobs.apple.com/en-us/details/200659431-3337/software-engineer",
#     "https://jobs.apple.com/en-us/details/200635007/software-engineer-full-stack-ebusiness-services",
#     "https://jobs.apple.com/en-us/details/200642870-0836/software-engineer-apple-services-engineering",
#     "https://jobs.ashbyhq.com/Eragon/59218142-8bfd-4b49-90d9-bdc7f2dd948b",
#     "https://jobs.ashbyhq.com/unitxlabs/dd8f4858-46b6-40cf-a529-e21a94f643c3",
#     "https://jobs.ashbyhq.com/Aven/b1bdc3be-89c6-4645-8e79-8ea528f058da/",
#     "https://careers.qualcomm.com/careers/job/446718764455"
# ]


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

MIN_EXTRACTED_TEXT_CHARS = 80


class VisibleTextParser(HTMLParser):
    """
    Lightweight fallback for extracting visible text when BeautifulSoup is not
    installed in the active Python environment.
    """

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth:
            data = data.strip()
            if data:
                self.parts.append(data)

    def get_text(self):
        return " ".join(self.parts)


def clean_text(text):
    """Normalize escaped entities, markdown bullets, and repeated whitespace."""
    text = unescape(text or "")
    if re.search(r"<[a-zA-Z][^>]*>", text):
        text = html_to_text(text)

    text = text.replace("\\u0026", "&").replace("\\u0027", "'")
    text = re.sub(r"#+\s*", "", text)
    text = re.sub(r"\s*\*\s+", "\n- ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def html_to_text(html):
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)

    parser = VisibleTextParser()
    parser.feed(html)
    return parser.get_text()


def iter_json_ld_blocks(html):
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            yield script.get_text(strip=True)
        return

    pattern = re.compile(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(html):
        yield match.group(1).strip()


def find_job_posting(payload):
    if isinstance(payload, list):
        for item in payload:
            found = find_job_posting(item)
            if found:
                return found
    elif isinstance(payload, dict):
        item_type = payload.get("@type")
        if item_type == "JobPosting" or (
            isinstance(item_type, list) and "JobPosting" in item_type
        ):
            return payload
        graph = payload.get("@graph")
        if graph:
            return find_job_posting(graph)
    return None


def find_nested_key(payload, key):
    if isinstance(payload, dict):
        if key in payload:
            return payload[key]

        for value in payload.values():
            found = find_nested_key(value, key)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = find_nested_key(item, key)
            if found:
                return found

    return None


def extract_job_posting_text(html):
    """Extract structured job details exposed by many careers websites."""
    for block in iter_json_ld_blocks(html):
        try:
            payload = json.loads(unescape(block))
        except json.JSONDecodeError:
            continue

        job = find_job_posting(payload)
        if not job:
            continue

        parts = [
            job.get("title", ""),
            (
                job.get("hiringOrganization", {}).get("name", "")
                if isinstance(job.get("hiringOrganization"), dict)
                else ""
            ),
            (
                job.get("jobLocation", {}).get("address", {}).get("addressLocality", "")
                if isinstance(job.get("jobLocation"), dict)
                else ""
            ),
            job.get("description", ""),
        ]
        return clean_text("\n\n".join(part for part in parts if part))

    return ""


def iter_json_parse_payloads(html):
    pattern = re.compile(r'JSON\.parse\("((?:\\.|[^"\\])*)"\)', re.DOTALL)
    for match in pattern.finditer(html):
        try:
            json_text = json.loads(f'"{match.group(1)}"')
            yield json.loads(json_text)
        except json.JSONDecodeError:
            continue


def extract_apple_job_text(html):
    """Extract jobs.apple.com details from React Router hydration data."""
    for payload in iter_json_parse_payloads(html):
        jobs_data = find_nested_key(payload, "jobsData")
        if not isinstance(jobs_data, dict):
            continue

        location_names = []
        for location in jobs_data.get("locations", []):
            if not isinstance(location, dict):
                continue

            city = location.get("city") or location.get("name")
            state = location.get("stateProvince")
            country = location.get("countryName")
            location_name = ", ".join(part for part in [city, state, country] if part)
            if location_name:
                location_names.append(location_name)

        parts = [
            jobs_data.get("postingTitle", ""),
            "Apple",
            " | ".join(location_names),
            (
                f"Posted: {jobs_data.get('postingDateMeta', '')}"
                if jobs_data.get("postingDateMeta")
                else ""
            ),
            "Summary:",
            jobs_data.get("jobSummary", ""),
            "Description:",
            jobs_data.get("description", ""),
            "Minimum Qualifications:",
            jobs_data.get("minimumQualifications", ""),
            "Preferred Qualifications:",
            jobs_data.get("preferredQualifications", ""),
        ]
        return clean_text("\n\n".join(part for part in parts if part))

    return ""


def find_pdf_links(html, base_url):
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        links = [
            link.get("href")
            for link in soup.find_all("a", href=re.compile(r"\.pdf(?:$|\?)", re.I))
        ]
    else:
        links = re.findall(r"""href=["']([^"']+\.pdf(?:\?[^"']*)?)["']""", html, re.I)

    pdf_urls = []
    seen = set()
    for link in links:
        if not link:
            continue

        pdf_url = urljoin(base_url, link)
        if pdf_url not in seen:
            seen.add(pdf_url)
            pdf_urls.append(pdf_url)

    return pdf_urls


def scrape_job_description(url):
    """
    Scrape job description from the given URL and extract text from it.
    """
    parsed_url = urlparse(str(url))
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise JobDescriptionFetchError(
            "Enter a valid job description URL that starts with http:// or https://."
        )

    try:
        response = get_url(str(url), headers=HEADERS)
    except requests.exceptions.MissingSchema as exc:
        raise JobDescriptionFetchError(
            "Enter a valid job description URL that starts with http:// or https://."
        ) from exc
    except requests.exceptions.InvalidURL as exc:
        raise JobDescriptionFetchError(
            "The job description URL is not valid. Check it and try again."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise JobDescriptionFetchError(
            "The job description page took too long to respond. Try again later."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise JobDescriptionFetchError(
            "Could not fetch the job description page. Check the URL and your connection."
        ) from exc

    if response.status_code != 200:
        raise JobDescriptionFetchError(
            f"Could not fetch the job description page. The site returned HTTP {response.status_code}."
        )

    html = response.text

    # Prefer structured JobPosting data when the page exposes it. This is more
    # reliable for JS-heavy job sites than generic visible-text scraping.
    text = (
        extract_job_posting_text(html)
        or extract_apple_job_text(html)
        or clean_text(html_to_text(html))
    )

    # Check for PDF links and extract text from them
    for pdf_url in find_pdf_links(html, str(url)):
        if extract_pdf_text is None:
            continue

        try:
            pdf_response = get_url(pdf_url, headers=HEADERS)
        except requests.exceptions.RequestException:
            continue
        if pdf_response.status_code == 200:
            pdf_text = extract_pdf_text(BytesIO(pdf_response.content))
            text += "\n\n" + clean_text(pdf_text)

    if len(text.strip()) < MIN_EXTRACTED_TEXT_CHARS:
        raise EmptyJobDescriptionError(
            "The page loaded, but no usable job description text was found. Try a public JD URL or paste the JD text."
        )

    return text


# def main():
#     # url = test_urls[6]  # Change this to test different URLs
#     job_description_text = scrape_job_description(url)
#     print(job_description_text)


# if __name__ == "__main__":
#     main()
