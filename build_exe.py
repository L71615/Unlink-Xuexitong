# -*- coding: utf-8 -*-
"""打包脚本：生成单文件 exe。

用法：
    python build_exe.py

产物：
    dist/UnlinkXuexitong.exe

注意：只收集运行需要的图片、帮助文档、驱动和扩展，不会把
account_info.json、刷课记录、日志、缓存打进包里。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_NAME = "UnlinkXuexitong"
APP_VERSION = "1.0.0"
ASSETS = ROOT / "build_assets"

TOOL_FILES = ("Help.txt", "font_dict.txt", "version_info", "account_info.example.json")
CRX_FILES = ("speed.crx", "chrome-extension.crx", "zyb-227372.crx")

# 这台机器的 Python 环境装了不少机器学习/分析库，PyInstaller 会顺着
# 可选导入把它们全收进来（体积几个 GB）。项目本身完全用不到，直接排除。
EXCLUDES = (
    "torch", "torchvision", "torchaudio", "tensorflow", "keras",
    "transformers", "datasets", "accelerate", "tokenizers", "sentencepiece",
    "pandas", "scipy", "matplotlib", "pyarrow", "sklearn", "numba",
    "pygame", "bokeh", "plotly", "IPython", "jupyter", "notebook", "pytest",
    "cv2", "gi", "PyQt5", "PyQt6", "PySide2", "PySide6", "wx",
    "sqlalchemy", "alembic", "statsmodels", "seaborn",
)


def make_icon(path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    size = 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([6, 6, size - 6, size - 6], radius=58, fill="#2F6BFF")
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 148, index=0)
    except OSError:
        font = ImageFont.load_default()
    left, top, right, bottom = draw.textbbox((0, 0), "学", font=font)
    draw.text(((size - (right - left)) / 2 - left, (size - (bottom - top)) / 2 - top),
              "学", font=font, fill="#FFFFFF")
    image.save(path, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])


def make_version_file(path: Path) -> None:
    content = """VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('080404b0', [
        StringStruct('CompanyName', 'L71615'),
        StringStruct('FileDescription', 'Xuexitong Helper'),
        StringStruct('FileVersion', '1.0.0'),
        StringStruct('InternalName', 'UnlinkXuexitong'),
        StringStruct('OriginalFilename', 'UnlinkXuexitong.exe'),
        StringStruct('ProductName', 'Xuexitong Helper'),
        StringStruct('ProductVersion', '1.0.0')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [2052, 1200])])
  ]
)
"""
    path.write_text(content, encoding="utf-8")


def stage_assets() -> Path:
    """把需要随包分发的资源收集到 build_assets/task 下。"""
    if ASSETS.exists():
        shutil.rmtree(ASSETS)
    task_dst = ASSETS / "task"
    img_dst = task_dst / "img"
    img_dst.mkdir(parents=True)

    for name in (ROOT / "task" / "img").iterdir():
        if name.is_file():
            shutil.copy2(name, img_dst / name.name)

    tool_dst = task_dst / "tool"
    tool_dst.mkdir()
    for name in TOOL_FILES:
        source = ROOT / "task" / "tool" / name
        if source.is_file():
            shutil.copy2(source, tool_dst / name)
    for name in CRX_FILES:
        source = ROOT / "task" / "tool" / name
        if source.is_file():
            shutil.copy2(source, tool_dst / name)

    driver_src = ROOT / "task" / "tool" / "edge_driver"
    if driver_src.is_dir():
        shutil.copytree(driver_src, tool_dst / "edge_driver")

    record_dst = task_dst / "record"
    record_dst.mkdir()
    (record_dst / "__init__.py").write_text("", encoding="utf-8")

    # 空的进度文件，避免首次运行缺少 course_process.json
    (tool_dst / "course_process.json").write_text("{}", encoding="utf-8")
    return task_dst


def main() -> int:
    ASSETS.mkdir(exist_ok=True)
    icon = ASSETS / "app.ico"
    make_icon(icon)
    version_file = ASSETS / "version.txt"
    make_version_file(version_file)
    data_dir = stage_assets()

    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile", "--windowed",
        "--name", APP_NAME,
        "--icon", str(icon),
        "--version-file", str(version_file),
        "--add-data", f"{data_dir};task",
        "--collect-all", "customtkinter",
        "--collect-all", "selenium",
        "--hidden-import", "main",
        "--hidden-import", "task",
        "--hidden-import", "task.xxt",
        *sum((["--exclude-module", name] for name in EXCLUDES), []),
        "start.py",
    ]
    print(" ".join(command))
    result = subprocess.run(command, cwd=str(ROOT))
    if result.returncode != 0:
        print("打包失败")
        return result.returncode

    exe = ROOT / "dist" / f"{APP_NAME}.exe"
    if exe.exists():
        print(f"已生成：{exe}（{exe.stat().st_size / 1024 / 1024:.1f} MB）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
