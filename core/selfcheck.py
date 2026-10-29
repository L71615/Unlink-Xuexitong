# -*- coding: utf-8 -*-
"""启动环境自检：依赖、驱动、浏览器、写入权限、答题 Key。

只做本地、无网络的快速检查；结果在主页日志里逐条列出，
关键项失败时弹一次提示，避免换台电脑后「点了没反应」。
"""
from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass

BUNDLED_DRIVER = os.path.join("task", "tool", "edge_driver", "msedgedriver.exe")
BROWSER_PATHS = {
    "edge": (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ),
    "chrome": (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ),
}


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str = ""
    fix: str = ""
    critical: bool = False


def _module(name: str, label: str, fix: str, critical: bool = False) -> Check:
    try:
        importlib.import_module(name)
    except Exception as error:  # pragma: no cover - 依赖缺失时才走到
        return Check(label, False, f"导入失败：{error}", fix, critical)
    return Check(label, True, "已安装")


def _python() -> Check:
    version = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info < (3, 10):
        return Check("Python 版本", False, version, "升级到 Python 3.10 或更高版本", True)
    return Check("Python 版本", True, version)


def _driver(path: str) -> Check:
    candidate = (path or "").strip() or BUNDLED_DRIVER
    if os.path.isfile(candidate):
        return Check("浏览器驱动", True, candidate)
    return Check("浏览器驱动", False, candidate,
                 "在设置里选择 msedgedriver.exe，或放回 task/tool/edge_driver/", True)


def _browser(name: str) -> Check:
    label = "浏览器"
    if not name or name in ("不指定浏览器", "自动"):
        return Check(label, True, "自动选择，不检查固定路径")
    paths = BROWSER_PATHS.get(name.lower())
    if not paths:
        return Check(label, True, f"未内置 {name} 的路径检查")
    for path in paths:
        if os.path.isfile(path):
            return Check(label, True, path)
    return Check(label, False, f"没有找到 {name} 的可执行文件",
                 f"确认已安装 {name}，或在设置里改用「不指定浏览器」")


def _writable() -> Check:
    folder = os.path.join("task", "tool")
    path = os.path.join(folder, f".selfcheck_{os.getpid()}")
    try:
        os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("ok")
        os.remove(path)
    except OSError as error:
        return Check("配置写入权限", False, str(error),
                     "把程序放到有写权限的目录，或以管理员身份运行", True)
    return Check("配置写入权限", True, folder)


def _api_key(account: dict) -> Check:
    key = str((account or {}).get("API") or "").strip()
    if key:
        return Check("答题 API Key", True, "已填写")
    return Check("答题 API Key", False, "未填写",
                 "不用 AI 答题可以忽略；需要时在设置里填写", False)


def run(account: dict | None = None) -> list[Check]:
    """跑一遍全部检查，返回结果列表。"""
    account = account or {}
    checks = [
        _python(),
        _module("customtkinter", "customtkinter", "pip install customtkinter", True),
        _module("selenium", "selenium", "pip install selenium", True),
        _module("pyautogui", "PyAutoGUI", "pip install PyAutoGUI", True),
        _module("Crypto.Cipher.AES", "pycryptodome", "pip install pycryptodome"),
        _module("openai", "openai", "pip install openai"),
        _driver(account.get("driver_path", "")),
        _browser(account.get("browser", "")),
        _writable(),
        _api_key(account),
    ]
    return checks


def failures(checks: list[Check]) -> list[Check]:
    return [check for check in checks if not check.ok]
