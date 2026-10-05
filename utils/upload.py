"""
Take pdf as input from upload folder
"""

import os

from config import PDF_PATH


def find_pdf(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError("File not found")
    if not file_path.endswith(".pdf"):
        raise ValueError("File must be a PDF")

    pdf_name = PDF_PATH.split("/")[-1]
    pdf_name = pdf_name.replace(".pdf", "")
    print(f"Found PDF: {pdf_name}")

    return file_path, pdf_name
