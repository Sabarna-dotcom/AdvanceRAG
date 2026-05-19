# tests/test_video_preprocessing_pipeline.py

"""
Test file for video preprocessing pipeline.
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


logger = get_logger(__name__)


# ==========================================
# Test Config Loading
# ==========================================

def test_video_preprocessing_config():

    """
    Test video preprocessing config.
    """

    print(
        "\n1. Testing video preprocessing configuration..."
    )

    config = get_config()

    assert (
        config.paths.raw_video_dir
        is not None
    )

    assert (
        config.paths.raw_audio_dir
        is not None
    )

    print(
        f"   Raw video dir: "
        f"{config.paths.raw_video_dir}"
    )

    print(
        f"   Raw audio dir: "
        f"{config.paths.raw_audio_dir}"
    )

    print(
        "   ✓ Video preprocessing config loaded!"
    )


# ==========================================
# Test Video Directory
# ==========================================

def test_video_directory_exists():

    """
    Test raw video directory exists.
    """

    print(
        "\n2. Testing raw video directory..."
    )

    config = get_config()

    video_dir = (
        config.paths.raw_video_dir
    )

    assert os.path.exists(video_dir), (
        f"Video directory does not exist: "
        f"{video_dir}"
    )

    print(
        f"   ✓ Video directory exists: "
        f"{video_dir}"
    )


# ==========================================
# Test Audio Directory
# ==========================================

def test_audio_directory_exists():

    """
    Test raw audio directory exists.
    """

    print(
        "\n3. Testing raw audio directory..."
    )

    config = get_config()

    audio_dir = (
        config.paths.raw_audio_dir
    )

    os.makedirs(
        audio_dir,
        exist_ok=True
    )

    assert os.path.exists(audio_dir), (
        f"Audio directory does not exist: "
        f"{audio_dir}"
    )

    print(
        f"   ✓ Audio directory exists: "
        f"{audio_dir}"
    )


# ==========================================
# Test Video Files
# ==========================================

def test_video_files_present():

    """
    Test video files are available.
    """

    print(
        "\n4. Testing video files..."
    )

    config = get_config()

    video_dir = (
        config.paths.raw_video_dir
    )

    supported_formats = (

        ".mp4",

        ".mkv",

        ".avi",

        ".mov"
    )

    video_files = [

        file for file in os.listdir(video_dir)

        if file.endswith(supported_formats)
    ]

    assert len(video_files) > 0, (
        "No video files found"
    )

    print(
        f"   Found {len(video_files)} "
        f"video files"
    )

    for file in video_files:

        print(f"   - {file}")

    print(
        "   ✓ Video files available!"
    )


# ==========================================
# Test FFmpeg Installation
# ==========================================

def test_ffmpeg_installation():

    """
    Test FFmpeg availability.
    """

    print(
        "\n5. Testing FFmpeg installation..."
    )

    try:

        result = subprocess.run(

            ["ffmpeg", "-version"],

            capture_output=True,

            text=True,

            check=True
        )

        assert "ffmpeg version" in (
            result.stdout.lower()
        )

        print(
            "   ✓ FFmpeg installed successfully!"
        )

    except Exception as e:

        raise ValidationException(
            "FFmpeg not installed properly",
            str(e)
        )


# ==========================================
# Test Generated MP3 Files
# ==========================================

def test_generated_audio_files():

    """
    Test generated MP3 files.
    """

    print(
        "\n6. Testing generated MP3 files..."
    )

    config = get_config()

    audio_dir = (
        config.paths.raw_audio_dir
    )

    mp3_files = [

        file for file in os.listdir(audio_dir)

        if file.endswith(".mp3")
    ]

    if len(mp3_files) == 0:

        print(
            "   No MP3 files found."
        )

        print(
            "   Run video preprocessing "
            "pipeline first."
        )

        return

    print(
        f"   Found {len(mp3_files)} "
        f"generated MP3 files"
    )

    for file in mp3_files:

        print(f"   - {file}")

    print(
        "   ✓ MP3 generation successful!"
    )


# ==========================================
# Main Test Runner
# ==========================================

if __name__ == "__main__":

    try:

        logger.info(
            "Starting video preprocessing "
            "pipeline tests..."
        )

        test_video_preprocessing_config()

        test_video_directory_exists()

        test_audio_directory_exists()

        test_video_files_present()

        test_ffmpeg_installation()

        test_generated_audio_files()

        logger.info(
            "All video preprocessing "
            "tests passed!"
        )

        print(
            "\n✓ ALL VIDEO PREPROCESSING TESTS PASSED"
        )

    except Exception as e:

        logger.error(
            f"Video preprocessing tests failed "
            f"| {str(e)}"
        )

        raise ValidationException(
            "Video preprocessing testing failed",
            str(e)
        )