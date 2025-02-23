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
from generate_cover import generate_cover

console = Console()


def load_course_config() -> dict:
    """Load the course covers configuration file"""
    config_path = Path(__file__).parent.parent / "config" / "course-covers.json"
    if not config_path.exists():
        console.print("[red]❌ Course configuration file not found[/red]")
        return {}

    try:
        return json.loads(config_path.read_text())
    except Exception as e:
        console.print(f"[red]❌ Error loading course config: {e}[/red]")
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
            "\n[yellow]⚠ Skipping 'en' language as it's the source language[/yellow]"
        )
        return

    # Load configuration
    with console.status("[bold blue]Loading configuration...[/bold blue]") as status:
        config = load_course_config()
        if not config:
            console.print("\n[red]❌ No course configuration found[/red]")
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
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        BarColumn(complete_style="green"),
        TaskProgressColumn(),
        console=Console(stderr=True),  # 将进度条输出重定向到 stderr
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
                    console.print(
                        f"[dim]Cover already exists for [bold]{course_alias}[/bold], skipping...[/dim]"
                    )
                    progress.advance(task)
                    continue

                # Generate cover with overwrite parameter
                generate_cover(course_alias, lang, overwrite=overwrite)
                console.print(
                    f"[green]✓[/green] Successfully generated cover for [bold]{course_alias}[/bold]"
                )
                progress.advance(task)

            except Exception as e:
                console.print(
                    f"[red]❌ Error generating cover for [bold]{course_alias}[/bold]: {str(e)}[/red]"
                )
                progress.advance(task)
                continue

    console.print(
        f"\n[bold green]✓ Successfully completed generating covers for {lang}![/bold green]"
    )


if __name__ == "__main__":
    main()
