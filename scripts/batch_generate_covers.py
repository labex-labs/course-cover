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

# 使用 rich 配置日志（与 generate_cover.py 保持一致）
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
    """加载课程封面配置文件"""
    config_path = Path(__file__).parent.parent / "config" / "course-covers.json"
    if not config_path.exists():
        logger.error("未找到课程配置文件")
        return {}

    try:
        return json.loads(config_path.read_text())
    except Exception as e:
        logger.error(f"加载课程配置文件出错：{e}")
        return {}


def get_existing_covers(lang: str) -> set:
    """获取指定语言下已存在的课程封面集合"""
    covers_path = Path(__file__).parent.parent / "public" / lang
    if not covers_path.exists():
        return set()

    return {path.stem for path in covers_path.glob("*.png")}


@click.command()
@click.argument("lang")
@click.option("--overwrite", is_flag=True, help="覆盖已存在的封面")
@click.option("--clean-invalid", is_flag=True, help="移除无效的课程配置")
@click.option(
    "--skip-projects",
    is_flag=True,
    help="跳过别名以 'project-' 开头的课程",
)
def main(lang: str, overwrite: bool, clean_invalid: bool, skip_projects: bool):
    """为指定语言批量生成课程封面。

    LANG 为目标语言代码（如 zh, es, fr）
    """
    # 加载配置
    logger.info("正在加载课程配置...")
    config = load_course_config()
    if not config:
        logger.error("未找到任何课程配置")
        return

    # 记录需要移除的无效课程
    invalid_courses = set()

    # 获取已存在的封面
    existing_covers = get_existing_covers(lang)

    # 创建输出目录
    output_dir = Path(__file__).parent.parent / "public" / lang
    output_dir.mkdir(parents=True, exist_ok=True)

    # 为配置中的每个课程生成封面
    total_courses = len(config)
    logger.info(f"开始为 {lang} 生成 {total_courses} 个课程封面")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        BarColumn(complete_style="green"),
        TaskProgressColumn(),
        console=Console(stderr=True),
        expand=True,
    ) as progress:
        task = progress.add_task(
            f"[bold] 正在为 {lang} 生成封面 [/bold]", total=total_courses
        )

        for course_alias, course_config in config.items():
            try:
                progress.update(
                    task, description=f"[bold] 正在处理 {course_alias}[/bold]"
                )

                # 如果启用 skip_projects，跳过以 "project-" 开头的课程
                if skip_projects and course_alias.startswith("project-"):
                    logger.info(f"跳过项目课程：{course_alias}")
                    progress.advance(task)
                    continue

                # 如果封面已存在且未启用 overwrite，则跳过
                if course_alias in existing_covers and not overwrite:
                    logger.info(f"{course_alias} 的封面已存在，跳过...")
                    progress.advance(task)
                    continue

                # 生成封面，传递 overwrite 参数
                try:
                    result = generate_cover(course_alias, lang, overwrite=overwrite)

                    # 如果启用 clean_invalid 且课程不存在，则记录为无效课程
                    if clean_invalid and result is False:
                        # 仅在课程确实不存在时才加入无效课程
                        invalid_courses.add(course_alias)
                        logger.warning(f"标记 {course_alias} 为无效课程，准备移除")
                    elif result is True:
                        logger.info(f"成功处理 {course_alias}")

                except Exception as e:
                    logger.error(f"生成 {course_alias} 封面时出错：{str(e)}")
                    # 临时错误不标记为无效
                    continue

                progress.advance(task)

            except Exception as e:
                logger.error(f"主循环处理 {course_alias} 时出错：{str(e)}")
                progress.advance(task)
                continue

    # 如需清理无效课程
    if clean_invalid and invalid_courses:
        logger.info(f"正在清理 {len(invalid_courses)} 个无效课程配置...")
        config_path = Path(__file__).parent.parent / "config" / "course-covers.json"
        try:
            # 重新加载当前配置
            with open(config_path) as f:
                current_config = json.load(f)

            # 移除无效课程
            for course in invalid_courses:
                if course in current_config:
                    del current_config[course]
                    logger.info(f"已移除无效课程：{course}")

            # 保存更新后的配置
            with open(config_path, "w") as f:
                json.dump(current_config, indent=2, sort_keys=True, fp=f)

            logger.info("无效课程配置清理完成")
        except Exception as e:
            logger.error(f"清理无效课程时出错：{str(e)}")

    logger.info(f"{lang} 的课程封面生成任务已完成！")


if __name__ == "__main__":
    main()
