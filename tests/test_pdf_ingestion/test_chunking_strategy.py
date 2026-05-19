from src.ingestion.pdfs.chunking_strategies import ChunkingStrategy


def test_chunking():

    documents = [
        {
            "text": "Machine learning is amazing. " * 200,
            "metadata": {
                "source_type": "pdf"
            }
        }
    ]

    chunker = ChunkingStrategy()

    chunks = chunker.chunk_documents(documents)

    assert len(chunks) > 1

    assert "text" in chunks[0]

    assert "metadata" in chunks[0]

    print("Chunking Strategy Test Passed")
