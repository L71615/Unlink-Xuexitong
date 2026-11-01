# -*- coding: utf-8 -*-
"""通用小组件：卡片、标签、状态胶囊、导航项、按钮。"""
from __future__ import annotations

import functools
import os

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

from gui import theme

ICON_FONT_FILES = (r"C:\Windows\Fonts\SegoeIcons.ttf",
                   r"C:\Windows\Fonts\segmdl2.ttf")


@functools.lru_cache(maxsize=128)
def _glyph(name: str, px: int, color: str):
    """把图标字体里的字形画成 4 倍图，保证高 DPI 下依然锐利。"""
    char = theme.ICONS.get(name)
    if not char:
        return None
    path = next((p for p in ICON_FONT_FILES if os.path.exists(p)), None)
    if path is None:
        return None
    try:
        font = ImageFont.truetype(path, px * 4)
    except OSError:
        return None
    box = px * 4
    image = Image.new("RGBA", (box, box), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.text((box / 2, box / 2), char, font=font, fill=color, anchor="mm")
    return image


def icon_image(name: str, size: int = 14, color: str | None = None):
    """给按钮/标签用的图标图片；拿不到字体时返回 None，界面自动降级为纯文字。"""
    image = _glyph(name, size, color or theme.MUTED)
    if image is None:
        return None
    return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))


def _attach_icon(kwargs: dict, icon: str | None, fallback: str) -> None:
    if not icon:
        return
    color = kwargs.pop("icon_color", None) or kwargs.get("text_color") or fallback
    size = kwargs.pop("icon_size", 14)
    image = icon_image(icon, size, color)
    if image is not None:
        kwargs.setdefault("image", image)
        kwargs.setdefault("compound", "left")


class Card(ctk.CTkFrame):
    """白底圆角卡片。"""

    def __init__(self, master, padding: tuple[int, int] = (0, 0), **kwargs):
        kwargs.setdefault("fg_color", theme.PANEL)
        kwargs.setdefault("corner_radius", theme.RADIUS)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", theme.LINE)
        super().__init__(master, **kwargs)
        self._pad = padding

    def body(self):
        return self


class SectionTitle(ctk.CTkLabel):
    def __init__(self, master, text: str, size: int | None = None, **kwargs):
        kwargs.setdefault("text_color", theme.TEXT)
        kwargs.setdefault("anchor", "w")
        super().__init__(master, text=text, font=theme.font(size or 13, "bold"), **kwargs)


class IconBadge(ctk.CTkFrame):
    """圆角方形图标底座。"""

    def __init__(self, master, name: str, color: str, bg: str,
                 size: int = 34, icon_size: int = 15, **kwargs):
        kwargs.setdefault("width", size)
        kwargs.setdefault("height", size)
        kwargs.setdefault("corner_radius", theme.RADIUS_SM)
        kwargs.setdefault("fg_color", bg)
        super().__init__(master, **kwargs)
        self.pack_propagate(False)
        self.grid_propagate(False)
        Icon(self, name, icon_size, color).place(relx=0.5, rely=0.5, anchor="center")


class StatTile(Card):
    """数据卡：图标 + 标签 + 大数字 + 说明。"""

    def __init__(self, master, icon: str, label: str, value: str = "0",
                 sub: str = "", color: str | None = None, bg: str | None = None,
                 **kwargs):
        super().__init__(master, **kwargs)
        color = color or theme.accent()
        bg = bg or theme.accent_weak()
        self._color = color

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14, 0))
        IconBadge(top, icon, color, bg, 32, 14).pack(side="left")
        ctk.CTkLabel(top, text=label, font=theme.font(11),
                     text_color=theme.MUTED, anchor="w").pack(
            side="left", padx=(10, 0))

        self._value = ctk.CTkLabel(self, text=value, font=theme.font(22, "bold"),
                                   text_color=theme.TEXT, anchor="w")
        self._value.pack(fill="x", padx=16, pady=(6, 0))
        self._sub = ctk.CTkLabel(self, text=sub, font=theme.font(10),
                                 text_color=theme.FAINT, anchor="w")
        self._sub.pack(fill="x", padx=16, pady=(0, 12))

    def set(self, value: str, sub: str | None = None) -> None:
        self._value.configure(text=value)
        if sub is not None:
            self._sub.configure(text=sub)


