"""
PDF Ingestion Pipeline Test Suite.

Tests each component of the PDF ingestion pipeline step by step:
1. ChunkingStrategy     - splits documents into chunks
2. ParentChildChunker   - creates parent-child chunk relationships
3. MetadataExtractor    - extracts topics and difficulty from text
4. PDFLoader            - loads raw PDF files from disk
5. DocumentProcessor    - full end-to-end PDF processing pipeline

Run with:

    python -m tests.test_pdf_ingestion_pipeline

or:

    python tests/test_pdf_ingestion_pipeline.py
"""

import sys
import traceback


# ==================================================
# Helpers
# ==================================================

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_result(label: str, value):
    print(f" ✓ {label}: {value}")


def print_fail(label: str, error):
    print(f" ✗ {label}: {error}")


# ==================================================
# Sample test data
# ==================================================

SAMPLE_PDF_PATH = "data/raw/pdfs/3. Reproductive Health.pdf"

LONG_TEXT_ML = "Machine learning is amazing. " * 200

LONG_TEXT_DL = "Deep learning enables neural networks. " * 500

METADATA_TEXT = """
Machine learning and neural networks are part of artificial intelligence.
"""


# ==================================================
# Test 1: ChunkingStrategy
# ==================================================

def test_chunking_strategy():
    print_header("TEST 1: ChunkingStrategy")

    try:
        from src.ingestion.pdfs.chunking_strategies import ChunkingStrategy

        chunker = ChunkingStrategy()
        print_result("Initialized", "ChunkingStrategy")

        documents = [
            {
                "text": LONG_TEXT_ML,
                "metadata": {"source_type": "pdf"},
            }
        ]

        chunks = chunker.chunk_documents(documents)

        print_result("Total chunks produced", len(chunks))

        assert len(chunks) > 1, "Expected more than 1 chunk"
        assert "text" in chunks[0], "Chunk missing 'text' key"
        assert "metadata" in chunks[0], "Chunk missing 'metadata' key"

        print_result("'text' key present", True)
        print_result("'metadata' key present", True)

        print("\n✅ ChunkingStrategy PASSED")
        return True

    except Exception as e:
        print_fail("ChunkingStrategy FAILED", e)
        traceback.print_exc()
        return False


# ==================================================
# Test 2: ParentChildChunker
# ==================================================

def test_parent_child_chunker():
    print_header("TEST 2: ParentChildChunker")

    try:
        from src.ingestion.pdfs.parent_child_chunker import ParentChildChunker

        chunker = ParentChildChunker()
        print_result("Initialized", "ParentChildChunker")

        document = {
            "text": LONG_TEXT_DL,
            "metadata": {"source_type": "pdf"},
        }

        chunks = chunker.chunk(document)

        print_result("Total chunks produced", len(chunks))

        assert len(chunks) > 0, "Expected at least 1 chunk"
        assert "parent_id" in chunks[0], "Chunk missing 'parent_id'"
        assert "parent_text" in chunks[0], "Chunk missing 'parent_text'"

        assert (
            len(chunks[0]["text"])
            < len(chunks[0]["parent_text"])
        ), "Child text should be shorter than parent"

        print_result("'parent_id' key present", True)
        print_result("'parent_text' key present", True)
        print_result("Child text shorter than parent text", True)

        print("\n✅ ParentChildChunker PASSED")
        return True

    except Exception as e:
        print_fail("ParentChildChunker FAILED", e)
        traceback.print_exc()
        return False


# ==================================================
# Test 3: MetadataExtractor
# ==================================================

def test_metadata_extractor():
    print_header("TEST 3: MetadataExtractor")

    try:
        from src.ingestion.pdfs.metadata_extractor import MetadataExtractor

        extractor = MetadataExtractor()
        print_result("Initialized", "MetadataExtractor")

        topics = extractor.extract_topics(METADATA_TEXT)
        difficulty = extractor.detect_difficulty(METADATA_TEXT)

        print_result("Topics extracted", topics)
        print_result("Difficulty detected", difficulty)

        assert isinstance(topics, list), "Topics should be a list"

        assert difficulty in (
            "beginner",
            "intermediate",
            "advanced",
        ), f"Unexpected difficulty level: {difficulty}"

        print_result("Topics type is list", True)
        print_result("Difficulty is valid level", True)

        print("\n✅ MetadataExtractor PASSED")
        return True

    except Exception as e:
        print_fail("MetadataExtractor FAILED", e)
        traceback.print_exc()
        return False


# ==================================================
# Test 4: PDFLoader
# ==================================================

def test_pdf_loader():
    print_header("TEST 4: PDFLoader")

    try:
        from src.ingestion.pdfs.pdf_loader import PDFLoader

        loader = PDFLoader()
        print_result("Initialized", "PDFLoader")

        print(f"\n -> Loading: {SAMPLE_PDF_PATH}")

        documents = loader.load(SAMPLE_PDF_PATH)

        print_result("Documents loaded", len(documents))

        assert len(documents) > 0, "No documents loaded"
        assert "text" in documents[0], "Document missing 'text' key"
        assert "metadata" in documents[0], "Document missing 'metadata' key"

        print_result("'text' key present", True)
        print_result("'metadata' key present", True)

        print_result(
            "Text preview",
            documents[0]["text"][:80].replace("\n", " "),
        )

        print("\n✅ PDFLoader PASSED")
        return True

    except Exception as e:
        print_fail("PDFLoader FAILED", e)
        traceback.print_exc()
        return False


# ==================================================
# Test 5: DocumentProcessor (full pipeline)
# ==================================================

def test_document_processor():
    print_header("TEST 5: DocumentProcessor (Full Pipeline)")

    try:
        from src.ingestion.pdfs.document_processor import DocumentProcessor

        processor = DocumentProcessor()

        print_result("Initialized", "DocumentProcessor")

        print(f"\n -> Processing: {SAMPLE_PDF_PATH}")

        chunks = processor.process_pdf(SAMPLE_PDF_PATH)

        print_result("Chunks produced", len(chunks))

        assert len(chunks) > 0, "No chunks produced"
        assert "chunk_id" in chunks[0], "Chunk missing 'chunk_id'"
        assert "metadata" in chunks[0], "Chunk missing 'metadata'"

        print_result("'chunk_id' key present", True)
        print_result("'metadata' key present", True)

        print_result(
            "Text preview",
            chunks[0].get("text", "")[:80].replace("\n", " "),
        )

        print("\n✅ DocumentProcessor PASSED")
        return True

    except Exception as e:
        print_fail("DocumentProcessor FAILED", e)
        traceback.print_exc()
        return False


# ==================================================
# Main Runner
# ==================================================

def main():

    print("\n" + "=" * 20)
    print(" PDF INGESTION PIPELINE TEST SUITE")
    print("=" * 20)

    results = {}

    results["1. ChunkingStrategy"] = test_chunking_strategy()
    results["2. ParentChildChunker"] = test_parent_child_chunker()
    results["3. MetadataExtractor"] = test_metadata_extractor()
    results["4. PDFLoader"] = test_pdf_loader()
    results["5. DocumentProcessor"] = test_document_processor()

    print_header("FINAL RESULTS")

    passed = 0
    failed = 0

    for test_name, result in results.items():

        status = "✅ PASS" if result else "❌ FAIL"

        print(f"{status} {test_name}")

        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED - PDF Ingestion pipeline is working!")
    else:
        print(f"\n⚠️ {failed} test(s) failed - check errors above")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)