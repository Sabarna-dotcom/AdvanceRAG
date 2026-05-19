# src/ingestion/run_video_preprocessing_pipeline.py

"""
Convert video files into MP3 audio files.
"""

import os
import subprocess

from src.config.ingestion_config import (
    get_config
)

from src.utils.logger import (
    get_logger
)

from src.utils.exceptions import (
    ValidationException
)


# ==========================================
# Config & Logger
# ==========================================

config = get_config()

logger = get_logger(__name__)


# ==========================================
# Input / Output Directories
# ==========================================

video_dir = (
    config.paths.raw_video_dir
)

audio_dir = (
    config.paths.raw_audio_dir
)


# ==========================================
# Create Audio Directory
# ==========================================

os.makedirs(
    audio_dir,
    exist_ok=True
)


# ==========================================
# Supported Video Formats
# ==========================================

supported_formats = (

    ".mp4",

    ".mkv",

    ".avi",

    ".mov"
)


# ==========================================
# Read Video Files
# ==========================================

try:

    video_files = os.listdir(
        video_dir
    )

    logger.info(
        f"Found {len(video_files)} "
        f"video files"
    )

except Exception as e:

    logger.error(
        f"Failed reading video directory "
        f"| {str(e)}"
    )

    raise ValidationException(
        "Video directory read failed",
        str(e)
    )


# ==========================================
# Process Videos
# ==========================================

for video_file in video_files:

    try:

        if video_file.endswith(
            supported_formats
        ):

            logger.info(
                f"Processing video: "
                f"{video_file}"
            )

            video_path = os.path.join(
                video_dir,
                video_file
            )


            # ==========================================
            # File Metadata Extraction
            # ==========================================

            file_number = (
                os.path.splitext(
                    video_file
                )[0]
            )

            cleaned_name = (
                video_file
                .replace(".mp4", "")
                .replace(".mkv", "")
                .replace(".avi", "")
                .replace(".mov", "")
                .replace(" ", "_")
            )


            # ==========================================
            # Output Audio Path
            # ==========================================

            output_audio_path = os.path.join(

                audio_dir,

                f"{cleaned_name}.mp3"
            )


            # ==========================================
            # FFmpeg Conversion
            # ==========================================

            subprocess.run(

                [

                    "ffmpeg",

                    "-i",

                    video_path,

                    output_audio_path
                ],

                check=True
            )


            logger.info(
                f"Audio generated: "
                f"{output_audio_path}"
            )

    except Exception as e:

        logger.error(
            f"Failed processing video "
            f"{video_file} | {str(e)}"
        )

        continue


logger.info(
    "Video preprocessing pipeline completed"
)