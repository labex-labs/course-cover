import os
from pathlib import Path
import json
from PIL import Image
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def extract_dominant_color(image_path: Path) -> str:
    """Extract the dominant background color from the bottom-left corner of the image"""
    with Image.open(image_path) as img:
        # Convert image to RGB mode if it's not
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Get average color from a 10x10 pixel area in the bottom-left corner
        left = 0
        bottom = img.height - 10
        area = img.crop((left, bottom, left + 10, bottom + 10))

        # Calculate average color
        avg_color_per_row = [pixel for pixel in area.getdata()]
        avg_color = tuple(
            sum(color) // len(avg_color_per_row) for color in zip(*avg_color_per_row)
        )

        # Convert RGB to hex
        return f"{avg_color[0]:02x}{avg_color[1]:02x}{avg_color[2]:02x}"


def extract_icon(image_path: Path, output_path: Path) -> bool:
    """Extract 512x512 icon from the right side of the cover image"""
    try:
        with Image.open(image_path) as img:
            # Expected dimensions for course cover
            if img.size != (1400, 720):
                logger.warning(
                    f"Unexpected image dimensions for {image_path}: {img.size}"
                )
                return False

            # Calculate coordinates for the icon (right side of the image)
            # The icon should be centered vertically
            start_y = 113
            start_x = 808

            # Crop the icon
            icon = img.crop((start_x, start_y, start_x + 512, start_y + 512))

            # Save the icon
            output_path.parent.mkdir(parents=True, exist_ok=True)
            icon.save(output_path, "PNG")
            logger.info(f"Extracted icon saved to {output_path}")
            return True
    except Exception as e:
        logger.error(f"Error extracting icon from {image_path}: {e}")
        return False


def update_config(course_alias: str, icon_path: str, bg_color: str):
    """Update the course covers configuration file"""
    config_path = Path(__file__).parent.parent / "config" / "course-covers.json"

    # Load existing config or create new one
    if config_path.exists():
        config = json.loads(config_path.read_text())
    else:
        config = {}

    # Update config for this course
    config[course_alias] = {
        "image_url": icon_path,
        "bg_color": bg_color,
        "created_at": datetime.now().isoformat(),
    }

    # Save updated config
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True))
    logger.info(f"Updated config for {course_alias}")


def main():
    # Define paths
    base_path = Path(__file__).parent.parent
    covers_path = base_path / "public" / "en"
    icons_path = base_path / "assets" / "icons"

    # Create icons directory if it doesn't exist
    icons_path.mkdir(parents=True, exist_ok=True)

    # Process each cover image
    for cover_path in covers_path.glob("*.png"):
        course_alias = cover_path.stem
        icon_path = icons_path / f"{course_alias}.png"

        logger.info(f"Processing {course_alias}")

        # Extract icon
        if extract_icon(cover_path, icon_path):
            # Extract background color
            bg_color = extract_dominant_color(cover_path)

            # Update configuration
            relative_icon_path = f"./assets/icons/{course_alias}.png"
            update_config(course_alias, relative_icon_path, bg_color)
        else:
            logger.warning(f"Skipped {course_alias} due to extraction error")


if __name__ == "__main__":
    main()
