from src.ingestion.pdfs.metadata_extractor import MetadataExtractor


def test_metadata_extractor():

    extractor = MetadataExtractor()

    text = """
    Machine learning and neural networks are part of artificial intelligence.
    """

    topics = extractor.extract_topics(text)

    difficulty = extractor.detect_difficulty(text)

    assert isinstance(topics, list)

    assert difficulty in [
        "beginner",
        "intermediate",
        "advanced"
    ]

    print("Metadata Extractor Test Passed")
