# -*- coding: utf-8 -*-
"""左侧导航栏。"""
from __future__ import annotations

import customtkinter as ctk

from gui import theme
from gui.widgets import Icon, NavItem

GROUPS = (
    ("学习", (
        ("home", "主页"),
        ("log", "刷课日志"),
        ("score", "测试成绩"),
        ("bank", "题库查询"),
    )),
    ("其他", (
        ("error", "报错日志"),
        ("settings", "设置"),
        ("help", "帮助"),
    )),
)


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, version: str, on_select, name: str = "课业助手", **kwargs):
        kwargs.setdefault("width", 224)
        kwargs.setdefault("fg_color", theme.PANEL)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)
        self.pack_propagate(False)
        self.grid_propagate(False)
        self._on_select = on_select
        self._name = name
        self._items: dict[str, NavItem] = {}

        # 右侧 1px 分隔线
        ctk.CTkFrame(self, width=1, fg_color=theme.LINE, corner_radius=0).place(
            relx=1.0, x=-1, y=0, relheight=1.0)

        self._build_brand(version)
        for group_name, items in GROUPS:
            self._build_group(group_name, items)
        self._build_spacer()
        self._build_user()

    # ------------------------------------------------------------------
    def _build_brand(self, version: str) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(20, 14))

        logo = ctk.CTkFrame(row, width=28, height=28, corner_radius=8,
                            fg_color=theme.accent())
        logo.pack(side="left")
        logo.pack_propagate(False)
        ctk.CTkLabel(logo, text="课", font=theme.font(12, "bold"),
                     text_color="#FFFFFF").place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(row, text=self._name, font=theme.font(13, "bold"),
                     text_color=theme.TEXT).pack(side="left", padx=(10, 0))
        ctk.CTkLabel(row, text=version, font=theme.font(10),
                     text_color=theme.FAINT).pack(side="right")

    def _build_group(self, name: str, items) -> None:
        ctk.CTkLabel(self, text=name, font=theme.font(10),
                     text_color=theme.FAINT, anchor="w").pack(
            fill="x", padx=(26, 0), pady=(8, 5))
        for key, text in items:
            item = NavItem(self, key, text, command=self._on_select)
            item.pack(fill="x", padx=14, pady=1)
            self._items[key] = item

    def _build_spacer(self) -> None:
        self._spacer = ctk.CTkFrame(self, fg_color="transparent", width=1, height=1)
        self._spacer.pack(fill="both", expand=True)

    def _build_user(self) -> None:
        card = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=12,
                            border_width=1, border_color=theme.LINE)
        card.pack(fill="x", padx=14, pady=(0, 16))

        avatar = ctk.CTkFrame(card, width=30, height=30, corner_radius=15,
                              fg_color="#E9EDF5")
        avatar.pack(side="left", padx=(10, 9), pady=10)
        avatar.pack_propagate(False)
        self._avatar_text = ctk.CTkLabel(avatar, text="未", font=theme.font(11, "bold"),
                                         text_color="#5B6472")
        self._avatar_text.place(relx=0.5, rely=0.5, anchor="center")

        text_col = ctk.CTkFrame(card, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True, pady=10)
        self._user_state = ctk.CTkLabel(text_col, text="未登录", font=theme.font(11, "bold"),
                                        text_color=theme.TEXT, anchor="w")
        self._user_state.pack(fill="x")
        self._user_phone = ctk.CTkLabel(text_col, text="请先完成设置", font=theme.font(10),
                                        text_color=theme.MUTED, anchor="w")
        self._user_phone.pack(fill="x", pady=(1, 0))

    # ------------------------------------------------------------------
    def set_active(self, key: str) -> None:
        for name, item in self._items.items():
            item.set_active(name == key)

    def set_user(self, phone: str) -> None:
        if phone:
            masked = phone if len(phone) <= 4 else f"{phone[:3]}****{phone[-4:]}"
            self._user_state.configure(text="已登录")
            self._user_phone.configure(text=masked)
            self._avatar_text.configure(text=phone[0])
        else:
            self._user_state.configure(text="未登录")
            self._user_phone.configure(text="请先完成设置")
            self._avatar_text.configure(text="未")
