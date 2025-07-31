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
from playwright.sync_api import sync_playwright

# 配置 rich 控制台
console = Console()

# 使用 rich 配置日志
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

# 支持的语言列表
SUPPORTED_LANGUAGES = ["en", "ja", "zh", "fr", "es", "de", "ru", "ko", "pt"]


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


def generate_random_color() -> str:
    """生成随机浅色背景色"""
    import random
    
    def rand():
        return random.randint(180, 255)
    
    return f"{rand():02x}{rand():02x}{rand():02x}"


def save_course_config(course_alias: str, config: dict):
    """保存课程配置到 JSON 文件"""
    config_path = Path(__file__).parent.parent / "config" / "course-covers.json"
    try:
        if config_path.exists():
            existing_config = json.loads(config_path.read_text())
        else:
            existing_config = {}

        existing_config[course_alias] = config
        config_path.write_text(json.dumps(existing_config, indent=2, sort_keys=True))
    except Exception as e:
        logger.error(f"保存课程配置出错：{e}")


def load_course_config(course_alias: str) -> dict:
    """从 JSON 文件加载课程配置"""
    config_path = Path(__file__).parent.parent / "config" / "course-covers.json"
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("{}")
        return None

    try:
        config = json.loads(config_path.read_text())
        return config.get(course_alias)
    except Exception as e:
        logger.error(f"加载课程配置出错：{e}")
        return None


def generate_path_cover(
    path_alias: str, 
    path_name: str, 
    template_text: str, 
    lang: str, 
    overwrite: bool = False
) -> bool:
    """为指定 path 生成封面图片
    
    参数：
        path_alias (str): path 别名，如 'linux'
        path_name (str): path 名称，如 'Linux'  
        template_text (str): 模板文案，如 '{} Interview Questions'
        lang (str): 语言代码
        overwrite (bool): 是否覆盖已存在的封面
        
    返回：
        bool: 成功返回 True，失败返回 False
    """
    logger.info(f"开始生成 path 封面：{path_alias}, 语言：{lang}")
    
    # 构建课程别名（用于文件名）
    course_alias = f"{path_alias}-interview-questions"
    
    # 构建课程名称（用于显示）
    course_name = template_text.format(path_name)
    
    # 检查文件是否已存在
    output_dir = Path(__file__).parent.parent / "public" / lang
    output_path = output_dir / f"{course_alias}.png"
    
    if output_path.exists() and not overwrite:
        logger.info(f"{output_path} 已存在且未启用覆盖，跳过生成")
        return True
    
    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查对应的图标是否存在
    icon_path = Path(__file__).parent.parent / "assets" / "icons" / f"{path_alias}.png"
    if not icon_path.exists():
        logger.warning(f"未找到 {path_alias} 的图标文件：{icon_path}")
        # 使用默认图标
        image_url = "./assets/icons/linux.png"  # 使用 linux 作为默认图标
    else:
        image_url = f"./assets/icons/{path_alias}.png"
    
    # 加载或生成课程配置
    course_config = load_course_config(course_alias)
    if course_config is None:
        # 生成新配置
        course_config = {
            "image_url": image_url,
            "bg_color": generate_random_color(),
            "created_at": datetime.now().isoformat(),
        }
        # 保存配置
        save_course_config(course_alias, course_config)
        logger.info(f"已生成新课程配置：{course_alias}")
    else:
        logger.info(f"使用已存在的课程配置：{course_alias}")
    
    # 组装参数
    params = {
        "course_type": "normal",
        "course_name": course_name,
        "image_url": course_config["image_url"],
        "bg_color": course_config["bg_color"],
        "lang": lang,
    }
    
    logger.debug(f"生成参数：{params}")
    
    # 读取模板 HTML
    template_path = Path(__file__).parent.parent / "preview.html"
    logger.info(f"使用模板：{template_path}")
    
    # 用 Playwright 生成截图
    try:
        with sync_playwright() as p:
            logger.info("启动浏览器")
            browser = p.chromium.launch()
            # 设置更大视口确保内容完整
            page = browser.new_page(viewport={"width": 1600, "height": 900})
            
            # 拼接参数
            params_str = "&".join(f"{k}={v}" for k, v in params.items())
            file_url = f"file://{template_path}?{params_str}"
            
            # 跳转并截图
            logger.info(f"截图：{file_url}")
            page.goto(file_url)
            page.wait_for_load_state("networkidle")
            
            # 精确截取指定区域
            page.screenshot(
                path=str(output_path), clip={"x": 0, "y": 0, "width": 1400, "height": 720}
            )
            logger.info(f"截图已保存：{output_path}")
            
            browser.close()
            logger.info("浏览器已关闭")
            
        return True
    except Exception as e:
        logger.error(f"生成封面时出错：{e}")
        return False


