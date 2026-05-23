"""
Unit tests for PDF ingestion pipeline.
"""

import pytest
from unittest.mock import (
    patch,
    MagicMock,
    mock_open
)

from src.utils.exceptions import (
    LLMException,
    VectorStoreException
)

from src.ingestion.pdfs.ingest_pdfs import (
    load_pdf_chunks,
    main
)


# ==========================================
# Test: load_pdf_chunks success
# ==========================================

@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='[{"text": "chunk1"}, {"text": "chunk2"}]'
)
def test_load_pdf_chunks_success(
    mock_file
):

    result = load_pdf_chunks()

    assert len(result) == 2

    assert result[0]["text"] == "chunk1"

    assert result[1]["text"] == "chunk2"


# ==========================================
# Test: load_pdf_chunks failure
# ==========================================

@patch("builtins.open")
def test_load_pdf_chunks_failure(
    mock_open_file
):

    mock_open_file.side_effect = Exception(
        "File not found"
    )

    with pytest.raises(
        LLMException
    ):

        load_pdf_chunks()


# ==========================================
# Test: main success
# ==========================================

@patch(
    "src.ingestion.pdfs.run_pdf_ingestion_pipeline.load_pdf_chunks"
)
@patch(
    "src.ingestion.pdfs.run_pdf_ingestion_pipeline.PDFBatchEmbedder"
)
@patch(
    "src.ingestion.pdfs.run_pdf_ingestion_pipeline.PDFIndexingManager"
)
def test_main_success(
    mock_indexer_class,
    mock_embedder_class,
    mock_load_chunks
):

    mock_chunks = [
        {"text": "pdf text"}
    ]

    mock_embeddings = [
        {
            "text": "pdf text",
            "embedding": [0.1, 0.2]
        }
    ]

    mock_load_chunks.return_value = (
        mock_chunks
    )

    mock_embedder = MagicMock()

    mock_embedder.generate_embeddings.return_value = (
        mock_embeddings
    )

    mock_embedder_class.return_value = (
        mock_embedder
    )

    mock_indexer = MagicMock()

    mock_indexer_class.return_value = (
        mock_indexer
    )

    main()

    mock_load_chunks.assert_called_once()

    mock_embedder.generate_embeddings.assert_called_once_with(
        mock_chunks
    )

    mock_indexer.index_chunks.assert_called_once_with(
        mock_embeddings
    )


# ==========================================
# Test: main handles LLMException
# ==========================================

@patch(
    "src.ingestion.pdfs.run_pdf_ingestion_pipeline.load_pdf_chunks"
)
def test_main_llm_exception(
    mock_load_chunks
):

    mock_load_chunks.side_effect = (
        LLMException(
            message="LLM Error",
            details="Embedding failed"
        )
    )

    with pytest.raises(
        LLMException
    ):

        main()


# ==========================================
# Test: main handles VectorStoreException
# ==========================================

@patch(
    "src.ingestion.pdfs.run_pdf_ingestion_pipeline.PDFIndexingManager"
)
@patch(
    "src.ingestion.pdfs.run_pdf_ingestion_pipeline.PDFBatchEmbedder"
)
@patch(
    "src.ingestion.pdfs.run_pdf_ingestion_pipeline.load_pdf_chunks"
)
def test_main_vectorstore_exception(
    mock_load_chunks,
    mock_embedder_class,
    mock_indexer_class
):

    mock_load_chunks.return_value = [
        {"text": "sample"}
    ]

    mock_embedder = MagicMock()

    mock_embedder.generate_embeddings.return_value = [
        {
            "text": "sample",
            "embedding": [0.1]
        }
    ]

    mock_embedder_class.return_value = (
        mock_embedder
    )

    mock_indexer = MagicMock()

    mock_indexer.index_chunks.side_effect = (
        VectorStoreException(
            message="Qdrant Error",
            details="Insert failed"
        )
    )

    mock_indexer_class.return_value = (
        mock_indexer
    )

    with pytest.raises(
        VectorStoreException
    ):

        main()


# ==========================================
# Test: main unexpected exception
# ==========================================

@patch(
    "src.ingestion.pdfs.run_pdf_ingestion_pipeline.load_pdf_chunks"
)
def test_main_unexpected_exception(
    mock_load_chunks
):

    mock_load_chunks.side_effect = Exception(
        "Unexpected error"
    )

    with pytest.raises(
        Exception
    ):

        main()