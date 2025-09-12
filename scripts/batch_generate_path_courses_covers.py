import os
import sys
import requests
import json
import click
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
import logging
from datetime import datetime

# 导入 generate_cover.py 中的函数
from generate_cover import generate_cover, get_course_info, SUPPORTED_LANGUAGES, logger

# 配置 rich 控制台
console = Console()


def get_paths_from_api() -> list[dict]:
    """从 LabEx API 获取 paths 信息"""
    logger.info("正在从 LabEx API 获取 paths 信息...")
    url = "https://labex.io/api/v2/paths/basic"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        paths = data.get("paths", [])
        logger.info(f"成功获取 {len(paths)} 个 paths")
        return paths
    except Exception as e:
        logger.error(f"获取 paths 信息失败：{e}")
        raise


def get_path_details(path_alias: str) -> dict | None:
    """从 LabEx API 获取指定 path 的详细信息"""
    logger.info(f"正在获取 path 详情：{path_alias}")
    url = f"https://labex.io/api/v2/paths/{path_alias}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        path_details = data.get("path")
        if path_details:
            logger.info(f"成功获取 path 详情：{path_alias}")
            return path_details
        else:
            logger.warning(f"path {path_alias} 没有详情信息")
            return None
    except Exception as e:
        logger.error(f"获取 path {path_alias} 详情失败：{e}")
        return None


def extract_level1_course_aliases(path_details: dict) -> list[str]:
    """从 path 详情中提取 level=1 的课程别名"""
    course_aliases = []

    if not path_details or "levels" not in path_details:
        return course_aliases

    for level_info in path_details["levels"]:
        if level_info.get("level") == 1 and "courses" in level_info:
            for course in level_info["courses"]:
                if "alias" in course:
                    course_aliases.append(course["alias"])

    logger.info(f"找到 {len(course_aliases)} 个 level=1 课程")
    return course_aliases


