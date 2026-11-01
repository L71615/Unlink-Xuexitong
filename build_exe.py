# -*- coding: utf-8 -*-
"""打包脚本：生成绿色免安装目录。

用法：
    python build_exe.py              # 默认 onedir，产物 dist/课业助手/
    python build_exe.py --onefile    # 单文件，产物 dist/课业助手.exe（每次启动要解压，慢）

产物：
    dist/课业助手/课业助手.exe + _internal/，双击 exe 即可运行。

注意：只收集运行需要的帮助文档、驱动和扩展，不会把
account_info.json、刷课记录、日志、缓存打进包里。
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from version import APP_VERSION, EXE_NAME, version_tuple

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "build_assets"

# GitHub Actions 的控制台是 cp1252，直接 print 中文会 UnicodeEncodeError
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TOOL_FILES = ("Help.txt", "font_dict.txt", "version_info", "account_info.example.json")
CRX_FILES = ("speed.crx", "chrome-extension.crx")

# 这台机器的 Python 环境装了不少机器学习/分析库，PyInstaller 会顺着
# 可选导入把它们全收进来（体积几个 GB）。项目本身完全用不到，直接排除。
EXCLUDES = (
    "torch", "torchvision", "torchaudio", "tensorflow", "keras",
    "transformers", "datasets", "accelerate", "tokenizers", "sentencepiece",
    "pandas", "scipy", "matplotlib", "pyarrow", "sklearn", "numba",
    "pygame", "bokeh", "plotly", "IPython", "jupyter", "notebook", "pytest",
    "cv2", "gi", "PyQt5", "PyQt6", "PySide2", "PySide6", "wx",
    "sqlalchemy", "alembic", "statsmodels", "seaborn",
    "lxml", "sounddevice", "bcrypt", "websockets", "IPython",
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
    left, top, right, bottom = draw.textbbox((0, 0), "课", font=font)
    draw.text(((size - (right - left)) / 2 - left, (size - (bottom - top)) / 2 - top),
              "课", font=font, fill="#FFFFFF")
    image.save(path, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])


def make_version_file(path: Path) -> None:
    major, minor, patch, build = version_tuple()
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, {build}),
    prodvers=({major}, {minor}, {patch}, {build}),
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
        StringStruct('FileDescription', '{EXE_NAME}'),
        StringStruct('FileVersion', '{APP_VERSION}'),
        StringStruct('InternalName', 'CourseHelper'),
        StringStruct('OriginalFilename', '{EXE_NAME}.exe'),
        StringStruct('ProductName', '{EXE_NAME}'),
        StringStruct('ProductVersion', '{APP_VERSION}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [2052, 1200])])
  ]
)
"""
    path.write_text(content, encoding="utf-8")


def stage_assets() -> Path:
    """把需要随包分发的资源收集到 build_assets/task 下。"""
    task_dst = ASSETS / "task"
    # 只清 task 子目录：app.ico 和 version.txt 就在 ASSETS 下，不能一起删
    if task_dst.exists():
        shutil.rmtree(task_dst)
    task_dst.mkdir(parents=True)

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
    # 版本号单一来源：界面上显示的版本与 exe 属性一致
    (tool_dst / "version_info").write_text(APP_VERSION + "\n", encoding="utf-8")
    return task_dst


def fetch_drivers(majors: list[str]) -> None:
    """把指定主版本的 msedgedriver 下到 task/tool/edge_driver/<主版本>/。

    下载走 urllib：本机 schannel 对 msedgedriver.microsoft.com 报
    ``SEC_E_NO_CREDENTIALS``，curl/Invoke-WebRequest 都不行，Python 的
    urllib 可以。CI 上同理可用。
    """
    import io
    import urllib.request
    import zipfile

    base = "https://msedgedriver.microsoft.com"
    for major in majors:
        major = major.strip()
        if not major.isdigit():
            print(f"跳过非法主版本：{major!r}")
            continue
        latest_url = f"{base}/LATEST_RELEASE_{major}_WINDOWS"
        version = urllib.request.urlopen(latest_url, timeout=30).read().decode("utf-16").strip()
        if not version:
            print(f"取不到 Edge {major} 的最新版本号，跳过")
            continue
        target = ROOT / "task" / "tool" / "edge_driver" / major
        target.mkdir(parents=True, exist_ok=True)
        zip_url = f"{base}/{version}/edgedriver_win64.zip"
        payload = urllib.request.urlopen(zip_url, timeout=180).read()
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = [n for n in archive.namelist() if n.endswith("msedgedriver.exe")]
            if not names:
                print(f"{zip_url} 里没有 msedgedriver.exe")
                continue
            (target / "msedgedriver.exe").write_bytes(archive.read(names[0]))
        print(f"驱动 {version} -> {target}")


def directory_size(path: Path) -> float:
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total / 1024 / 1024


def build_command(icon: Path, version_file: Path, data_dir: Path, onefile: bool,
                  console: bool = False) -> list[str]:
    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--console" if console else "--windowed",
        "--onefile" if onefile else "--onedir",
        "--name", EXE_NAME,
        "--icon", str(icon),
        "--version-file", str(version_file),
        "--add-data", f"{data_dir};task",
        "--collect-all", "customtkinter",
        "--collect-all", "selenium",
        "--hidden-import", "main",
        "--hidden-import", "version",
        "--hidden-import", "task",
        "--hidden-import", "task.xxt",
        "--hidden-import", "Crypto",
        "--hidden-import", "Crypto.Cipher",
        "--hidden-import", "Crypto.Cipher.AES",
        *sum((["--exclude-module", name] for name in EXCLUDES), []),
        "start.py",
    ]
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description="打包课业助手")
    parser.add_argument("--onefile", action="store_true",
                        help="生成单文件 exe（启动慢，约 5-10 秒解压）")
    parser.add_argument("--skip-build", action="store_true",
                        help="只准备 build_assets，不调用 PyInstaller")
    parser.add_argument("--fetch-drivers", default="",
                        help="下载指定主版本的 msedgedriver，逗号分隔，如 156,155")
    parser.add_argument("--console", action="store_true",
                        help="保留控制台窗口，排查打包后启动失败时用")
    args = parser.parse_args()

    if args.fetch_drivers:
        fetch_drivers(args.fetch_drivers.split(","))

    ASSETS.mkdir(exist_ok=True)
    icon = ASSETS / "app.ico"
    make_icon(icon)
    version_file = ASSETS / "version.txt"
    make_version_file(version_file)
    data_dir = stage_assets()

    if args.skip_build:
        print(f"资源已准备：{data_dir}")
        return 0

    command = build_command(icon, version_file, data_dir, args.onefile, args.console)
    print(" ".join(command))
    result = subprocess.run(command, cwd=str(ROOT))
    if result.returncode != 0:
        print("打包失败")
        return result.returncode

    if args.onefile:
        exe = ROOT / "dist" / f"{EXE_NAME}.exe"
        if exe.exists():
            print(f"已生成：{exe}（{exe.stat().st_size / 1024 / 1024:.1f} MB）")
    else:
        bundle = ROOT / "dist" / EXE_NAME
        exe = bundle / f"{EXE_NAME}.exe"
        if exe.exists():
            size = directory_size(bundle)
            print(f"已生成：{bundle}（目录 {size:.1f} MB）")
            print(f"双击运行：{exe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
