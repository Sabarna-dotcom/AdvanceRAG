import os
from typing import List, Dict

import pdfplumber
from pypdf import PdfReader

from src.ingestion.pdfs.base_loader import BaseLoader


class PDFLoader(BaseLoader):

    def load(self, file_path: str) -> List[Dict]:

        documents = []

        reader = PdfReader(file_path)
        pdf_metadata = reader.metadata

        with pdfplumber.open(file_path) as pdf:

            for page_number, page in enumerate(pdf.pages, start=1):

                text = page.extract_text()

                if not text:
                    continue

                documents.append(
                    {
                        "text": text,
                        "page_number": page_number,
                        "metadata": {
                            "source_type": "pdf",
                            "source_name": os.path.basename(file_path),
                            "title": pdf_metadata.title if pdf_metadata else None,
                            "author": pdf_metadata.author if pdf_metadata else None,
                        },
                    }
                )

        return documents
