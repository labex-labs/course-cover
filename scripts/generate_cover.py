import os
import sys
import random
import requests
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from datetime import datetime
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


def get_course_info(course_alias: str, lang: str) -> tuple[dict | None, bool]:
    """从 LabEx API 获取课程信息

    返回：
        tuple: (course_info, is_language_supported)
        - course_info: 如果课程不存在为 None，否则为 dict
        - is_language_supported: 语言不支持为 False，否则为 True
    """
    logger.info(f"正在获取 {course_alias} 的 {lang} 课程信息")
    url = f"https://labex.io/api/v2/courses/{course_alias}?lang={lang}"
    try:
        logger.info(f"请求：{url}")
        response = requests.get(url)
        response.raise_for_status()
        course_info = response.json()["course"]

        # 检查请求的语言是否可用
        available_langs = course_info.get("langs", [])
        if lang not in available_langs:
            logger.warning(
                f"课程 {course_alias} 不支持 {lang}，可用语言：{', '.join(available_langs)}"
            )
            # 返回课程信息，但标记语言不支持
            return course_info, False

        logger.info(f"课程名称：{course_info['name']}")
        return course_info, True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"未找到课程 {course_alias}")
            return None, False  # 课程不存在
        logger.error(f"HTTP 错误：{e}")
        raise  # 重新抛出其他 HTTP 错误
    except Exception as e:
        logger.error(f"获取课程信息出错：{e}")
        raise  # 重新抛出其他错误


def get_course_type(type_id: int) -> str:
    """将课程类型 ID 转换为类型名称"""
    type_map = {0: "normal", 1: "alibaba", 3: "project"}
    return type_map.get(type_id, "normal")


