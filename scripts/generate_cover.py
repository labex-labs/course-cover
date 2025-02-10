import os
import sys
import random
import requests
import logging
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_course_info(course_alias: str, lang: str) -> dict:
    """Get course information from LabEx API"""
    logger.info(f"Fetching course info for {course_alias} in {lang}")
    url = f"https://labex.io/api/v2/courses/{course_alias}?lang={lang}"
    # 伪装浏览器
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["course"]


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


def generate_cover(course_alias: str, lang: str, overwrite: bool = False):
    """Generate course cover image

    Args:
        course_alias (str): Course alias
        lang (str): Language code
        overwrite (bool, optional): Whether to overwrite existing cover. Defaults to False.
    """
    logger.info(
        f"Starting cover generation for course: {course_alias}, language: {lang}"
    )

    # Create output directory and check if file exists
    output_dir = Path(__file__).parent.parent / "public" / lang
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{course_alias}.png"

    if output_path.exists() and not overwrite:
        logger.info(
            f"Cover already exists at {output_path} and overwrite=False, skipping generation"
        )
        return

    # Get course info
    course_info = get_course_info(course_alias, lang)

    # Prepare parameters
    params = {
        "course_type": get_course_type(course_info.get("type", 0)),
        "course_name": course_info["name"],
        "image_url": get_freepik_image(course_alias.replace("-", " ")),
        "bg_color": generate_random_color(),
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


if __name__ == "__main__":
    if len(sys.argv) not in [3, 4]:
        print("Usage: python generate_cover.py <course_alias> <lang> [overwrite]")
        sys.exit(1)

    course_alias = sys.argv[1]
    lang = sys.argv[2]
    overwrite = sys.argv[3].lower() == "true" if len(sys.argv) > 3 else False

    generate_cover(course_alias, lang, overwrite)
