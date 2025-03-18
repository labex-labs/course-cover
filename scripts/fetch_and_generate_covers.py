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


def fetch_courses(lang: str) -> list:
    """Fetch all courses from LabEx API"""
    url = f"https://labex.io/api/v2/courses?lang={lang}"
    try:
        logger.info(f"Fetching courses from: {url}")
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Extract course aliases
        courses = data.get("courses", [])
        course_aliases = [course["alias"] for course in courses]

        logger.info(f"Found {len(course_aliases)} courses")
        return course_aliases
    except Exception as e:
        logger.error(f"Error fetching courses: {e}")
        return []


def process_course(course_alias: str, lang: str, overwrite: bool) -> tuple:
    """Process a single course cover generation"""
    try:
        result = generate_cover(course_alias, lang, overwrite)
        return course_alias, result, None
    except Exception as e:
        return course_alias, False, str(e)


@click.command()
@click.argument("lang")
@click.option("--overwrite", is_flag=True, help="Overwrite existing covers")
@click.option(
    "--workers",
    default=multiprocessing.cpu_count(),
    help="Number of worker processes",
    type=int,
)
def main(lang: str, overwrite: bool, workers: int):
    """
    Fetch course information and generate covers in batch.

    LANG: Language code (e.g. zh, en)
    """
    try:
        # Fetch course aliases
        course_aliases = fetch_courses(lang)
        if not course_aliases:
            logger.error("No courses found")
            return

        total_courses = len(course_aliases)
        logger.info(
            f"Starting to generate {total_courses} covers using {workers} workers"
        )

        # Create a process pool
        pool = multiprocessing.Pool(processes=workers)

        # Prepare the worker function with fixed parameters
        worker_func = partial(process_course, lang=lang, overwrite=overwrite)

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
                f"[bold]Generating covers for {lang}[/bold]", total=total_courses
            )

            # Process courses in parallel and track results
            successful = 0
            failed = 0
            failed_courses = []

            for course_alias, result, error in pool.imap_unordered(
                worker_func, course_aliases
            ):
                if result:
                    successful += 1
                    progress.update(
                        task,
                        description=f"[green]Successfully processed {course_alias}[/green]",
                    )
                else:
                    failed += 1
                    failed_courses.append((course_alias, error))
                    progress.update(
                        task, description=f"[red]Failed processing {course_alias}[/red]"
                    )
                progress.advance(task)

        # Close and join the pool
        pool.close()
        pool.join()

        # Report results
        logger.info(f"Cover generation completed!")
        logger.info(f"Successfully generated: {successful}")
        logger.info(f"Failed: {failed}")

        if failed_courses:
            logger.info("\nFailed courses:")
            for course, error in failed_courses:
                logger.error(f"{course}: {error}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
