import os
import sys
import random
import requests
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from datetime import datetime
import click
from rich.console import Console
from rich.logging import RichHandler
import logging

# Configure rich console
console = Console()

# Configure logging with rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        RichHandler(
            console=Console(stderr=True),  # 将日志输出重定向到 stderr
            show_time=False,  # 不显示时间
            show_path=False,  # 不显示文件路径
            rich_tracebacks=True,
        )
    ],
)
logger = logging.getLogger("rich")


def get_course_info(course_alias: str, lang: str) -> dict:
    """Get course information from LabEx API"""
    logger.info(f"Fetching course info for {course_alias} in {lang}")
    url = f"https://labex.io/api/v2/courses/{course_alias}?lang={lang}"
    try:
        logger.info(f"Fetching: {url}")
        response = requests.get(url)
        response.raise_for_status()
        course_info = response.json()["course"]

        # Check if requested language is available
        available_langs = course_info.get("langs", [])
        if lang not in available_langs:
            logger.warning(
                f"Course {course_alias} is not available in {lang}. "
                f"Available languages: {', '.join(available_langs)}"
            )
            return None

        logger.info(f"Course name: {course_info['name']}")
        return course_info
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Course {course_alias} not found")
            return None
        raise
    except Exception as e:
        logger.error(f"Error fetching course info: {e}")
        return None


def get_course_type(type_id: int) -> str:
    """Convert course type ID to type name"""
    type_map = {0: "normal", 1: "alibaba", 3: "project"}
    return type_map.get(type_id, "normal")


def get_freepik_image(term: str) -> str:
    """Get a random Freepik icon URL with retry mechanism"""
    logger.info(f"Searching Freepik image for term: {term}")
    api_key = os.environ.get("FREEPIK_API_KEY")
    if not api_key:
        logger.error("FREEPIK_API_KEY environment variable is not set")
        raise ValueError("FREEPIK_API_KEY environment variable is not set")

    params = {
        "term": term,
        "filters[shape]": "lineal-color",
        "thumbnail_size": "512",
        "page": 1,
        "limit": 20,
    }

    headers = {
        "Accept-Language": "en-gb",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-freepik-api-key": api_key,
    }

    max_retries = 3
    retry_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            response = requests.get(
                "https://api.freepik.com/v1/icons", params=params, headers=headers
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("data"):
                logger.warning("No Freepik data found for term: %s", term)
                return "https://cdn.jsdelivr.net/gh/labex-labs/course-cover/default.png"

            lineal_color = [
                item
                for item in data["data"]
                if "lineal color" in item["style"]["name"].lower()
            ]
            image_list = lineal_color if lineal_color else data["data"]
            random_image = random.choice(image_list)

            logger.info(
                f"Successfully fetched Freepik image: {random_image['thumbnails'][0]['url']}"
            )
            return random_image["thumbnails"][0]["url"]

        except Exception as e:
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed for term: {term}",
                exc_info=e,
            )
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"All retries failed for term: {term}", exc_info=e)
                return "https://cdn.jsdelivr.net/gh/labex-labs/course-cover/labex-icon-blue.png"


def generate_random_color() -> str:
    """Generate a random light color"""

    def rand():
        return random.randint(180, 255)

    return f"{rand():02x}{rand():02x}{rand():02x}"


def download_image(url: str, course_alias: str) -> str:
    """Download image from URL and save to assets directory"""
    assets_dir = Path(__file__).parent.parent / "assets" / "icons"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename from course alias and original extension
    ext = url.split(".")[-1].lower()
    if ext not in ["png", "jpg", "jpeg"]:
        ext = "png"
    filename = f"{course_alias}.{ext}"
    image_path = assets_dir / filename

    # Download if not exists
    if not image_path.exists():
        try:
            logger.info(f"Downloading image from {url}")
            response = requests.get(url, stream=True)
            response.raise_for_status()

            with image_path.open("wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Image saved to {image_path}")
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return url  # Fallback to original URL if download fails

    # Return relative path for use in HTML
    return f"./assets/icons/{filename}"


def load_course_config(course_alias: str) -> dict:
    """Load course configuration from JSON file"""
    config_path = Path(__file__).parent.parent / "config" / "course-covers.json"
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("{}")
        return None

    try:
        config = json.loads(config_path.read_text())
        return config.get(course_alias)
    except Exception as e:
        logger.error(f"Error loading course config: {e}")
        return None


