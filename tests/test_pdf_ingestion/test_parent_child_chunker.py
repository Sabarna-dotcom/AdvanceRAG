from src.ingestion.pdfs.parent_child_chunker import ParentChildChunker


def test_parent_child_chunker():

    document = {
        "text": "Deep learning enables neural networks. " * 500,
        "metadata": {
            "source_type": "pdf"
        }
    }

    chunker = ParentChildChunker()

    chunks = chunker.chunk(document)

    assert len(chunks) > 0

    assert "parent_id" in chunks[0]

    assert "parent_text" in chunks[0]

    assert len(chunks[0]["text"]) < len(chunks[0]["parent_text"])

    print("Parent Child Chunker Test Passed")
