import os
from pathlib import Path
from generate_cover import generate_cover

def main():
    # 读取 zh-alias.txt 文件
    alias_file = Path(__file__).parent.parent / "zh-alias.txt"
    with open(alias_file, "r") as f:
        aliases = [line.strip() for line in f if line.strip()]

    # 检查输出目录
    output_dir = Path(__file__).parent.parent / "public" / "zh"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 获取已存在的封面
    existing_covers = {f.stem for f in output_dir.glob("*.png")}

    # 统计信息
    total = len(aliases)
    skipped = 0
    generated = 0
    failed = 0

    # 批量生成封面
    for i, alias in enumerate(aliases, 1):
        if alias in existing_covers:
            print(f"[{i}/{total}] Skipping existing cover: {alias}")
            skipped += 1
            continue

        try:
            print(f"[{i}/{total}] Generating cover for: {alias}")
            generate_cover(alias, "zh", False)
            generated += 1
        except Exception as e:
            print(f"Failed to generate cover for {alias}: {str(e)}")
            failed += 1

    # 打印统计信息
    print("\nGeneration completed!")
    print(f"Total aliases: {total}")
    print(f"Skipped: {skipped}")
    print(f"Generated: {generated}")
    print(f"Failed: {failed}")

if __name__ == "__main__":
    main() 