def save_course_config(course_alias: str, config: dict):
    """Save course configuration to JSON file"""
    config_path = Path(__file__).parent.parent / "config" / "course-covers.json"
    try:
        if config_path.exists():
            existing_config = json.loads(config_path.read_text())
        else:
            existing_config = {}

        existing_config[course_alias] = config
        config_path.write_text(json.dumps(existing_config, indent=2, sort_keys=True))
    except Exception as e:
        logger.error(f"Error saving course config: {e}")


def generate_cover(course_alias: str, lang: str, overwrite: bool = False):
    """Generate course cover image

    Args:
        course_alias (str): Course alias
        lang (str): Language code
        overwrite (bool, optional): Whether to overwrite existing cover. Defaults to False.

    Returns:
        bool: True if generation was successful or skipped, False if course does not exist
    """
    logger.info(
        f"Starting cover generation for course: {course_alias}, language: {lang}"
    )

    # Try to get course info from the attribute first (batch mode)
    if (
        hasattr(generate_cover, "course_info")
        and generate_cover.course_info is not None
    ):
        course_info = generate_cover.course_info
        # Clear the course_info after using it to avoid affecting next call
        generate_cover.course_info = None
    else:
        # Fallback to fetching course info individually (single mode)
        course_info = get_course_info(course_alias, lang)
        if course_info is None:
            logger.info(
                f"Skipping cover generation as course {course_alias} does not exist or not available in {lang}"
            )
            return False

    # Create output directory and check if file exists
    output_dir = Path(__file__).parent.parent / "public" / lang
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{course_alias}.png"

    if output_path.exists() and not overwrite:
        logger.info(
            f"Cover already exists at {output_path} and overwrite=False, skipping generation"
        )
        return True  # Return True for successful generation

    # Load or generate course configuration
    course_config = load_course_config(course_alias)
    if course_config is None:
        # Get new image from Freepik
        freepik_url = get_freepik_image(course_alias.replace("-", " "))
        # Download image and get local path
        local_image_path = download_image(freepik_url, course_alias)

        # Generate new configuration
        course_config = {
            "image_url": local_image_path,
            "bg_color": generate_random_color(),
            "created_at": datetime.now().isoformat(),
        }
        # 只有从 Freepik 获取的图片才添加 remote_url
        if not freepik_url.startswith("./"):
            course_config["remote_url"] = freepik_url

        # Save configuration for future use
        save_course_config(course_alias, course_config)
        logger.info(f"Generated new course config for {course_alias}")
    else:
        logger.info(f"Using existing course config for {course_alias}")

    # Prepare parameters
    params = {
        "course_type": get_course_type(course_info.get("type", 0)),
        "course_name": course_info["name"].replace("`", ""),
        "image_url": course_config["image_url"],
        "bg_color": course_config["bg_color"],
        "lang": lang,
    }
    logger.debug(f"Generated parameters: {params}")

    # Read template HTML
    template_path = Path(__file__).parent.parent / "preview.html"
    logger.info(f"Using template at: {template_path}")

    # Generate screenshot using Playwright
    with sync_playwright() as p:
        logger.info("Launching browser")
        browser = p.chromium.launch()
        # 设置更大的视口以确保内容完全渲染
        page = browser.new_page(viewport={"width": 1600, "height": 900})

        # Construct URL with parameters
        params_str = "&".join(f"{k}={v}" for k, v in params.items())
        file_url = f"file://{template_path}?{params_str}"

        # Navigate and screenshot
        logger.info(f"Taking screenshot: {file_url}")
        page.goto(file_url)
        page.wait_for_load_state("networkidle")

        # 使用 clip 选项精确截取指定区域
        page.screenshot(
            path=str(output_path), clip={"x": 0, "y": 0, "width": 1400, "height": 720}
        )
        logger.info(f"Screenshot saved to: {output_path}")

        browser.close()
        logger.info("Browser closed")

    return True  # Return True for successful generation


@click.command()
@click.argument("course_alias")
@click.argument("lang")
@click.option(
    "--overwrite/--no-overwrite",
    default=False,
    help="Overwrite existing cover if it exists",
)
def main(course_alias: str, lang: str, overwrite: bool = False):
    """
    Generate course cover image.

    COURSE_ALIAS: Course alias (e.g. html-for-beginners)
    LANG: Course language code (e.g. en, zh)
    """
    try:
        logger.info(f"Generating cover for {course_alias} ({lang})...")
        generate_cover(course_alias, lang, overwrite)
        logger.info(f"Successfully generated cover for {course_alias}")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
