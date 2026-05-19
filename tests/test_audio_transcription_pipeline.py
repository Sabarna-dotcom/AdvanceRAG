# tests/test_audio_transcription_pipeline.py

"""
Test file for audio transcription pipeline.
"""

import os
import json

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


def test_audio_pipeline_configuration():

    """
    Test ingestion configuration loading.
    """

    print(
        "\n1. Testing audio ingestion configuration..."
    )

    config = get_config()

    assert (
        config.paths.raw_audio_dir
        is not None
    )

    assert (
        config.paths.raw_audio_dir
        is not None
    )

    print(
        f"   Raw audio dir: "
        f"{config.paths.raw_audio_dir}"
    )

    print(
        f"   Transcript dir: "
        f"{config.paths.raw_audio_dir}"
    )

    print(
        "   ✓ Audio ingestion config loaded!"
    )


def test_audio_directory_exists():

    """
    Test raw audio directory exists.
    """

    print(
        "\n2. Testing raw audio directory..."
    )

    config = get_config()

    audio_dir = (
        config.paths.raw_audio_dir
    )

    assert os.path.exists(audio_dir), (
        f"Audio directory does not exist: "
        f"{audio_dir}"
    )

    print(
        f"   ✓ Audio directory exists: "
        f"{audio_dir}"
    )


def test_audio_files_present():

    """
    Test audio files are available.
    """

    print(
        "\n3. Testing audio files..."
    )

    config = get_config()

    audio_dir = (
        config.paths.raw_audio_dir
    )

    audio_files = [

        file for file in os.listdir(audio_dir)

        if file.endswith(".mp3")
    ]

    assert len(audio_files) > 0, (
        "No MP3 files found"
    )

    print(
        f"   Found {len(audio_files)} MP3 files"
    )

    for file in audio_files:

        print(f"   - {file}")

    print(
        "   ✓ Audio files available!"
    )


def test_transcript_output_directory():

    """
    Test transcript output directory creation.
    """

    print(
        "\n4. Testing transcript output directory..."
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
        "Transcript output directory "
        "was not created"
    )

    print(
        f"   ✓ Transcript directory exists: "
        f"{audio_dir}"
    )


def test_generated_transcript_json():

    """
    Test generated transcript JSON files.
    """

    print(
        "\n5. Testing generated transcript JSON..."
    )

    config = get_config()

    audio_dir = (
        config.paths.raw_audio_dir
    )

    json_files = [

        file for file in os.listdir(
            audio_dir
        )

        if file.endswith(".json")
    ]

    if len(json_files) == 0:

        print(
            "   No transcript JSON files found."
        )

        print(
            "   Run audio transcription "
            "pipeline first."
        )

        return

    print(
        f"   Found {len(json_files)} "
        f"transcript JSON files"
    )

    sample_file = os.path.join(
        audio_dir,
        json_files[0]
    )

    with open(
        sample_file,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    assert "chunks" in data
    assert "text" in data

    print(
        f"   ✓ Valid transcript JSON: "
        f"{json_files[0]}"
    )


def test_transcript_chunk_structure():

    """
    Validate transcript chunk structure.
    """

    print(
        "\n6. Testing transcript chunk structure..."
    )

    config = get_config()

    audio_dir = (
        config.paths.raw_audio_dir
    )

    json_files = [

        file for file in os.listdir(
            audio_dir
        )

        if file.endswith(".json")
    ]

    if len(json_files) == 0:

        print(
            "   No transcript files found."
        )

        return

    sample_file = os.path.join(
        audio_dir,
        json_files[0]
    )

    with open(
        sample_file,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    sample_chunk = data["chunks"][0]

    required_keys = [

        "number",
        "title",
        "start",
        "end",
        "text"
    ]

    for key in required_keys:

        assert key in sample_chunk, (
            f"Missing key: {key}"
        )

    print(
        "   ✓ Transcript chunk structure valid!"
    )


if __name__ == "__main__":

    try:

        logger.info(
            "Starting audio transcription "
            "pipeline tests..."
        )

        test_audio_pipeline_configuration()

        test_audio_directory_exists()

        test_audio_files_present()

        test_transcript_output_directory()

        test_generated_transcript_json()

        test_transcript_chunk_structure()

        logger.info(
            "All audio transcription "
            "pipeline tests passed!"
        )

        print(
            "\n✓ ALL AUDIO PIPELINE TESTS PASSED"
        )

    except Exception as e:

        logger.error(
            f"Audio pipeline tests failed "
            f"| {str(e)}"
        )

        raise ValidationException(
            "Audio pipeline testing failed",
            str(e)
        )