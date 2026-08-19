#!/usr/bin/env python3
"""Generate title-free course covers from the existing icon and color config."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "course-covers.json"
DEFAULT_OUTPUT_DIR = ROOT / "public" / "icon-only"
CANVAS_SIZE = (1400, 720)
ICON_BOX = (512, 512)


def load_config() -> dict[str, dict[str, str]]:
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        return json.load(config_file)


def generate_cover(
    alias: str, cover: dict[str, str], output_dir: Path
) -> Path:
    background = cover.get("bg_color")
    icon_path_value = cover.get("image_url")

    if not background or not icon_path_value:
        raise ValueError(f"Course {alias!r} is missing bg_color or image_url")

    icon_path = (ROOT / icon_path_value).resolve()
    if not icon_path.is_file():
        raise FileNotFoundError(f"Icon not found: {icon_path}")

    try:
        background_rgb = tuple(bytes.fromhex(background.removeprefix("#")))
    except ValueError as error:
        raise ValueError(
            f"Invalid background color for {alias!r}: {background}"
        ) from error
    if len(background_rgb) != 3:
        raise ValueError(f"Invalid background color for {alias!r}: {background}")

    canvas = Image.new("RGB", CANVAS_SIZE, background_rgb)
    with Image.open(icon_path) as source:
        icon = source.convert("RGBA")
    icon.thumbnail(ICON_BOX, Image.Resampling.LANCZOS)

    position = (
        (CANVAS_SIZE[0] - icon.width) // 2,
        (CANVAS_SIZE[1] - icon.height) // 2,
    )
    canvas.paste(icon, position, icon)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{alias}.png"
    canvas.save(output_path, format="PNG", optimize=True)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate 1400x720 icon-only course covers."
    )
    parser.add_argument("aliases", nargs="*", help="Course aliases from the cover config")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate every course in the config",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory (default: public/icon-only)",
    )
    args = parser.parse_args()

    if args.all and args.aliases:
        parser.error("course aliases cannot be combined with --all")
    if not args.all and not args.aliases:
        parser.error("provide at least one course alias or use --all")

    covers = load_config()
    aliases = sorted(covers) if args.all else args.aliases
    unknown_aliases = [alias for alias in aliases if alias not in covers]
    if unknown_aliases:
        parser.error(f"unknown course alias: {', '.join(unknown_aliases)}")

    output_dir = args.output_dir.resolve()
    generated = 0
    failures: list[tuple[str, str]] = []
    for alias in aliases:
        try:
            output_path = generate_cover(alias, covers[alias], output_dir)
        except (OSError, ValueError) as error:
            failures.append((alias, str(error)))
            print(f"ERROR {alias}: {error}", file=sys.stderr)
            continue

        try:
            displayed_path = output_path.relative_to(ROOT)
        except ValueError:
            displayed_path = output_path
        print(displayed_path)
        generated += 1

    print(f"Generated {generated} cover(s) in {output_dir}")
    if failures:
        print(f"Failed to generate {len(failures)} cover(s)", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
