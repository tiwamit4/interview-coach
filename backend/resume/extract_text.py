import importlib
import subprocess
from pathlib import Path

PdfReader = None
for module_name in ("pypdf", "PyPDF2"):
    try:
        PdfReader = importlib.import_module(module_name).PdfReader
        break
    except ImportError:
        pass

if PdfReader is None:
    raise ImportError("Requires pypdf or PyPDF2 to be installed")


def read_pdf(pdf_path):
    """
    Read pdf file and extract text
    """
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text


if __name__ == "__main__":
    pdf_files = Path("upload").glob("*.pdf")
    pdf_path = next(pdf_files, None)
    if pdf_path is None:
        raise SystemExit("No PDF files found in upload/")

    text = read_pdf(pdf_path)
    print(text)
