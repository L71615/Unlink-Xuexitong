# -*- coding: utf-8 -*-
"""界面设计令牌：颜色、字体、图标。改整体配色只改这一个文件。"""
from __future__ import annotations

import tkinter.font as tkfont

import customtkinter as ctk

# ---------------- 基础色 ----------------
BG = "#F6F7F9"          # 窗口底色
PANEL = "#FFFFFF"       # 卡片
LINE = "#E8EAEE"        # 分隔线 / 边框
LINE_SOFT = "#F1F3F6"   # 更淡的分隔
TEXT = "#12161C"        # 主文字
TEXT_SOFT = "#4D545E"   # 次级文字
MUTED = "#7A828E"       # 说明文字
FAINT = "#9AA1AB"       # 更淡的说明

OK = "#2FA36B"
WARN = "#D98324"
DANGER = "#D64545"

# 主题色：(强调色, 浅底)
ACCENTS = {
    "蓝": ("#2F6BFF", "#EDF2FF"),
    "青": ("#0F766E", "#E6F2EF"),
    "靛": ("#4F46E5", "#EEF0FF"),
    "石墨": ("#14161A", "#F1F2F4"),
}
DEFAULT_ACCENT = "蓝"

UI_FAMILIES = ("Microsoft YaHei", "微软雅黑", "Segoe UI", "Helvetica")
MONO_FAMILIES = ("Cascadia Mono", "Consolas", "Courier New")
ICON_FAMILIES = ("Segoe Fluent Icons", "Segoe MDL2 Assets")

# Segoe MDL2 / Fluent 图标码位
ICONS = {
    "home": "\uE80F",
    "log": "\uE8FD",
    "score": "\uE930",
    "bank": "\uE8F1",
    "error": "\uE7BA",
    "settings": "\uE713",
    "help": "\uE897",
    "play": "\uE768",
    "sign": "\uE787",
    "stop": "\uE71A",
    "refresh": "\uE72C",
    "delete": "\uE74D",
    "search": "\uE721",
    "user": "\uE77B",
    "clock": "\uE823",
    "save": "\uE74E",
    "folder": "\uE8B7",
    "add": "\uE710",
    "chevron": "\uE76C",
}

_state = {
    "family": "Microsoft YaHei",
    "size": 13,
    "accent": DEFAULT_ACCENT,
    "icon_family": None,
}


def configure(family: str | None = None, size: int | None = None,
              accent: str | None = None) -> None:
    """启动时调用一次，把用户设置灌进来。"""
    if family:
        _state["family"] = family
    if size:
        _state["size"] = int(size)
    if accent in ACCENTS:
        _state["accent"] = accent


def accent_name() -> str:
    return _state["accent"]


def set_accent(name: str) -> None:
    if name in ACCENTS:
        _state["accent"] = name


def accent() -> str:
    return ACCENTS.get(_state["accent"], ACCENTS[DEFAULT_ACCENT])[0]


def accent_weak() -> str:
    return ACCENTS.get(_state["accent"], ACCENTS[DEFAULT_ACCENT])[1]


def base_size() -> int:
    return int(_state["size"])


def ui_family() -> str:
    return _state["family"]


def icon_family() -> str:
    if _state["icon_family"] is None:
        try:
            families = set(tkfont.families())
        except Exception:
            families = set()
        found = ""
        for name in ICON_FAMILIES:
            if name in families:
                found = name
                break
        _state["icon_family"] = found
    return _state["icon_family"]


def font(size: int | None = None, weight: str = "normal", mono: bool = False,
         icon: bool = False) -> ctk.CTkFont:
    """按当前设置生成字体，size 缺省跟随基础字号。"""
    if icon:
        family = icon_family() or "Segoe UI Symbol"
        return ctk.CTkFont(family=family, size=size or 14)
    family = (MONO_FAMILIES[0] if mono else ui_family())
    return ctk.CTkFont(family=family, size=int(size or _state["size"]), weight=weight)


def shade(hex_color: str, factor: float) -> str:
    """把颜色调暗(0<factor<1)或调亮(factor>1)。"""
    hex_color = hex_color.lstrip("#")
    rgb = [int(hex_color[i:i + 2], 16) for i in (0, 2, 4)]
    if factor <= 1:
        rgb = [int(c * factor) for c in rgb]
    else:
        rgb = [int(c + (255 - c) * (factor - 1)) for c in rgb]
    return "#%02X%02X%02X" % tuple(max(0, min(255, c)) for c in rgb)
