# -*- coding: utf-8 -*-
"""主页：当前课程、本次运行数据、运行日志。"""
from __future__ import annotations

import tkinter as tk
import time

import customtkinter as ctk

from gui import theme
from gui.widgets import (Card, Chip, Hint, KVRow, ProgressBar, SectionTitle,
                         ghost_button, primary_button, text_button)


class LogView(ctk.CTkFrame):
    """等宽字体日志区，支持按级别着色。"""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        self._text = tk.Text(self, bd=0, highlightthickness=0, wrap="none",
                             bg=theme.PANEL, fg=theme.TEXT_SOFT,
                             font=(theme.MONO_FAMILIES[0], 10),
                             padx=0, pady=0, spacing1=2, spacing3=2)
        self._text.grid(row=0, column=0, sticky="nsew")
        self._bar = ctk.CTkScrollbar(self, command=self._text.yview,
                                     fg_color="transparent", width=10)
        self._bar.grid(row=0, column=1, sticky="ns", padx=(6, 0))
        self._text.configure(yscrollcommand=self._bar.set)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._text.tag_config("time", foreground=theme.FAINT)
        self._text.tag_config("normal", foreground=theme.TEXT_SOFT)
        self._text.tag_config("ok", foreground=theme.OK)
        self._text.tag_config("warn", foreground=theme.WARN)
        self._text.tag_config("err", foreground=theme.DANGER)
        self._text.configure(state="disabled")

        self._placeholder = ctk.CTkLabel(
            self, text="还没有运行记录，点「开始刷课」开始",
            font=theme.font(11), text_color=theme.FAINT)
        self._placeholder.place(relx=0.5, rely=0.45, anchor="center")

    def append(self, text: str, level: str = "normal") -> None:
        if self._placeholder is not None:
            self._placeholder.place_forget()
            self._placeholder = None
        self._text.configure(state="normal")
        stamp = time.strftime("%H:%M:%S")
        self._text.insert("end", f"{stamp}  ", "time")
        self._text.insert("end", text.rstrip() + "\n", level)
        self._text.configure(state="disabled")
        self._text.see("end")

    def clear(self) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")
        if self._placeholder is None:
            self._placeholder = ctk.CTkLabel(
                self, text="还没有运行记录，点「开始刷课」开始",
                font=theme.font(11), text_color=theme.FAINT)
            self._placeholder.place(relx=0.5, rely=0.45, anchor="center")


