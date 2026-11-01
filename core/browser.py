# -*- coding: utf-8 -*-
"""浏览器与驱动的统一入口。

以前驱动的解析散在 `main.py` 与 `core/selfcheck.py` 两处，路径还是相对
`task/tool/...` 的字符串，换个工作目录（打包版双击启动时很常见）就找不到；
内置驱动与系统 Edge 版本不匹配时，报错信息只有 Selenium 的长串堆栈。

这里把它们收拢：

- :func:`resolve_driver` 决定用哪个驱动（用户指定 / 内置 / 在线下载）；
- :func:`driver_state` 给出「浏览器版本 - 驱动版本 - 是否匹配」的状态，
  自检页和日志都用它；
- :func:`create_driver` 负责建 webdriver（含扩展与反自动化参数）。

版本判断只看 ``主.次.构建`` 三段：Edge 的补丁号（第四段）不一致时驱动
依然可用，这与实际表现一致。
"""
from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

def _app_root() -> Path:
    """打包后是 exe 所在目录（`_internal` 里只有运行库），源码运行时是项目根。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


ROOT = _app_root()
DRIVER_DIR = ROOT / "task" / "tool" / "edge_driver"
# 老布局：驱动直接放在 edge_driver/ 下；新布局按主版本分目录，见 :func:`bundled_drivers`
BUNDLED_DRIVER = DRIVER_DIR / "msedgedriver.exe"
SPEED_EXTENSION = ROOT / "task" / "tool" / "speed.crx"
EXTENSION = ROOT / "task" / "tool" / "chrome-extension.crx"

BROWSER_PATHS = {
    "edge": (
        Path(os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)")
        / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("ProgramFiles") or r"C:\Program Files")
        / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ),
    "chrome": (
        Path(os.environ.get("ProgramFiles") or r"C:\Program Files")
        / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)")
        / "Google" / "Chrome" / "Application" / "chrome.exe",
    ),
}


def parse_version(text) -> tuple[int, int, int] | None:
    """从 ``156.0.4314.50`` 这类字符串里取前三位，失败返回 None。"""
    if not text:
        return None
    parts = str(text).strip().split(".")
    numbers: list[int] = []
    for part in parts[:3]:
        digits = "".join(ch for ch in part if ch.isdigit())
        if not digits:
            return None
        numbers.append(int(digits))
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)  # type: ignore[return-value]


def versions_match(browser_version, driver_version) -> bool:
    """三段版本是否一致；任一方读不到时返回 False（交给调用方决定）。"""
    left = parse_version(browser_version)
    right = parse_version(driver_version)
    return bool(left and right and left == right)


class _FixedFileInfo(ctypes.Structure):
    _fields_ = [
        ("dwSignature", ctypes.c_uint32),
        ("dwStrucVersion", ctypes.c_uint32),
        ("dwFileVersionMS", ctypes.c_uint32),
        ("dwFileVersionLS", ctypes.c_uint32),
        ("dwProductVersionMS", ctypes.c_uint32),
        ("dwProductVersionLS", ctypes.c_uint32),
        ("dwFileFlagsMask", ctypes.c_uint32),
        ("dwFileFlags", ctypes.c_uint32),
        ("dwFileOS", ctypes.c_uint32),
        ("dwFileType", ctypes.c_uint32),
        ("dwFileSubtype", ctypes.c_uint32),
        ("dwFileDateMS", ctypes.c_uint32),
        ("dwFileDateLS", ctypes.c_uint32),
    ]


def file_version(path) -> str | None:
    """读 Windows 可执行文件的版本号，例如 ``156.0.4314.50``。

    不启动进程、不联网；非 Windows 或读取失败返回 None。
    """
    if not sys.platform.startswith("win"):
        return None
    target = str(path or "")
    if not target or not os.path.isfile(target):
        return None
    try:
        version_dll = ctypes.windll.version
        size = version_dll.GetFileVersionInfoSizeW(target, None)
        if not size:
            return None
        buffer = ctypes.create_string_buffer(size)
        if not version_dll.GetFileVersionInfoW(target, 0, size, buffer):
            return None
        pointer = ctypes.c_void_p()
        length = ctypes.c_uint()
        if not version_dll.VerQueryValueW(buffer, "\\", ctypes.byref(pointer),
                                          ctypes.byref(length)):
            return None
        info = ctypes.cast(pointer, ctypes.POINTER(_FixedFileInfo)).contents
        high, low = info.dwFileVersionMS, info.dwFileVersionLS
        return f"{high >> 16}.{high & 0xFFFF}.{low >> 16}.{low & 0xFFFF}"
    except Exception:
        return None


def browser_exe(browser: str) -> str | None:
    """返回已安装浏览器的可执行文件路径。"""
    for path in BROWSER_PATHS.get((browser or "").lower(), ()):
        if path.is_file():
            return str(path)
    return None


def browser_version(browser: str) -> str | None:
    exe = browser_exe(browser)
    return file_version(exe) if exe else None


def driver_version(path=None) -> str | None:
    """内置/指定驱动的版本号。"""
    target = Path(path) if path else BUNDLED_DRIVER
    return file_version(target)


def bundled_drivers() -> dict[str, Path]:
    """随包分发的驱动清单：``{主版本: 路径}``。

    新布局是 ``edge_driver/156/msedgedriver.exe``，可以同时带几个主版本，
    Edge 自动升级到另一个主版本时仍有匹配的驱动可用；老布局的扁平
    ``edge_driver/msedgedriver.exe`` 记为 ``"flat"`` 继续兼容。
    """
    drivers: dict[str, Path] = {}
    if DRIVER_DIR.is_dir():
        for item in sorted(DRIVER_DIR.iterdir()):
            if not item.is_dir():
                continue
            exe = item / "msedgedriver.exe"
            if item.name.isdigit() and exe.is_file():
                drivers[item.name] = exe
    if BUNDLED_DRIVER.is_file():
        drivers.setdefault("flat", BUNDLED_DRIVER)
    return drivers


def _pick_by_major(installed) -> Path | None:
    """按已装 Edge 的主版本挑驱动；没装浏览器时返回 None。

    目录名就是主版本，所以这里只认主版本：msedgedriver 只要求主版本一致，
    补丁号不同（浏览器自动小版本升级）也能用。这样连驱动文件版本读不出来的
    环境（个别打包/权限受限场景）也不会白白回退到联网下载。
    """
    major = parse_version(installed)
    if not major:
        return None
    drivers = bundled_drivers()
    return drivers.get(str(major[0]))


def _any_bundled() -> Path | None:
    """随便挑一个自带驱动：主版本号最大的优先，老扁平布局最后兜底。"""
    drivers = bundled_drivers()
    majors = [name for name in drivers if name.isdigit()]
    if majors:
        return drivers[max(majors, key=int)]
    return drivers.get("flat")


def resolve_driver(browser: str, driver_path: str = "") -> tuple[str, str]:
    """决定用哪个驱动。

    返回 ``(来源, 路径)``，来源取值：

    - ``custom``：设置页里手动指定的驱动；
    - ``bundled``：自带的 msedgedriver；
    - ``manager``：交给 Selenium Manager 联网下载（版本不匹配时的兜底）；
    - ``manager-missing``：本该用在线驱动，但 Selenium Manager 不在包里。
    """
    explicit = str(driver_path or "").strip()
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = (ROOT / path).resolve()
        if path.is_file():
            return "custom", str(path)
    name = (browser or "").lower()
    if name not in BROWSER_PATHS:
        # 设置页里存的是「不指定浏览器」这类中文选项，按 Edge 处理
        name = "edge"
    if name == "chrome":
        return "manager", ""
    installed = browser_version(name)
    matched = _pick_by_major(installed)
    if matched is not None:
        return "bundled", str(matched)
    if not installed:
        # 读不到浏览器版本（没装 / 权限受限）时，有内置驱动就直接用，别去联网
        fallback = _any_bundled()
        if fallback is not None:
            return "bundled", str(fallback)
    if not BUNDLED_DRIVER.is_file():
        return "manager", ""
    if installed:
        bundled = driver_version()
        if bundled and not versions_match(installed, bundled):
            # 补丁号不同没关系，主.次.构建不同就必须换驱动
            return "manager", ""
    return "bundled", str(BUNDLED_DRIVER)


def driver_state(browser: str = "", driver_path: str = "") -> dict:
    """浏览器 / 驱动版本与匹配情况，供自检和日志展示。"""
    name = (browser or "edge").lower()
    if name not in BROWSER_PATHS:
        name = "edge"
    installed = browser_version(name)
    source, path = resolve_driver(browser, driver_path)
    current = driver_version(path) if path else None
    if installed and current:
        matched: bool | None = versions_match(installed, current)
    else:
        matched = None
    return {
        "browser": name,
        "browser_version": installed,
        "driver_source": source,
        "driver_path": path,
        "driver_version": current,
        "available_drivers": sorted(bundled_drivers()),
        "matched": matched,
    }


def create_driver(browser: str, driver_path: str = "", speed="1", headless: bool = False):
    """建 webdriver：驱动按 :func:`resolve_driver` 选，扩展用绝对路径。"""
    name = (browser or "").lower()
    if name == "chrome":
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    else:
        from selenium.webdriver.edge.options import Options
        from selenium.webdriver.edge.service import Service
    from selenium import webdriver

    source, path = resolve_driver(browser, driver_path)
    if source in ("custom", "bundled"):
        service = Service(path)
    else:
        from selenium.webdriver.common import selenium_manager
        manager = Path(selenium_manager.__file__).parent / "windows" / "selenium-manager.exe"
        if manager.is_file():
            os.environ["SE_MANAGER_PATH"] = str(manager)
        service = Service()

    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    if str(speed) != "1" and SPEED_EXTENSION.is_file():
        options.add_extension(str(SPEED_EXTENSION))
    if EXTENSION.is_file():
        options.add_extension(str(EXTENSION))
    options.add_argument("--enable-extensions")
    if headless:
        options.add_argument("--headless=new")

    if name == "chrome":
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Edge(service=service, options=options)
    driver.implicitly_wait(2)
    return driver
