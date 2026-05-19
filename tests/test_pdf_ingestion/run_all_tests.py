from tests.test_pdf_ingestion.test_pdf_loader import test_pdf_loader
from tests.test_pdf_ingestion.test_chunking_strategy import test_chunking
from tests.test_pdf_ingestion.test_parent_child_chunker import (
    test_parent_child_chunker,
)
from tests.test_pdf_ingestion.test_metadata_extractor import (
    test_metadata_extractor,
)
from tests.test_pdf_ingestion.test_document_processor_pdf import (
    test_document_processor_pdf,
)



if __name__ == "__main__":

    print("\nRunning Ingestion Pipeline Tests\n")

    test_chunking()
    test_parent_child_chunker()
    test_metadata_extractor()

    # Uncomment when sample files exist

    test_pdf_loader()
    test_document_processor_pdf()

    print("\nAll Basic Tests Passed Successfully\n")