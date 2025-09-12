#!/usr/bin/env python3
"""
批量为以 project- 开头的课程添加 project 状态标签
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict
import click
from rich.console import Console
from rich.logging import RichHandler
import logging

# 配置 rich 控制台
console = Console()

# 使用 rich 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        RichHandler(
            console=Console(stderr=True),  # 日志输出到 stderr
            show_time=False,  # 不显示时间
            show_path=False,  # 不显示文件路径
            rich_tracebacks=True,
        )
    ],
)
logger = logging.getLogger("rich")

# 支持的语言列表
SUPPORTED_LANGUAGES = ["en", "ja", "zh", "fr", "es", "de", "ru", "ko", "pt"]


def read_course_config() -> Dict[str, Dict]:
    """读取课程配置文件"""
    config_path = Path(__file__).parent.parent / "config" / "course-covers.json"
    if not config_path.exists():
        logger.error(f"配置文件不存在：{config_path}")
        return {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"成功读取配置文件，包含 {len(config)} 个课程")
        return config
    except Exception as e:
        logger.error(f"读取配置文件失败：{e}")
        return {}


def filter_project_courses(course_config: Dict[str, Dict]) -> List[str]:
    """筛选出以 project- 开头的课程别名"""
    project_courses = []
    for alias in course_config.keys():
        if alias.startswith("project-"):
            project_courses.append(alias)

    logger.info(f"找到 {len(project_courses)} 个以 project- 开头的课程")
    return project_courses


def generate_project_covers(aliases: List[str], lang: str, overwrite: bool = False):
    """为指定的课程列表生成带有 project 状态的封面"""
    from generate_cover import generate_cover

    success_count = 0
    total_count = len(aliases)

    logger.info(f"开始为 {total_count} 个课程生成 project 状态封面...")

    for i, alias in enumerate(aliases, 1):
        logger.info(f"[{i}/{total_count}] 处理课程：{alias}")

        try:
            # 根据语言参数决定如何处理
            if lang == "all":
                # 为所有支持的语言生成封面
                langs_to_process = SUPPORTED_LANGUAGES
            else:
                langs_to_process = [lang]

            course_success = True
            for lang_code in langs_to_process:
                try:
                    if not generate_cover(alias, lang_code, overwrite, "project"):
                        course_success = False
                        logger.warning(f"为 {alias} ({lang_code}) 生成封面失败")
                except Exception as e:
                    course_success = False
                    logger.error(f"为 {alias} ({lang_code}) 生成封面时出错：{str(e)}")

            if course_success:
                success_count += 1

        except Exception as e:
            logger.error(f"处理课程 {alias} 时出错：{str(e)}")

    logger.info(f"批量处理完成：{success_count}/{total_count} 个课程成功")


@click.command(no_args_is_help=True)
@click.option(
    "--lang",
    type=click.Choice(SUPPORTED_LANGUAGES + ["all"]),
    default="all",
    help="课程语言代码，或 'all' 表示全部支持语言",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="如已存在则覆盖封面",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="仅显示将要处理的课程，不实际生成封面",
)
def main(lang: str, overwrite: bool = False, dry_run: bool = False):
    """
    批量为以 project- 开头的课程添加 project 状态标签
    """
    try:
        # 读取课程配置
        course_config = read_course_config()
        if not course_config:
            sys.exit(1)

        # 筛选出 project- 开头的课程
        project_courses = filter_project_courses(course_config)

        if not project_courses:
            logger.warning("未找到任何以 project- 开头的课程")
            return

        # 显示将要处理的课程
        console.print(f"\n[bold blue] 将要处理的课程 ({len(project_courses)} 个):[/bold blue]")
        for alias in project_courses:
            console.print(f"  • {alias}")

        if dry_run:
            console.print("\n[yellow] 这是 dry-run 模式，不会实际生成封面 [/yellow]")
            return

        # 确认操作
        if not click.confirm(f"\n确认要为这 {len(project_courses)} 个课程生成 project 状态封面吗？"):
            console.print("[yellow] 操作已取消 [/yellow]")
            return

        # 开始批量处理
        generate_project_covers(project_courses, lang, overwrite)

        logger.info("批量处理完成")

    except Exception as e:
        logger.error(f"执行出错：{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
