import os
import sys
from pathlib import Path
import json
import logging
from generate_cover import generate_cover

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_course_config() -> dict:
    """Load the course covers configuration file"""
    config_path = Path(__file__).parent.parent / "config" / "course-covers.json"
    if not config_path.exists():
        logger.error("Course configuration file not found")
        return {}

    try:
        return json.loads(config_path.read_text())
    except Exception as e:
        logger.error(f"Error loading course config: {e}")
        return {}


def get_existing_covers(lang: str) -> set:
    """Get set of existing course covers for a language"""
    covers_path = Path(__file__).parent.parent / "public" / lang
    if not covers_path.exists():
        return set()

    return {path.stem for path in covers_path.glob("*.png")}


def main():
    if len(sys.argv) != 2:
        print("Usage: python batch_generate_covers.py <lang>")
        print("Example: python batch_generate_covers.py zh")
        sys.exit(1)

    target_lang = sys.argv[1]
    if target_lang == "en":
        logger.warning("Skipping 'en' language as it's the source language")
        sys.exit(0)

    # Load configuration
    config = load_course_config()
    if not config:
        logger.error("No course configuration found")
        sys.exit(1)

    # Get existing covers
    existing_covers = get_existing_covers(target_lang)

    # Create output directory
    output_dir = Path(__file__).parent.parent / "public" / target_lang
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate covers for each course in config
    total_courses = len(config)
    for idx, (course_alias, course_config) in enumerate(config.items(), 1):
        try:
            logger.info(f"[{idx}/{total_courses}] Processing {course_alias}")

            # Skip if cover already exists
            if course_alias in existing_covers:
                logger.info(f"Cover already exists for {course_alias}, skipping...")
                continue

            # Generate cover
            generate_cover(course_alias, target_lang, overwrite=False)
            logger.info(f"Successfully generated cover for {course_alias}")

        except Exception as e:
            logger.error(f"Error generating cover for {course_alias}: {e}")
            continue

    logger.info(f"Completed generating covers for {target_lang}")


if __name__ == "__main__":
    main()