@click.command()
@click.option(
    "--lang",
    type=click.Choice(SUPPORTED_LANGUAGES + ["all"]),
    default="all",
    help="课程语言代码，或 'all' 表示全部支持语言",
)
@click.option("--overwrite", is_flag=True, help="覆盖已存在的封面（默认已启用）")
@click.option("--path-filter", help="只处理指定的 path（用逗号分隔），不指定则处理全部")
@click.option(
    "--course-filter", help="只处理指定的课程（用逗号分隔），不指定则处理全部"
)
def main(lang: str, overwrite: bool, path_filter: str, course_filter: str):
    """
    批量生成 LabEx paths 中所有 level=1 课程的封面图片。

    工作流程：
    1. 获取所有 paths 列表
    2. 对每个 path 获取详细信息
    3. 提取 level=1 的课程别名
    4. 为每个课程生成封面（带 course 状态标签）

    注意：默认启用覆盖模式，如果封面已存在会被覆盖。

    示例：
    python batch_generate_path_courses_covers.py --lang all
    python batch_generate_path_courses_covers.py --lang en --path-filter "linux,devops"
    """
    try:
        # 获取所有 paths
        all_paths = get_paths_from_api()

        # 过滤掉 alibaba 路径
        paths = [path for path in all_paths if path["alias"] != "alibaba"]
        filtered_alibaba_count = len(all_paths) - len(paths)
        if filtered_alibaba_count > 0:
            logger.info(f"已过滤掉 {filtered_alibaba_count} 个 alibaba 路径")

        # 过滤 paths（如果指定了过滤条件）
        if path_filter:
            filter_aliases = [alias.strip() for alias in path_filter.split(",")]
            paths = [path for path in paths if path["alias"] in filter_aliases]
            logger.info(f"根据 path 过滤条件，将处理 {len(paths)} 个 paths")

        if not paths:
            logger.error("没有找到需要处理的 paths")
            sys.exit(1)

        # 确定要处理的语言列表
        if lang == "all":
            target_languages = SUPPORTED_LANGUAGES
        else:
            target_languages = [lang]

        # 统计信息
        success_count = 0
        skip_count = 0
        fail_count = 0
        total_paths_processed = 0
        total_courses_found = 0

        logger.info(f"将逐个处理 {len(paths)} 个路径，每个路径的所有课程")

        # 逐个处理路径
        for path_idx, path in enumerate(paths, 1):
            path_alias = path["alias"]
            path_name = path["name"]

            logger.info("=" * 60)
            logger.info(
                f"开始处理路径 {path_idx}/{len(paths)}: {path_alias} ({path_name})"
            )
            logger.info("=" * 60)

            # 获取 path 详情
            path_details = get_path_details(path_alias)
            if not path_details:
                logger.warning(f"无法获取路径 {path_alias} 的详情，跳过")
                continue

            # 提取 level=1 课程
            course_aliases = extract_level1_course_aliases(path_details)
            if not course_aliases:
                logger.info(f"路径 {path_alias} 没有 level=1 课程，跳过")
                total_paths_processed += 1
                continue

            total_courses_found += len(course_aliases)
            logger.info(f"路径 {path_alias} 包含 {len(course_aliases)} 个 level=1 课程")

            # 过滤课程（如果指定了过滤条件）
            if course_filter:
                filter_course_aliases = [
                    alias.strip() for alias in course_filter.split(",")
                ]
                original_count = len(course_aliases)
                course_aliases = [
                    alias for alias in course_aliases if alias in filter_course_aliases
                ]
                filtered_count = original_count - len(course_aliases)
                if filtered_count > 0:
                    logger.info(f"根据课程过滤条件，过滤掉 {filtered_count} 个课程")

            if not course_aliases:
                logger.info(f"路径 {path_alias} 在应用课程过滤后没有需要处理的课程")
                total_paths_processed += 1
                continue

            # 处理这个路径的所有课程
            path_operations = len(course_aliases) * len(target_languages)

            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}[/bold blue]"),
                BarColumn(complete_style="green"),
                TaskProgressColumn(),
                console=Console(stderr=True),
                expand=True,
            ) as progress:
                task = progress.add_task(
                    f"[bold] 处理路径 {path_alias} 的课程 ({lang}) [/bold]",
                    total=path_operations,
                )

                for course_alias in course_aliases:
                    for target_lang in target_languages:
                        try:
                            progress.update(
                                task,
                                description=f"[bold] {course_alias} ({target_lang}) [/bold]",
                            )

                            # 检查课程是否存在
                            course_details, is_supported = get_course_info(
                                course_alias, target_lang
                            )
                            if course_details is None:
                                logger.warning(f"课程 {course_alias} 不存在，跳过")
                                skip_count += 1
                                progress.advance(task)
                                continue

                            if not is_supported:
                                logger.info(
                                    f"课程 {course_alias} 不支持 {target_lang}，跳过"
                                )
                                skip_count += 1
                                progress.advance(task)
                                continue

                            # 生成封面（默认启用覆盖）
                            result = generate_cover(
                                course_alias=course_alias,
                                lang=target_lang,
                                overwrite=True,  # 默认启用覆盖
                                status="course",  # 添加 course 状态标签
                            )

                            if result:
                                success_count += 1
                                logger.info(
                                    f"成功生成 {course_alias} ({target_lang}) 封面"
                                )
                            else:
                                fail_count += 1
                                logger.error(
                                    f"生成 {course_alias} ({target_lang}) 封面失败"
                                )

                        except Exception as e:
                            fail_count += 1
                            logger.error(
                                f"处理 {course_alias} ({target_lang}) 时出错：{str(e)}"
                            )

                        progress.advance(task)

            total_paths_processed += 1
            logger.info(
                f"路径 {path_alias} 处理完成 ({total_paths_processed}/{len(paths)})"
            )
            logger.info("-" * 60)

        # 输出统计信息
        logger.info("=" * 50)
        logger.info("任务完成统计：")
        logger.info(f"  处理的路径数：{total_paths_processed}")
        logger.info(f"  发现的课程数：{total_courses_found}")
        logger.info(f"  成功生成：{success_count}")
        logger.info(f"  跳过：{skip_count}")
        logger.info(f"  失败：{fail_count}")
        logger.info("=" * 50)

        if fail_count > 0:
            sys.exit(1)

    except Exception as e:
        logger.error(f"出错：{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
