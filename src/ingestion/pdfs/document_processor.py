
from src.ingestion.pdfs.pdf_loader import PDFLoader
from src.ingestion.pdfs.parent_child_chunker import ParentChildChunker
from src.ingestion.pdfs.metadata_extractor import MetadataExtractor

try:
    from src.utils.logger import get_logger
    from src.utils.exceptions import ValidationException
except ImportError:
    get_logger = None

    class ValidationException(Exception):
        pass


logger = get_logger(__name__) if get_logger else None


class DocumentProcessor:

    def __init__(self):

        self.pdf_loader = PDFLoader()
        self.chunker = ParentChildChunker()
        self.metadata_extractor = MetadataExtractor()

        if logger:
            logger.info(
                "DocumentProcessor initialized"
            )

    def process_pdf(self, file_path):

        try:

            documents = self.pdf_loader.load(
                file_path
            )

            all_chunks = []

            for document in documents:

                chunks = self.chunker.chunk(
                    document
                )

                for chunk in chunks:

                    topics = self.metadata_extractor.extract_topics(
                        chunk["text"]
                    )

                    difficulty = self.metadata_extractor.detect_difficulty(
                        chunk["text"]
                    )

                    chunk["metadata"]["topics"] = topics
                    chunk["metadata"]["difficulty"] = difficulty

                all_chunks.extend(chunks)

            if logger:
                logger.info(
                    f"Processed PDF: {file_path}"
                )

            return all_chunks

        except Exception as e:

            if logger:
                logger.error(
                    f"PDF processing failed: {file_path}"
                )

            raise ValidationException(
                f"Failed processing PDF: {file_path}"
            ) from e

