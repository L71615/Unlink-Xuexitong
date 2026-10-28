# -*- coding: utf-8 -*-
"""通用小组件：卡片、标签、状态胶囊、导航项、按钮。"""
from __future__ import annotations

import customtkinter as ctk

from gui import theme


class Card(ctk.CTkFrame):
    """白底圆角卡片。"""

    def __init__(self, master, padding: tuple[int, int] = (0, 0), **kwargs):
        kwargs.setdefault("fg_color", theme.PANEL)
        kwargs.setdefault("corner_radius", 16)
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


class PageHeader(ctk.CTkFrame):
    """页面标题 + 副标题，可选右侧控件容器。"""

    def __init__(self, master, title: str, subtitle: str = "", **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", anchor="s")
        ctk.CTkLabel(left, text=title, font=theme.font(20, "bold"),
                     text_color=theme.TEXT, anchor="w").pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(left, text=subtitle, font=theme.font(11),
                         text_color=theme.MUTED, anchor="w").pack(anchor="w", pady=(3, 0))
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
        kwargs.setdefault("corner_radius", 15)
        kwargs.setdefault("height", 30)
        super().__init__(master, **kwargs)
        self.pack_propagate(False)
        self._dot = ctk.CTkLabel(self, text="●", font=theme.font(9), text_color=theme.FAINT)
        self._dot.pack(side="left", padx=(10, 5))
        self._label = ctk.CTkLabel(self, text=text, font=theme.font(11),
                                   text_color=theme.TEXT_SOFT)
        self._label.pack(side="left", padx=(0, 11))
        self._fit(text)

    @staticmethod
    def _width_for(text: str) -> int:
        width = 0
        for char in text:
            width += 12 if ord(char) > 127 else 7
        return max(74, width + 36)

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
        kwargs.setdefault("fg_color", "#EEF1F5")
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


class KVRow(ctk.CTkFrame):
    """一行「说明 ---- 值」。"""

    def __init__(self, master, key: str, value: str = "-", **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self._key = ctk.CTkLabel(self, text=key, font=theme.font(11),
                                 text_color=theme.MUTED, anchor="w")
        self._key.grid(row=0, column=0, sticky="w")
        self._value = ctk.CTkLabel(self, text=value, font=theme.font(12, "bold"),
                                   text_color=theme.TEXT, anchor="e")
        self._value.grid(row=0, column=1, sticky="e")

    def set(self, value: str) -> None:
        self._value.configure(text=value)


class NavItem(ctk.CTkFrame):
    """侧栏导航项：图标 + 文字，支持选中态与悬停。"""

    def __init__(self, master, key: str, text: str, command=None, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("corner_radius", 9)
        kwargs.setdefault("height", 38)
        super().__init__(master, **kwargs)
        self.pack_propagate(False)
        self._key = key
        self._text = text
        self._command = command
        self._active = False

        self.grid_columnconfigure(1, weight=1)
        self._icon = Icon(self, key, 14, theme.MUTED, width=18)
        self._icon.grid(row=0, column=0, padx=(10, 9), pady=8, sticky="w")
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
    kwargs.setdefault("text_color", "#FFFFFF")
    kwargs.setdefault("corner_radius", 10)
    kwargs.setdefault("height", 40)
    kwargs.setdefault("font", theme.font(13, "bold"))
    kwargs.setdefault("text", text)
    kwargs.setdefault("command", command)
    return ctk.CTkButton(master, **kwargs)


def ghost_button(master, text: str, command=None, icon: str | None = None, **kwargs):
    kwargs.setdefault("fg_color", theme.PANEL)
    kwargs.setdefault("hover_color", theme.LINE_SOFT)
    kwargs.setdefault("text_color", theme.TEXT_SOFT)
    kwargs.setdefault("border_width", 1)
    kwargs.setdefault("border_color", theme.LINE)
    kwargs.setdefault("corner_radius", 10)
    kwargs.setdefault("height", 40)
    kwargs.setdefault("font", theme.font(13))
    kwargs.setdefault("text", text)
    kwargs.setdefault("command", command)
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