def get_freepik_image(term: str) -> str:
    """使用重试机制从 Freepik 获取随机图标 URL"""
    logger.info(f"正在搜索 Freepik 图标：{term}")
    api_key = os.environ.get("FREEPIK_API_KEY")
    if not api_key:
        logger.error("未设置 FREEPIK_API_KEY 环境变量")
        raise ValueError("未设置 FREEPIK_API_KEY 环境变量")

    params = {
        "term": term,
        "filters[shape]": "lineal-color",
        "thumbnail_size": "512",
        "page": 1,
        "limit": 20,
    }

    headers = {
        "Accept-Language": "en-gb",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-freepik-api-key": api_key,
    }

    max_retries = 3
    retry_delay = 1  # 秒

    for attempt in range(max_retries):
        try:
            response = requests.get(
                "https://api.freepik.com/v1/icons", params=params, headers=headers
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("data"):
                logger.warning("未找到 Freepik 图标：%s", term)
                return "https://cdn.jsdelivr.net/gh/labex-labs/course-cover/default.png"

            lineal_color = [
                item
                for item in data["data"]
                if "lineal color" in item["style"]["name"].lower()
            ]
            image_list = lineal_color if lineal_color else data["data"]
            random_image = random.choice(image_list)

            logger.info(
                f"成功获取 Freepik 图标：{random_image['thumbnails'][0]['url']}"
            )
            return random_image["thumbnails"][0]["url"]

        except Exception as e:
            logger.warning(
                f"第 {attempt + 1}/{max_retries} 次尝试失败：{term}",
                exc_info=e,
            )
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
            else:
                logger.error(f"所有重试均失败：{term}", exc_info=e)
                return "https://cdn.jsdelivr.net/gh/labex-labs/course-cover/labex-icon-blue.png"


def generate_random_color() -> str:
    """生成随机浅色背景色"""

    def rand():
        return random.randint(180, 255)

    return f"{rand():02x}{rand():02x}{rand():02x}"


def download_image(url: str, course_alias: str) -> str:
    """下载图片到 assets 目录"""
    assets_dir = Path(__file__).parent.parent / "assets" / "icons"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 用课程别名和原始扩展名生成文件名
    ext = url.split(".")[-1].lower()
    if ext not in ["png", "jpg", "jpeg"]:
        ext = "png"
    filename = f"{course_alias}.{ext}"
    image_path = assets_dir / filename

    # 如果不存在则下载
    if not image_path.exists():
        try:
            logger.info(f"正在下载图片：{url}")
            response = requests.get(url, stream=True)
            response.raise_for_status()

            with image_path.open("wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"图片已保存到 {image_path}")
        except Exception as e:
            logger.error(f"下载图片出错：{e}")
            return url  # 下载失败时返回原始 URL

    # 返回用于 HTML 的相对路径
    return f"./assets/icons/{filename}"


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


def generate_cover(course_alias: str, lang: str, overwrite: bool = False):
    """生成课程封面图片

    参数：
        course_alias (str): 课程别名
        lang (str): 语言代码
        overwrite (bool, optional): 是否覆盖已存在的封面，默认为 False。

    返回：
        bool: 成功或跳过返回 True，课程不存在返回 False
    """
    logger.info(f"开始生成课程封面：{course_alias}, 语言：{lang}")

    # 检查文件是否已存在
    output_dir = Path(__file__).parent.parent / "public" / lang
    output_path = output_dir / f"{course_alias}.png"

    if output_path.exists() and not overwrite:
        logger.info(f"{output_path} 已存在且未启用覆盖，跳过生成")
        return True  # 跳过也视为成功

    # 优先从属性获取课程信息（批量模式）
    if (
        hasattr(generate_cover, "course_info")
        and generate_cover.course_info is not None
    ):
        course_info = generate_cover.course_info
        # 检查批量模式下语言是否支持
        available_langs = course_info.get("langs", [])
        is_language_supported = lang in available_langs
        # 用完后清空，避免影响下次调用
        generate_cover.course_info = None
    else:
        # 单独模式下单独获取课程信息
        course_info, is_language_supported = get_course_info(course_alias, lang)
        if course_info is None:
            logger.info(f"跳过生成，课程 {course_alias} 不存在")
            return False

    # 语言不支持则跳过
    if not is_language_supported:
        logger.info(f"跳过生成，课程 {course_alias} 不支持 {lang}")
        return True  # 课程存在但语言不支持

    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载或生成课程配置
    course_config = load_course_config(course_alias)
    if course_config is None:
        # 从 Freepik 获取新图片
        freepik_url = get_freepik_image(course_alias.replace("-", " "))
        # 下载图片并获取本地路径
        local_image_path = download_image(freepik_url, course_alias)

        # 生成新配置
        course_config = {
            "image_url": local_image_path,
            "bg_color": generate_random_color(),
            "created_at": datetime.now().isoformat(),
        }
        # 只有 Freepik 获取的图片才添加 remote_url
        if not freepik_url.startswith("./"):
            course_config["remote_url"] = freepik_url

        # 保存配置
        save_course_config(course_alias, course_config)
        logger.info(f"已生成新课程配置：{course_alias}")
    else:
        logger.info(f"使用已存在的课程配置：{course_alias}")

    # 组装参数
    params = {
        "course_type": get_course_type(course_info.get("type", 0)),
        "course_name": course_info["name"].replace("`", ""),
        "image_url": course_config["image_url"],
        "bg_color": course_config["bg_color"],
        "lang": lang,
    }
    logger.debug(f"生成参数：{params}")

    # 读取模板 HTML
    template_path = Path(__file__).parent.parent / "preview.html"
    logger.info(f"使用模板：{template_path}")

    # 用 Playwright 生成截图
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

    return True  # 成功返回 True


@click.command()
@click.argument("course_alias")
@click.argument("lang")
@click.option(
    "--overwrite/--no-overwrite",
    default=False,
    help="如已存在则覆盖封面",
)
def main(course_alias: str, lang: str, overwrite: bool = False):
    """
    生成课程封面图片。

    COURSE_ALIAS: 课程别名（如 html-for-beginners）
    LANG: 课程语言代码（如 en, zh），或 'all' 表示全部支持语言
    """
    try:
        if lang == "all":
            logger.info(f"正在为 {course_alias} 生成所有支持语言的封面...")
            success = True
            # 只获取一次课程信息，避免多次 API 调用
            course_info, _ = get_course_info(course_alias, "en")
            if course_info is None:
                logger.error(f"未找到课程 {course_alias}")
                sys.exit(1)
            
            generate_cover.course_info = course_info

            for supported_lang in SUPPORTED_LANGUAGES:
                try:
                    if not generate_cover(course_alias, supported_lang, overwrite):
                        success = False
                        logger.warning(f"为 {supported_lang} 生成封面失败")
                except Exception as e:
                    success = False
                    logger.error(f"为 {supported_lang} 生成封面时出错：{str(e)}")

            if not success:
                sys.exit(1)
        else:
            if lang not in SUPPORTED_LANGUAGES:
                logger.error(
                    f"不支持的语言：{lang}。支持的语言有：{', '.join(SUPPORTED_LANGUAGES)}"
                )
                sys.exit(1)
            if not generate_cover(course_alias, lang, overwrite):
                sys.exit(1)

        logger.info(f"{course_alias} 的封面生成成功")
    except Exception as e:
        logger.error(f"出错：{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