@click.command()
@click.option(
    "--template",
    default="{} Interview Questions",
    help="模板文案，使用 {} 作为 path name 的占位符，默认为 '{} Interview Questions'"
)
@click.option(
    "--lang",
    type=click.Choice(SUPPORTED_LANGUAGES),
    default="en",
    help="语言代码，默认为 en"
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="覆盖已存在的封面"
)
@click.option(
    "--path-filter",
    help="只处理指定的 path（用逗号分隔），不指定则处理全部"
)
def main(template: str, lang: str, overwrite: bool, path_filter: str):
    """
    批量生成 LabEx paths 对应的封面图片。
    
    例如：
    python batch_generate_paths_covers.py --template "{} Interview Questions" --lang en
    """
    try:
        # 验证模板文案
        if "{}" not in template:
            logger.error("模板文案必须包含 {} 作为 path name 的占位符")
            sys.exit(1)
        
        # 获取 paths 信息
        paths = get_paths_from_api()
        
        # 过滤 paths（如果指定了过滤条件）
        if path_filter:
            filter_aliases = [alias.strip() for alias in path_filter.split(",")]
            paths = [path for path in paths if path["alias"] in filter_aliases]
            logger.info(f"根据过滤条件，将处理 {len(paths)} 个 paths")
        
        if not paths:
            logger.error("没有找到需要处理的 paths")
            sys.exit(1)
        
        # 统计信息
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        # 使用进度条批量生成
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            BarColumn(complete_style="green"),
            TaskProgressColumn(),
            console=Console(stderr=True),
            expand=True,
        ) as progress:
            task = progress.add_task(
                f"[bold] 正在为 {lang} 生成 paths 封面 [/bold]", total=len(paths)
            )
            
            for path in paths:
                path_alias = path["alias"]
                path_name = path["name"]
                
                try:
                    progress.update(
                        task, description=f"[bold] 正在处理 {path_alias} ({path_name})[/bold]"
                    )
                    
                    # 检查对应的图标是否存在
                    icon_path = Path(__file__).parent.parent / "assets" / "icons" / f"{path_alias}.png"
                    if not icon_path.exists():
                        logger.warning(f"跳过 {path_alias}，未找到对应图标文件")
                        skip_count += 1
                        progress.advance(task)
                        continue
                    
                    # 生成封面
                    result = generate_path_cover(
                        path_alias, path_name, template, lang, overwrite
                    )
                    
                    if result:
                        success_count += 1
                        logger.info(f"成功生成 {path_alias} 封面")
                    else:
                        fail_count += 1
                        logger.error(f"生成 {path_alias} 封面失败")
                        
                except Exception as e:
                    fail_count += 1
                    logger.error(f"处理 {path_alias} 时出错：{str(e)}")
                
                progress.advance(task)
        
        # 输出统计信息
        logger.info(f"任务完成！成功：{success_count}，跳过：{skip_count}，失败：{fail_count}")
        
        if fail_count > 0:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"出错：{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()