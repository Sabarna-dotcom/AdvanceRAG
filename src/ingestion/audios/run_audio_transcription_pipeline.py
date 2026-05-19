# src/ingestion/run_audio_transcription_pipeline.py

import os
import json
import whisper

from src.config.ingestion_config import get_config
from src.utils.logger import get_logger
from src.utils.exceptions import ValidationException



# ==========================================
# Config & Logger
# ==========================================

config = get_config()
logger = get_logger(__name__)


# ==========================================
# Load Whisper Model
# ==========================================

try:

    logger.info("Loading Whisper model...")
    model = whisper.load_model("large-v2")
    logger.info("Whisper model loaded successfully")

except Exception as e:

    logger.error(f"Failed loading Whisper model | {str(e)}")
    raise ValidationException("Whisper model loading failed",str(e))

# ==========================================
# Input / Output Directories
# ==========================================

audio_dir = config.paths.raw_audio_dir
transcript_dir = config.paths.raw_transcript_dir

os.makedirs(transcript_dir,exist_ok=True)


# ==========================================
# Read Audio Files
# ==========================================

audio_files = os.listdir(audio_dir)

logger.info(f"Found {len(audio_files)} audio files")

# ==========================================
# Process Audio Files
# ==========================================

for audio_file in audio_files:

    try:

        if audio_file.endswith(".mp3"):

            logger.info(f"Processing audio: {audio_file}")

            file_path = os.path.join(
                audio_dir,
                audio_file
            )


            # ==========================================
            # Extract Metadata
            # ==========================================

            if "_" in audio_file:

                number = (
                    audio_file.split("_")[0]
                )

                title = (
                    audio_file
                    .split("_")[1]
                    .replace(".mp3", "")
                )

            else:

                number = "unknown"

                title = (
                    audio_file.replace(
                        ".mp3",
                        ""
                    )
                )


            # ==========================================
            # Whisper Transcription
            # ==========================================

            result = model.transcribe(
                audio=file_path,
                language="hi",
                task="translate",
                word_timestamps=False
            )


            # ==========================================
            # Create Chunks
            # ==========================================

            chunks = []

            for segment in result["segments"]:

                chunk = {
                    "number": number,
                    "title": title,
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"]
                }

                chunks.append(chunk)


            # ==========================================
            # Final Transcript JSON
            # ==========================================

            transcript_json = {
                "source_type": "audio",
                "source_name": audio_file,
                "text": result["text"],
                "chunks": chunks
            }


            # ==========================================
            # Save JSON
            # ==========================================

            output_file = os.path.join(

                transcript_dir,
                f"{audio_file}.json"
            )

            with open(
                output_file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    transcript_json,
                    f,
                    indent=2,
                    ensure_ascii=False
                )


            logger.info(f"Transcript saved: "f"{output_file}")

    except Exception as e:

        logger.error(f"Failed processing audio "f"{audio_file} | {str(e)}")

        continue


logger.info("Audio transcription pipeline completed")