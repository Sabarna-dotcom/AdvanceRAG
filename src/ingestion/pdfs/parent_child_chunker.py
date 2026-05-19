
import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from src.config.ingestion_config import get_config
    from src.utils.logger import get_logger
except ImportError:
    get_config = None
    get_logger = None


logger = get_logger(__name__) if get_logger else None


class ParentChildChunker:

    def __init__(self):

        if get_config:
            config = get_config()

            parent_size = config.pdf.parent_size
            child_size = config.pdf.child_size
            overlap = config.pdf.chunk_overlap

        else:
            parent_size = 1200
            child_size = 300
            overlap = 150

        self.parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=parent_size,
            chunk_overlap=overlap,
        )

        self.child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=child_size,
            chunk_overlap=50,
        )

        if logger:
            logger.info("ParentChildChunker initialized")

    def chunk(self, document):

        final_chunks = []

        parent_chunks = self.parent_splitter.split_text(
            document["text"]
        )

        for parent_text in parent_chunks:

            parent_id = str(uuid.uuid4())

            child_chunks = self.child_splitter.split_text(
                parent_text
            )

            for child_text in child_chunks:

                final_chunks.append(
                    {
                        "chunk_id": str(uuid.uuid4()),
                        "parent_id": parent_id,
                        "parent_text": parent_text,
                        "text": child_text,
                        "metadata": document["metadata"],
                    }
                )

        if logger:
            logger.info(
                f"Generated {len(final_chunks)} child chunks"
            )

        return final_chunks
