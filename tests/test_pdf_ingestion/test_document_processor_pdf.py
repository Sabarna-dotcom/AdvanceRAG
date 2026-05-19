from src.ingestion.pdfs.document_processor import DocumentProcessor


def test_document_processor_pdf():

    processor = DocumentProcessor()

    chunks = processor.process_pdf(
        "data/raw/pdfs/3. Reproductive Health.pdf"
    )

    assert len(chunks) > 0

    assert "chunk_id" in chunks[0]

    assert "metadata" in chunks[0]

    print("Document Processor PDF Test Passed")