class HomePage(ctk.CTkFrame):
    def __init__(self, master, on_start, on_sign, on_stop, on_clear_log, **kwargs):
        kwargs.setdefault("fg_color", theme.BG)
        super().__init__(master, **kwargs)
        self._on_start = on_start
        self._on_sign = on_sign
        self._on_stop = on_stop
        self._on_clear_log = on_clear_log
        self._running = False
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_cards()
        self._build_log()

    def _build_header(self) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew", padx=30, pady=(24, 0))

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", anchor="s")
        ctk.CTkLabel(left, text="主页", font=theme.font(20, "bold"),
                     text_color=theme.TEXT, anchor="w").pack(anchor="w")
        ctk.CTkLabel(left, text="让机器去刷，你去做别的", font=theme.font(11),
                     text_color=theme.MUTED, anchor="w").pack(anchor="w", pady=(3, 0))

        chips = ctk.CTkFrame(row, fg_color="transparent")
        chips.pack(side="right", anchor="s", pady=(0, 2))
        self.chip_timer = Chip(chips, "定时 未开启")
        self.chip_timer.pack(side="left", padx=(0, 8))
        self.chip_multi = Chip(chips, "多端 关闭")
        self.chip_multi.pack(side="left")

    def _build_cards(self) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=30, pady=(16, 0))
        row.grid_columnconfigure(0, weight=16)
        row.grid_columnconfigure(1, weight=10)
        row.grid_rowconfigure(0, weight=1)

        self._build_course_card(row).grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self._build_side_cards(row).grid(row=0, column=1, sticky="nsew")

    def _build_course_card(self, master) -> Card:
        card = Card(master)
        card.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 0))
        SectionTitle(head, "当前课程").pack(side="left")

        self._course_meta = Hint(card, "尚未选择课程")
        self._course_meta.configure(font=theme.font(11))
        self._course_meta.grid(row=1, column=0, sticky="w", padx=20, pady=(4, 0))

        name_row = ctk.CTkFrame(card, fg_color="transparent")
        name_row.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 0))
        self._course_name = ctk.CTkLabel(name_row, text="—", font=theme.font(17, "bold"),
                                         text_color=theme.TEXT, anchor="w")
        self._course_name.pack(side="left")
        self._course_tag = ctk.CTkLabel(name_row, text="未开始", font=theme.font(10, "bold"),
                                        text_color=theme.MUTED, fg_color=theme.LINE_SOFT,
                                        corner_radius=6, width=54, height=20)
        self._course_tag.pack(side="left", padx=(8, 0))

        self._bar = ProgressBar(card, height=8)
        self._bar.grid(row=3, column=0, sticky="ew", padx=20, pady=(14, 0))
        self._bar.set(0)

        self._meta = Hint(card, "")
        self._meta.grid(row=4, column=0, sticky="w", padx=20, pady=(8, 0))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=5, column=0, sticky="w", padx=20, pady=(16, 18))
        self._start_btn = primary_button(actions, "开始刷课", self._on_start, icon="play")
        self._start_btn.pack(side="left")
        self._sign_btn = ghost_button(actions, "自动签到", self._on_sign, icon="sign")
        self._sign_btn.pack(side="left", padx=(10, 0))
        self._stop_btn = text_button(actions, "结束", self._on_stop, color=theme.DANGER)
        self._stop_btn.pack(side="left", padx=(6, 0))
        self._stop_btn.configure(state="disabled")
        return card

    def _build_side_cards(self, master) -> ctk.CTkFrame:
        col = ctk.CTkFrame(master, fg_color="transparent")
        col.grid_columnconfigure(0, weight=1)
        col.grid_rowconfigure(0, weight=1)
        col.grid_rowconfigure(1, weight=1)

        run_card = Card(col)
        run_card.grid(row=0, column=0, sticky="nsew", pady=(0, 16))
        SectionTitle(run_card, "本次运行").pack(anchor="w", padx=18, pady=(16, 2))
        self._kv_done = KVRow(run_card, "已完成任务点", "0")
        self._kv_done.pack(fill="x", padx=18, pady=(8, 0))
        self._kv_time = KVRow(run_card, "已运行", "00:00:00")
        self._kv_time.pack(fill="x", padx=18, pady=(8, 0))
        self._kv_error = KVRow(run_card, "异常次数", "0")
        self._kv_error.pack(fill="x", padx=18, pady=(8, 14))

        quick = Card(col)
        quick.grid(row=1, column=0, sticky="nsew")
        SectionTitle(quick, "快捷").pack(anchor="w", padx=18, pady=(16, 2))
        self._kv_version = KVRow(quick, "版本", "-")
        self._kv_version.pack(fill="x", padx=18, pady=(8, 0))
        self._kv_cache = KVRow(quick, "题目缓存", "0 条")
        self._kv_cache.pack(fill="x", padx=18, pady=(8, 14))
        return col

    def _build_log(self) -> None:
        card = Card(self)
        card.grid(row=2, column=0, sticky="nsew", padx=30, pady=(16, 22))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 4))
        SectionTitle(head, "运行日志").pack(side="left")
        Hint(head, "自动滚动").pack(side="right")
        text_button(head, "清空", self._on_clear_log, height=26).pack(
            side="right", padx=(0, 10))

        self.log = LogView(card)
        self.log.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 14))

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------
    def set_course(self, name: str, done: int = 0, total: int = 0,
                   task_type: str = "章节") -> None:
        self._course_name.configure(text=name or "—")
        self._course_meta.configure(text=f"{name} · {task_type}" if name else "尚未选择课程")
        if total:
            ratio = min(max(done / total, 0.0), 1.0)
            self._bar.set(ratio)
            self._meta.configure(text=f"任务点 {done} / {total}")
        else:
            self._bar.set(0)
            self._meta.configure(text="")
        self._course_tag.configure(
            text="进行中" if self._running else "未开始",
            text_color=theme.accent() if self._running else theme.MUTED,
            fg_color=theme.accent_weak() if self._running else theme.LINE_SOFT)

    def set_running(self, running: bool) -> None:
        self._running = running
        self._start_btn.configure(state="disabled" if running else "normal",
                                  fg_color=theme.shade(theme.accent(), 1.35) if running
                                  else theme.accent())
        self._stop_btn.configure(state="normal" if running else "disabled")
        self._course_tag.configure(
            text="进行中" if running else "未开始",
            text_color=theme.accent() if running else theme.MUTED,
            fg_color=theme.accent_weak() if running else theme.LINE_SOFT)

    def set_chips(self, timer_on: bool, timer_text: str, multi_on: bool) -> None:
        self.chip_timer.set_state(timer_text, on=timer_on)
        self.chip_multi.set_state("多端 开启" if multi_on else "多端 关闭", on=multi_on)

    def set_metrics(self, done: int | None = None, elapsed: int | None = None,
                    errors: int | None = None) -> None:
        if done is not None:
            self._kv_done.set(str(done))
        if elapsed is not None:
            hours, rest = divmod(int(elapsed), 3600)
            minutes, seconds = divmod(rest, 60)
            self._kv_time.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        if errors is not None:
            self._kv_error.set(str(errors))

    def set_version(self, version: str) -> None:
        self._kv_version.set(version)

    def set_cache(self, count: int) -> None:
        self._kv_cache.set(f"{count} 条")
