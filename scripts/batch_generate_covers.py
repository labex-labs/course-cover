import json
from pathlib import Path
import click
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from generate_cover import generate_cover, logger
from rich.console import Console
from rich.logging import RichHandler
import logging

# Configure logging with rich (与 generate_cover.py 保持一致)
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        RichHandler(
            console=Console(stderr=True),
            show_time=False,
            show_path=False,
            rich_tracebacks=True,
        )
    ],
)


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


@click.command()
@click.argument("lang")
@click.option("--overwrite", is_flag=True, help="Overwrite existing covers")
def main(lang: str, overwrite: bool):
    """Generate course covers for the specified language.

    LANG is the target language code (e.g. zh, es, fr)
    """
    if lang == "en":
        logger.warning("Skipping 'en' language as it's the source language")
        return

    # Load configuration
    logger.info("Loading configuration...")
    config = load_course_config()
    if not config:
        logger.error("No course configuration found")
        return

    # Get existing covers
    existing_covers = get_existing_covers(lang)

    # Create output directory
    output_dir = Path(__file__).parent.parent / "public" / lang
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate covers for each course in config
    total_courses = len(config)
    logger.info(f"Starting to generate {total_courses} covers for {lang}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        BarColumn(complete_style="green"),
        TaskProgressColumn(),
        console=Console(stderr=True),
        expand=True,
    ) as progress:
        task = progress.add_task(
            f"[bold]Generating covers for {lang}[/bold]", total=total_courses
        )

        for course_alias, course_config in config.items():
            try:
                progress.update(
                    task, description=f"[bold]Processing {course_alias}[/bold]"
                )

                # Skip if cover already exists and not in overwrite mode
                if course_alias in existing_covers and not overwrite:
                    logger.info(f"Cover already exists for {course_alias}, skipping...")
                    progress.advance(task)
                    continue

                # Generate cover with overwrite parameter
                generate_cover(course_alias, lang, overwrite=overwrite)
                logger.info(f"Successfully generated cover for {course_alias}")
                progress.advance(task)

            except Exception as e:
                logger.error(f"Error generating cover for {course_alias}: {str(e)}")
                progress.advance(task)
                continue

    logger.info(f"Successfully completed generating covers for {lang}!")


if __name__ == "__main__":
    main()
