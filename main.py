from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from config import PDF_PATH, QUESTION, TEXT_PATH
from jd.extract_text import scrape_job_description
from prompts.prompt import JD_PROMPT, QUESTION_PROMPT
from resume.extract_text import read_pdf
from services.files import write_text_file
from utils.groq_service import groq_model_call
from utils.logging_utils import log_error
from utils.upload import find_pdf

load_dotenv()


def safe_filename_from_url(url):
    parsed_url = urlparse(url)
    path_parts = [part for part in parsed_url.path.split("/") if part]
    slug = "_".join(path_parts[-2:]) if len(path_parts) >= 2 else parsed_url.netloc
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in slug)


def main():
    print("Looking for PDF in upload folder...")
    pdf_path, pdf_name = find_pdf(PDF_PATH)

    # Extract text from the PDF
    text = read_pdf(pdf_path)
    print(f"Extracted text from {pdf_path}")

    # Save the extracted text to a file
    print(f"Created text file")
    file_path = write_text_file(TEXT_PATH, f"{pdf_name}.txt", text)
    print(f"Saving extracted text to {file_path}...")

    # Call the Groq model to generate questions based on the extracted text
    print("Calling Groq model...")
    response = groq_model_call(text, QUESTION_PROMPT)

    # Save the generated questions to a file
    question_file_path = write_text_file(
        QUESTION, f"{pdf_name}_questions.txt", response
    )

    print(f"Generated questions: {response}")
    print(response)

    url = "https://careers.qualcomm.com/careers/job/446718764455"
    print(f"Scraping job description from {url}...")
    jd_details = scrape_job_description(url)
    print(
        f"Extracted job description: {jd_details[:100]}..."
    )  # Print the first 100 characters of the job description
    print("Calling Groq model for job description...")
    jd_response = groq_model_call(jd_details, JD_PROMPT)

    Path(QUESTION).mkdir(parents=True, exist_ok=True)
    jd_question_file_path = write_text_file(
        QUESTION, f"jd_questions_{safe_filename_from_url(url)}.txt", jd_response
    )
    print(f"Generated questions for job description: {jd_response}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log_error(exc, event="cli_operation_failed", operation="main")
        raise
