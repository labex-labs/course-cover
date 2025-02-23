import json
from pathlib import Path
import click
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.logging import RichHandler
import logging
from generate_cover import generate_cover

# Configure logging with rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)
console = Console()


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
        console.print(
            "[yellow]Skipping 'en' language as it's the source language[/yellow]"
        )
        return

    # Load configuration
    with console.status("[bold blue]Loading configuration...") as status:
        config = load_course_config()
        if not config:
            console.print("[red]No course configuration found[/red]")
            return

    # Get existing covers
    existing_covers = get_existing_covers(lang)

    # Create output directory
    output_dir = Path(__file__).parent.parent / "public" / lang
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate covers for each course in config
    total_courses = len(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"Generating covers for {lang}", total=total_courses)

        for course_alias, course_config in config.items():
            try:
                progress.update(task, description=f"Processing {course_alias}")

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
                logger.error(f"Error generating cover for {course_alias}: {e}")
                progress.advance(task)
                continue

    console.print(
        f"\n[green]✓[/green] Completed generating covers for [bold]{lang}[/bold]"
    )


if __name__ == "__main__":
    main()
