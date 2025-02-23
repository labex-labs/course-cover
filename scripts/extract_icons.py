import os
from pathlib import Path
import json
from PIL import Image
from datetime import datetime
import click
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich import print as rprint

# 初始化 rich console
console = Console()


def extract_dominant_color(image_path: Path) -> str:
    """Extract the dominant background color from the bottom-left corner of the image"""
    with Image.open(image_path) as img:
        if img.mode != "RGB":
            img = img.convert("RGB")

        left = 0
        bottom = img.height - 10
        area = img.crop((left, bottom, left + 10, bottom + 10))

        avg_color_per_row = [pixel for pixel in area.getdata()]
        avg_color = tuple(
            sum(color) // len(avg_color_per_row) for color in zip(*avg_color_per_row)
        )

        return f"{avg_color[0]:02x}{avg_color[1]:02x}{avg_color[2]:02x}"


def extract_icon(image_path: Path, output_path: Path) -> bool:
    """Extract 512x512 icon from the right side of the cover image"""
    try:
        with Image.open(image_path) as img:
            if img.size != (1400, 720):
                console.print(
                    f"[yellow]Warning:[/] Unexpected image dimensions for {image_path}: {img.size}"
                )
                return False

            start_y = 113
            start_x = 808
            icon = img.crop((start_x, start_y, start_x + 512, start_y + 512))

            output_path.parent.mkdir(parents=True, exist_ok=True)
            icon.save(output_path, "PNG")
            return True
    except Exception as e:
        console.print(f"[red]Error:[/] extracting icon from {image_path}: {e}")
        return False


def update_config(course_alias: str, icon_path: str, bg_color: str):
    """Update the course covers configuration file"""
    config_path = Path(__file__).parent.parent / "config" / "course-covers.json"

    if config_path.exists():
        config = json.loads(config_path.read_text())
    else:
        config = {}

    config[course_alias] = {
        "image_url": icon_path,
        "bg_color": bg_color,
        "created_at": datetime.now().isoformat(),
    }

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True))


@click.command()
@click.option(
    "--covers-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Directory containing cover images",
    default=lambda: Path(__file__).parent.parent / "public" / "en",
)
@click.option(
    "--icons-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Directory to save extracted icons",
    default=lambda: Path(__file__).parent.parent / "assets" / "icons",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def main(covers_dir: Path, icons_dir: Path, verbose: bool):
    """Extract course icons from cover images and update configuration."""
    console.print("[bold blue]Starting icon extraction process...[/]")

    # Create icons directory if it doesn't exist
    icons_dir.mkdir(parents=True, exist_ok=True)

    # Get total number of PNG files
    png_files = list(covers_dir.glob("*.png"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Processing covers...", total=len(png_files))

        for cover_path in png_files:
            course_alias = cover_path.stem
            icon_path = icons_dir / f"{course_alias}.png"

            if verbose:
                console.print(f"\nProcessing: [cyan]{course_alias}[/]")

            # Extract icon
            if extract_icon(cover_path, icon_path):
                # Extract background color
                bg_color = extract_dominant_color(cover_path)

                # Update configuration
                relative_icon_path = f"./assets/icons/{course_alias}.png"
                update_config(course_alias, relative_icon_path, bg_color)

                if verbose:
                    console.print(f"✓ Successfully processed [green]{course_alias}[/]")
            else:
                console.print(f"[red]✗[/] Failed to process {course_alias}")

            progress.advance(task)

    console.print("\n[bold green]Icon extraction completed![/]")


if __name__ == "__main__":
    main()
