from src.ingestion.pdfs.pdf_loader import PDFLoader


def test_pdf_loader():

    loader = PDFLoader()

    documents = loader.load(
        "data/raw/pdfs/3. Reproductive Health.pdf"
    )

    assert len(documents) > 0

    assert "text" in documents[0]

    assert "metadata" in documents[0]

    print("PDF Loader Test Passed")
