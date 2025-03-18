import click
import requests
from rich.console import Console
from rich.logging import RichHandler
import logging
from generate_cover import generate_cover
import multiprocessing
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from functools import partial
import time

# Configure logging with rich
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
logger = logging.getLogger("rich")


def fetch_courses(lang: str) -> tuple[list, dict]:
    """Fetch all courses from LabEx API"""
    url = f"https://labex.io/api/v2/courses?lang={lang}"
    try:
        logger.info(f"Fetching courses from: {url}")
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Extract course information
        courses = data.get("courses", [])
        course_aliases = []
        course_info_map = {}

        for course in courses:
            alias = course["alias"]
            course_aliases.append(alias)
            # Store relevant course information
            course_info_map[alias] = {
                "name": course["name"],
                "type": course.get("type", 0),
                "langs": [lang],  # We know it's available in current language
            }

        logger.info(f"Found {len(course_aliases)} courses")
        return course_aliases, course_info_map
    except Exception as e:
        logger.error(f"Error fetching courses: {e}")
        return [], {}


def process_course(course_data: tuple) -> tuple:
    """Process a single course cover generation"""
    course_alias, course_info, lang, overwrite = course_data
    try:
        # Override the course info in generate_cover's global space
        # This avoids the need to fetch course info again
        generate_cover.course_info = course_info
        result = generate_cover(course_alias, lang, overwrite)
        return course_alias, result, None
    except Exception as e:
        return course_alias, False, str(e)


def process_batch(
    course_aliases: list,
    course_info_map: dict,
    lang: str,
    overwrite: bool,
    workers: int,
    description: str,
    max_retries: int = 3,
) -> tuple:
    """Process a batch of courses with retries"""
    remaining_courses = [
        (alias, course_info_map[alias], lang, overwrite) for alias in course_aliases
    ]
    retry_count = 0
    all_successful = []
    all_failed = []

    while remaining_courses and retry_count < max_retries:
        if retry_count > 0:
            logger.info(
                f"\nRetry attempt {retry_count} for {len(remaining_courses)} failed courses..."
            )
            # Add a small delay between retries
            time.sleep(2)

        # Create a process pool
        pool = multiprocessing.Pool(processes=workers)

        current_failed = []
        successful = 0
        failed = 0

        # Setup progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            BarColumn(complete_style="green"),
            TaskProgressColumn(),
            console=Console(stderr=True),
            expand=True,
        ) as progress:
            task = progress.add_task(
                f"[bold]{description}[/bold]", total=len(remaining_courses)
            )

            for course_alias, result, error in pool.imap_unordered(
                process_course, remaining_courses
            ):
                if result:
                    successful += 1
                    all_successful.append(course_alias)
                    progress.update(
                        task,
                        description=f"[green]Successfully processed {course_alias}[/green]",
                    )
                else:
                    failed += 1
                    current_failed.append((course_alias, error))
                    progress.update(
                        task, description=f"[red]Failed processing {course_alias}[/red]"
                    )
                progress.advance(task)

        # Close and join the pool
        pool.close()
        pool.join()

        # Update remaining courses for next retry
        remaining_courses = [
            (alias, course_info_map[alias], lang, overwrite)
            for alias, _ in current_failed
        ]
        all_failed = current_failed
        retry_count += 1

        # Log results for this attempt
        if retry_count > 0:
            logger.info(f"\nRetry {retry_count} results:")
        logger.info(f"Successfully generated: {successful}")
        logger.info(f"Failed: {failed}")

        # If all courses were successful, break the loop
        if not remaining_courses:
            break

    return all_successful, all_failed


@click.command()
@click.argument("lang")
@click.option("--overwrite", is_flag=True, help="Overwrite existing covers")
@click.option(
    "--workers",
    default=20,
    help="Number of worker processes",
    type=int,
)
@click.option(
    "--max-retries",
    default=3,
    help="Maximum number of retry attempts for failed courses",
    type=int,
)
def main(lang: str, overwrite: bool, workers: int, max_retries: int):
    """
    Fetch course information and generate covers in batch.

    LANG: Language code (e.g. zh, en)
    """
    try:
        # Fetch course aliases and info
        course_aliases, course_info_map = fetch_courses(lang)
        if not course_aliases:
            logger.error("No courses found")
            return

        total_courses = len(course_aliases)
        logger.info(
            f"Starting to generate {total_courses} covers using {workers} workers"
        )

        # Process all courses with retry mechanism
        successful, failed_courses = process_batch(
            course_aliases=course_aliases,
            course_info_map=course_info_map,
            lang=lang,
            overwrite=overwrite,
            workers=workers,
            description=f"Generating covers for {lang}",
            max_retries=max_retries,
        )

        # Final report
        logger.info("\nFinal Results:")
        logger.info(f"Total courses processed: {total_courses}")
        logger.info(f"Successfully generated: {len(successful)}")
        logger.info(f"Failed: {len(failed_courses)}")

        if failed_courses:
            logger.info("\nFailed courses after all retries:")
            for course, error in failed_courses:
                logger.error(f"{course}: {error}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
