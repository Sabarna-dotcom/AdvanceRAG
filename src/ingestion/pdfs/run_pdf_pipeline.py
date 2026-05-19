import os
import json

from .document_processor import DocumentProcessor
from src.config.settings import get_settings
from src.config.ingestion_config import get_config
from src.utils.logger import get_logger
from src.utils.exceptions import ValidationException



# ==========================================
# Config & Logger
# ==========================================

settings = get_settings()
config = get_config()
logger = get_logger(__name__)


# ==========================================
# Processor
# ==========================================

processor = DocumentProcessor()

all_chunks = []
all_parent_chunks = []
all_child_chunks = []
all_metadata = []

# ==========================================
# Input Directory
# ==========================================

pdf_dir = config.paths.raw_pdf_dir

# ==========================================
# Process PDFs
# ==========================================

try:

    logger.info(
        "Starting PDF ingestion pipeline"
    )

    for file_name in os.listdir(pdf_dir):

        if file_name.endswith(".pdf"):

            file_path = os.path.join(pdf_dir,file_name)

            logger.info(f"Processing PDF: {file_name}")

            try:

                chunks = processor.process_pdf(file_path)

                logger.info(f"Generated {len(chunks)} chunks")

                for chunk in chunks:

                    # Full chunks
                    all_chunks.append(chunk)

                    # Parent chunks
                    parent_chunk = {
                        "parent_id": chunk["parent_id"],
                        "parent_text": chunk["parent_text"]
                    }

                    if (parent_chunk not in all_parent_chunks):

                        all_parent_chunks.append(parent_chunk)

                    # Child chunks
                    child_chunk = {
                        "chunk_id": chunk["chunk_id"],
                        "parent_id": chunk["parent_id"],
                        "text": chunk["text"]
                    }

                    all_child_chunks.append(child_chunk)

                    # Metadata
                    metadata_item = {
                        "chunk_id": chunk["chunk_id"],
                        "metadata": chunk["metadata"]
                    }

                    all_metadata.append(metadata_item)

            except Exception as e:

                logger.error(f"Failed processing PDF: "f"{file_name} | {str(e)}")

                continue


    # ==========================================
    # Output Directories
    # ==========================================

    processed_pdf_dir = config.paths.processed_pdf_dir


    chunks_dir = f"{processed_pdf_dir}/chunks"
    parent_chunks_dir = f"{processed_pdf_dir}/parent_chunks"
    child_chunks_dir = f"{processed_pdf_dir}/child_chunks"
    metadata_dir = f"{processed_pdf_dir}/metadata"


    # ==========================================
    # Create Directories
    # ==========================================

    os.makedirs(chunks_dir,exist_ok=True)
    os.makedirs(parent_chunks_dir,exist_ok=True)
    os.makedirs(child_chunks_dir,exist_ok=True)
    os.makedirs(metadata_dir,exist_ok=True)


    # ==========================================
    # Save Full Chunks
    # ==========================================

    with open(f"{chunks_dir}/pdf_chunks.json","w",encoding="utf-8") as f:

        json.dump(
            all_chunks,
            f,
            indent=2,
            ensure_ascii=False
        )


    # ==========================================
    # Save Parent Chunks
    # ==========================================

    with open(f"{parent_chunks_dir}/pdf_parent_chunks.json","w",encoding="utf-8") as f:

        json.dump(
            all_parent_chunks,
            f,
            indent=2,
            ensure_ascii=False
        )


    # ==========================================
    # Save Child Chunks
    # ==========================================

    with open(f"{child_chunks_dir}/pdf_child_chunks.json","w",encoding="utf-8") as f:

        json.dump(
            all_child_chunks,
            f,
            indent=2,
            ensure_ascii=False
        )


    # ==========================================
    # Save Metadata
    # ==========================================

    with open(f"{metadata_dir}/pdf_metadata.json","w",encoding="utf-8") as f:

        json.dump(
            all_metadata,
            f,
            indent=2,
            ensure_ascii=False
        )


    logger.info(
        "PDF pipeline completed successfully"
    )

    logger.info(
        f"Total Chunks: {len(all_chunks)}"
    )

    logger.info(
        f"Total Parent Chunks: "
        f"{len(all_parent_chunks)}"
    )

    logger.info(
        f"Total Child Chunks: "
        f"{len(all_child_chunks)}"
    )

    logger.info(
        f"Total Metadata Entries: "
        f"{len(all_metadata)}"
    )


except Exception as e:

    logger.error(
        f"PDF ingestion pipeline failed "
        f"| {str(e)}"
    )

    raise ValidationException(
        "PDF ingestion pipeline failed",
        str(e)
    )