class PageHeader(ctk.CTkFrame):
    """页面标题 + 副标题，可选右侧控件容器。"""

    def __init__(self, master, title: str, subtitle: str = "", **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", anchor="s")
        ctk.CTkLabel(left, text=title, font=theme.font(21, "bold"),
                     text_color=theme.TEXT, anchor="w").pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(left, text=subtitle, font=theme.font(11),
                         text_color=theme.MUTED, anchor="w").pack(anchor="w", pady=(2, 0))
        self.right = ctk.CTkFrame(self, fg_color="transparent", width=1, height=1)
        self.right.pack(side="right", anchor="s", pady=(0, 2))


class Hint(ctk.CTkLabel):
    def __init__(self, master, text: str = "", size: int | None = None, **kwargs):
        kwargs.setdefault("text_color", theme.MUTED)
        kwargs.setdefault("anchor", "w")
        super().__init__(master, text=text, font=theme.font(size or 12), **kwargs)


class Icon(ctk.CTkLabel):
    def __init__(self, master, name: str, size: int = 14, color: str = theme.MUTED, **kwargs):
        kwargs.setdefault("text", theme.ICONS.get(name, ""))
        kwargs.setdefault("text_color", color)
        kwargs.setdefault("width", 0)
        super().__init__(master, font=theme.font(size, icon=True), **kwargs)


class Chip(ctk.CTkFrame):
    """状态胶囊：● 定时 未开启"""

    def __init__(self, master, text: str = "", on: bool | None = None, **kwargs):
        kwargs.setdefault("fg_color", theme.PANEL)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", theme.LINE)
        kwargs.setdefault("corner_radius", theme.RADIUS_XS)
        kwargs.setdefault("height", 26)
        super().__init__(master, **kwargs)
        self.pack_propagate(False)
        self._dot = ctk.CTkLabel(self, text="●", font=theme.font(7),
                                 text_color=theme.FAINT, width=6)
        self._dot.pack(side="left", padx=(9, 5))
        self._label = ctk.CTkLabel(self, text=text, font=theme.font(10),
                                   text_color=theme.TEXT_SOFT)
        self._label.pack(side="left", padx=(0, 9))
        self._fit(text)

    @staticmethod
    def _width_for(text: str) -> int:
        width = 0
        for char in text:
            width += 11 if ord(char) > 127 else 7
        return max(70, width + 34)

    def _fit(self, text: str) -> None:
        self.configure(width=self._width_for(text))

    def set_state(self, text: str | None = None, on: bool | None = None,
                  color: str | None = None) -> None:
        if text is not None:
            self._label.configure(text=text)
            self._fit(text)
        if color is not None:
            self._dot.configure(text_color=color)
        elif on is not None:
            self._dot.configure(text_color=theme.OK if on else theme.FAINT)


class ProgressBar(ctk.CTkFrame):
    """细进度条：0 时完全不画，避免出现一个小圆点。"""

    def __init__(self, master, height: int = 8, **kwargs):
        kwargs.setdefault("height", height)
        kwargs.setdefault("fg_color", theme.TRACK)
        kwargs.setdefault("corner_radius", max(height // 2, 1))
        super().__init__(master, **kwargs)
        self._fill = ctk.CTkFrame(self, fg_color=theme.accent(),
                                  corner_radius=max(height // 2, 1))

    def set(self, ratio: float) -> None:
        ratio = max(0.0, min(1.0, float(ratio or 0)))
        if ratio <= 0:
            self._fill.place_forget()
        else:
            self._fill.place(x=0, y=0, relheight=1.0, relwidth=ratio)

    def set_color(self, color: str) -> None:
        self._fill.configure(fg_color=color)


class NavItem(ctk.CTkFrame):
    """侧栏导航项：图标 + 文字，支持选中态与悬停。"""

    def __init__(self, master, key: str, text: str, command=None, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("corner_radius", theme.RADIUS_SM)
        kwargs.setdefault("height", 36)
        super().__init__(master, **kwargs)
        self.pack_propagate(False)
        self._key = key
        self._text = text
        self._command = command
        self._active = False

        self.grid_columnconfigure(1, weight=1)
        self._icon = Icon(self, key, 14, theme.MUTED, width=18)
        self._icon.grid(row=0, column=0, padx=(11, 9), pady=8, sticky="w")
        self._label = ctk.CTkLabel(self, text=text, font=theme.font(12),
                                   text_color=theme.TEXT_SOFT, anchor="w")
        self._label.grid(row=0, column=1, sticky="w", padx=(0, 8))

        for widget in (self, self._icon, self._label):
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    # ------------------------------------------------------------------
    def _on_click(self, _event=None):
        if self._command:
            self._command(self._key)

    def _on_enter(self, _event=None):
        if not self._active:
            self.configure(fg_color=theme.LINE_SOFT)

    def _on_leave(self, _event=None):
        if not self._active:
            self.configure(fg_color="transparent")

    def set_active(self, active: bool) -> None:
        self._active = active
        if active:
            self.configure(fg_color=theme.accent_weak())
            self._icon.configure(text_color=theme.accent())
            self._label.configure(text_color=theme.accent(), font=theme.font(12, "bold"))
        else:
            self.configure(fg_color="transparent")
            self._icon.configure(text_color=theme.MUTED)
            self._label.configure(text_color=theme.TEXT_SOFT, font=theme.font(12))


def primary_button(master, text: str, command=None, icon: str | None = None, **kwargs):
    kwargs.setdefault("fg_color", theme.accent())
    kwargs.setdefault("hover_color", theme.shade(theme.accent(), 0.86))
    kwargs.setdefault("text_color", theme.WHITE)
    kwargs.setdefault("corner_radius", theme.RADIUS_SM)
    kwargs.setdefault("height", 38)
    kwargs.setdefault("font", theme.font(12, "bold"))
    kwargs.setdefault("text", text)
    kwargs.setdefault("command", command)
    _attach_icon(kwargs, icon, theme.WHITE)
    return ctk.CTkButton(master, **kwargs)


def ghost_button(master, text: str, command=None, icon: str | None = None, **kwargs):
    kwargs.setdefault("fg_color", theme.PANEL)
    kwargs.setdefault("hover_color", theme.LINE_SOFT)
    kwargs.setdefault("text_color", theme.TEXT_SOFT)
    kwargs.setdefault("border_width", 1)
    kwargs.setdefault("border_color", theme.LINE)
    kwargs.setdefault("corner_radius", theme.RADIUS_SM)
    kwargs.setdefault("height", 38)
    kwargs.setdefault("font", theme.font(12))
    kwargs.setdefault("text", text)
    kwargs.setdefault("command", command)
    _attach_icon(kwargs, icon, theme.TEXT_SOFT)
    return ctk.CTkButton(master, **kwargs)


def text_button(master, text: str, command=None, color: str | None = None, **kwargs):
    kwargs.setdefault("fg_color", "transparent")
    kwargs.setdefault("hover_color", theme.LINE_SOFT)
    kwargs.setdefault("text_color", color or theme.MUTED)
    kwargs.setdefault("font", theme.font(12))
    kwargs.setdefault("height", 28)
    kwargs.setdefault("width", 10)
    kwargs.setdefault("text", text)
    kwargs.setdefault("command", command)
    return ctk.CTkButton(master, **kwargs)


def thin_divider(master, color: str = theme.LINE):
    return ctk.CTkFrame(master, height=1, fg_color=color, corner_radius=0)
