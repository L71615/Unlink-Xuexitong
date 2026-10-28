# -*- coding: utf-8 -*-
"""定时刷课设置窗口。"""
from __future__ import annotations

import re

import customtkinter as ctk
from tkinter import messagebox

from gui import theme
from gui.widgets import Hint, ghost_button, primary_button


class TimerWindow:
    def __init__(self, root, on_set, on_cancel):
        self.root = root
        self.on_set = on_set
        self.on_cancel = on_cancel
        self._window = None

    def open(self, start_time: str, end_time: str) -> None:
        if self._window is not None and self._window.winfo_exists():
            self._window.lift()
            return

        win = ctk.CTkToplevel(self.root)
        self._window = win
        win.title("定时刷课")
        win.geometry("380x270")
        win.resizable(False, False)
        win.configure(fg_color=theme.BG)
        win.transient(self.root)
        win.after(120, win.grab_set)
        win.after(150, win.lift)

        card = ctk.CTkFrame(win, fg_color=theme.PANEL, corner_radius=14,
                            border_width=1, border_color=theme.LINE)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(card, text="每天在这个时间段自动刷课",
                     font=theme.font(11), text_color=theme.MUTED,
                     anchor="w").grid(row=0, column=0, columnspan=2, sticky="w",
                                      padx=18, pady=(16, 10))

        ctk.CTkLabel(card, text="开始", font=theme.font(11),
                     text_color=theme.MUTED).grid(row=1, column=0, sticky="w",
                                                  padx=(18, 10), pady=6)
        start_entry = ctk.CTkEntry(card, font=theme.font(11.5), height=34,
                                   corner_radius=8, border_width=1,
                                   border_color=theme.LINE, fg_color=theme.PANEL,
                                   text_color=theme.TEXT)
        start_entry.grid(row=1, column=1, sticky="ew", padx=(0, 18), pady=6)
        start_entry.insert(0, start_time)

        ctk.CTkLabel(card, text="结束", font=theme.font(11),
                     text_color=theme.MUTED).grid(row=2, column=0, sticky="w",
                                                  padx=(18, 10), pady=6)
        end_entry = ctk.CTkEntry(card, font=theme.font(11.5), height=34,
                                 corner_radius=8, border_width=1,
                                 border_color=theme.LINE, fg_color=theme.PANEL,
                                 text_color=theme.TEXT)
        end_entry.grid(row=2, column=1, sticky="ew", padx=(0, 18), pady=6)
        end_entry.insert(0, end_time)

        Hint(card, "格式 HH:MM:SS，例如 04:00:00").grid(
            row=3, column=0, columnspan=2, sticky="w", padx=18, pady=(2, 8))

        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.grid(row=4, column=0, columnspan=2, sticky="e", padx=14, pady=(4, 14))
        ghost_button(buttons, "关闭定时", self._cancel, height=34).pack(side="left", padx=(0, 8))
        primary_button(buttons, "开启定时",
                       lambda: self._set(win, start_entry.get().strip(),
                                         end_entry.get().strip()),
                       height=34).pack(side="left")

    def _set(self, window, start_str: str, end_str: str) -> None:
        pattern = r"^([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$"
        if not re.match(pattern, start_str) or not re.match(pattern, end_str):
            messagebox.showerror("格式不对", "时间要写成 HH:MM:SS，例如 04:00:00")
            return
        if start_str == end_str:
            messagebox.showerror("格式不对", "开始时间和结束时间不能一样")
            return
        self.on_set(start_str, end_str)
        window.destroy()

    def _cancel(self) -> None:
        self.on_cancel()
        if self._window is not None:
            self._window.destroy()
