# -*- coding: utf-8 -*-
"""界面设计令牌：颜色、字体、图标。改整体配色只改这一个文件。"""
from __future__ import annotations

import tkinter.font as tkfont

import customtkinter as ctk

# ---------------- 基础色 ----------------
BG = "#F3F5F9"          # 窗口底色
PANEL = "#FFFFFF"       # 卡片
SIDEBAR = "#FAFBFD"     # 侧栏
SURFACE = "#F8FAFC"     # 卡片内的浅底区域
LINE = "#E6E9F0"        # 分隔线 / 边框
LINE_SOFT = "#F1F3F7"   # 更淡的分隔
TEXT = "#101828"        # 主文字
TEXT_SOFT = "#475467"   # 次级文字
MUTED = "#667085"       # 说明文字
FAINT = "#98A2B3"       # 更淡的说明

OK = "#16A34A"
WARN = "#D97706"
DANGER = "#DC2626"

# 深色主视觉
HERO = "#0D1B2E"
HERO_2 = "#16263D"
HERO_LINE = "#2A3B55"
HERO_TEXT = "#F8FAFC"
HERO_MUTED = "#9FB0C9"

# ---------------- 尺寸节奏 ----------------
RADIUS = 12          # 卡片
RADIUS_SM = 9        # 按钮 / 小标签
RADIUS_XS = 8        # 胶囊
PAGE_PAD = 28        # 页面左右留白
GAP = 16             # 栏间距
LOG_BG = "#FCFDFE"   # 日志区底色（白卡里略深一点，压住边界）
BAR_TRACK = "#E7EBF2"

# 补充色：弱底、成功底、滚动条
WEAK = "#F2F4F8"        # 胶囊 / 弱标记底
OK_WEAK = "#EDF8F1"     # 成功标记底
SCROLL = "#D9DFEA"      # 滚动条
SCROLL_HOVER = "#C4CCDA"
TRACK = "#EEF1F5"       # CTk 组件默认浅底
WHITE = "#FFFFFF"

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
    "resolved_family": None,
    "resolved_name": "",
}


def configure(family: str | None = None, size: int | None = None,
              accent: str | None = None) -> None:
    """启动时调用一次，把用户设置灌进来。"""
    if family:
        _state["family"] = family
        _state["resolved_family"] = None
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
    """返回本机真实可用的字体族（Tk 只认注册名，不认识英文别名时会静默回退）。"""
    family = _state["family"]
    if _state["resolved_family"] == family:
        return _state["resolved_name"]
    resolved = family
    try:
        families = set(tkfont.families())
    except Exception:
        families = set()
    if families and family not in families:
        for alias in UI_FAMILIES:
            if alias in families:
                resolved = alias
                break
    _state["resolved_family"] = family
    _state["resolved_name"] = resolved
    return resolved


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
