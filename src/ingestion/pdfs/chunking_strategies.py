
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from src.config.ingestion_config import get_config
except ImportError:
    get_config = None


class ChunkingStrategy:

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):

        if get_config:

            config = get_config()

            chunk_size = (
                chunk_size
                or config.pdf.chunk_size
            )

            chunk_overlap = (
                chunk_overlap
                or config.pdf.chunk_overlap
            )

        else:

            chunk_size = chunk_size or 600
            chunk_overlap = chunk_overlap or 100

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",
                "\n",
                ". ",
                " ",
                "",
            ],
        )

    def chunk_documents(self, documents):

        chunks = []

        for doc in documents:

            split_texts = self.splitter.split_text(
                doc["text"]
            )

            for text in split_texts:

                chunks.append(
                    {
                        "text": text,
                        "metadata": doc["metadata"],
                    }
                )

        return chunks
