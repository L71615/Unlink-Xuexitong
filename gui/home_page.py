# -*- coding: utf-8 -*-
"""主页：本次运行概览（左）+ 课程控制与运行日志（右）。"""
from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from gui import theme
from gui.widgets import (Card, Chip, ProgressBar, ghost_button, primary_button,
                         text_button)

LOG_FILE = Path(__file__).resolve().parent.parent / "输出记录.log"
PLACEHOLDER = "还没有运行记录，点「开始刷课」开始"
SPEEDS = ("1", "2", "3", "4", "5", "6", "8", "10", "16")


class LogView(ctk.CTkFrame):
    """等宽字体日志区，支持按级别着色。"""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", theme.PANEL)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)
        self._text = tk.Text(self, bd=0, highlightthickness=0, wrap="none",
                             bg=theme.PANEL, fg=theme.TEXT_SOFT,
                             font=(theme.MONO_FAMILIES[0], 10),
                             padx=16, pady=4, spacing1=2, spacing3=2,
                             cursor="arrow", insertwidth=0)
        self._text.grid(row=0, column=0, sticky="nsew")
        self._bar = ctk.CTkScrollbar(self, command=self._text.yview,
                                     fg_color="transparent", width=10,
                                     button_color=theme.SCROLL,
                                     button_hover_color=theme.SCROLL_HOVER)
        self._bar.grid(row=0, column=1, sticky="ns", padx=(2, 6), pady=6)
        self._text.configure(yscrollcommand=self._bar.set)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._text.tag_config("time", foreground=theme.FAINT)
        self._text.tag_config("normal", foreground=theme.TEXT_SOFT)
        self._text.tag_config("ok", foreground=theme.OK)
        self._text.tag_config("warn", foreground=theme.WARN)
        self._text.tag_config("err", foreground=theme.DANGER)
        self._text.tag_config("accent", foreground=theme.accent())
        self._text.configure(state="disabled")

        self._placeholder = None
        self._show_placeholder(True)

    # ------------------------------------------------------------------
    def _show_placeholder(self, show: bool) -> None:
        if show and self._placeholder is None:
            self._placeholder = ctk.CTkLabel(self, text=PLACEHOLDER,
                                             font=theme.font(11),
                                             text_color=theme.FAINT)
            self._placeholder.place(relx=0.5, rely=0.45, anchor="center")
        elif not show and self._placeholder is not None:
            self._placeholder.place_forget()
            self._placeholder = None

    def append(self, text: str, level: str = "normal") -> None:
        self._show_placeholder(False)
        self._text.configure(state="normal")
        self._text.insert("end", time.strftime("%H:%M:%S") + "  ", "time")
        self._text.insert("end", text.rstrip() + "\n",
                          level if level in ("ok", "warn", "err", "accent") else "normal")
        self._text.configure(state="disabled")
        self._text.see("end")

    def clear(self) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")
        self._show_placeholder(True)


class HomePage(ctk.CTkFrame):
    def __init__(self, master, on_start, on_sign, on_stop, on_clear_log,
                 on_retry=None, on_dismiss=None, on_login=None, **kwargs):
        kwargs.setdefault("fg_color", theme.BG)
        super().__init__(master, **kwargs)
        self._on_start = on_start
        self._on_sign = on_sign
        self._on_stop = on_stop
        self._on_clear_log = on_clear_log
        self._on_retry = on_retry
        self._on_dismiss = on_dismiss
        self._on_login = on_login

        self._running = False
        self._done = 0
        self._total = 0
        self._version = "-"
        self._resume = "未开始"
        self._cache = 0
        self._login_running = False
        self._course_vars: dict[str, tk.BooleanVar] = {}
        self._options_signature = None
        self._speed_value = "1"
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew",
                  padx=theme.PAGE_PAD, pady=(theme.GAP, 22))
        self._build_overview(body)
        self._build_workspace(body)

    def _build_header(self) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew", padx=theme.PAGE_PAD, pady=(22, 0))

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", anchor="s")
        ctk.CTkLabel(left, text="主页", font=theme.font(21, "bold"),
                     text_color=theme.TEXT, anchor="w").pack(anchor="w")
        ctk.CTkLabel(left, text="让机器去刷，你去做别的", font=theme.font(11),
                     text_color=theme.MUTED, anchor="w").pack(anchor="w", pady=(2, 0))

        chips = ctk.CTkFrame(row, fg_color="transparent")
        chips.pack(side="right", anchor="s", pady=(0, 2))
        self.chip_account = Chip(chips, "未配置账号")
        self.chip_account.pack(side="left", padx=(0, 8))
        self._login_btn = ghost_button(chips, "登录", self._on_login_click,
                                       icon="sign", width=82)
        self._login_btn.pack(side="left", padx=(0, 8))
        self.chip_timer = Chip(chips, "定时 未开启")
        self.chip_timer.pack(side="left")

    # ------------------------------------------------------------------
    def _build_overview(self, parent) -> None:
        card = Card(parent, width=288)
        card.pack(side="left", fill="y")
        card.pack_propagate(False)

        ctk.CTkLabel(card, text="本次运行", font=theme.font(11),
                     text_color=theme.MUTED, anchor="w").pack(
            fill="x", padx=18, pady=(16, 0))

        num = ctk.CTkFrame(card, fg_color="transparent")
        num.pack(fill="x", padx=18)
        self._num_done = ctk.CTkLabel(num, text="0", font=theme.font(34, "bold"),
                                      text_color=theme.TEXT, anchor="w")
        self._num_done.pack(side="left")
        self._num_total = ctk.CTkLabel(num, text="/ 0 任务点", font=theme.font(11),
                                       text_color=theme.FAINT, anchor="w")
        self._num_total.pack(side="left", padx=(8, 0), pady=(12, 0))

        self._bar = ProgressBar(card, height=6, fg_color=theme.BAR_TRACK)
        self._bar.pack(fill="x", padx=18, pady=(8, 16))
        self._bar.set(0)

        self._row_done = self._metric_row(card, "本次完成")
        self._row_time = self._metric_row(card, "用时")
        self._row_errors = self._metric_row(card, "异常")
        self._row_state = self._metric_row(card, "状态")

        ctk.CTkFrame(card, height=1, fg_color=theme.LINE_SOFT,
                     corner_radius=0).pack(fill="x", padx=18, pady=(14, 0))

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(14, 0))
        ctk.CTkLabel(head, text="待处理课程", font=theme.font(11),
                     text_color=theme.MUTED, anchor="w").pack(side="left")
        self._pending_count = ctk.CTkLabel(head, text="0", font=theme.font(10),
                                           text_color=theme.TEXT_SOFT,
                                           fg_color=theme.WEAK, corner_radius=6,
                                           width=22, height=18)
        self._pending_count.pack(side="right")

        self._pending_body = ctk.CTkFrame(card, fg_color="transparent")
        self._pending_body.pack(fill="x", pady=(2, 0))
        self._pending_rows = ctk.CTkFrame(self._pending_body, fg_color="transparent",
                                          width=1, height=1)
        self._pending_rows.pack(fill="x", padx=14)
        self._pending_empty = ctk.CTkLabel(
            self._pending_body, text="没有待处理的课程", font=theme.font(11),
            text_color=theme.FAINT, anchor="w")
        self._pending_empty.pack(fill="x", padx=18, pady=(6, 0))

        ctk.CTkFrame(card, fg_color="transparent", width=1,
                     height=1).pack(fill="both", expand=True)
        ctk.CTkFrame(card, height=1, fg_color=theme.LINE_SOFT,
                     corner_radius=0).pack(fill="x", padx=18)
        self._last_run = ctk.CTkLabel(card, text=self._last_run_text(),
                                      font=theme.font(10), text_color=theme.FAINT,
                                      anchor="w")
        self._last_run.pack(fill="x", padx=18, pady=12)

    def _metric_row(self, parent, key: str):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=5)
        ctk.CTkLabel(row, text=key, font=theme.font(11), text_color=theme.MUTED,
                     anchor="w").pack(side="left")
        value = ctk.CTkLabel(row, text="-", font=theme.font(11, "bold"),
                             text_color=theme.TEXT, anchor="e")
        value.pack(side="right")
        return value

    # ------------------------------------------------------------------
    def _build_workspace(self, parent) -> None:
        right = ctk.CTkFrame(parent, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True, padx=(theme.GAP, 0))

        ctrl = Card(right)
        ctrl.pack(fill="x")

        row = ctk.CTkFrame(ctrl, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=14)

        btns = ctk.CTkFrame(row, fg_color="transparent")
        btns.pack(side="right")
        self._start_btn = primary_button(btns, "开始刷课", self._on_start,
                                         icon="play", width=104)
        self._start_btn.pack(side="left")
        self._sign_btn = ghost_button(btns, "自动签到", self._on_sign,
                                      icon="sign", width=100)
        self._sign_btn.pack(side="left", padx=8)
        self._stop_btn = text_button(btns, "结束", self._on_stop, color=theme.DANGER,
                                     height=38, width=48)
        self._stop_btn.pack(side="left")
        self._stop_btn.configure(state="disabled")

        self._ctrl_info = ctk.CTkFrame(row, fg_color="transparent")
        self._ctrl_info.pack(side="left", fill="x", expand=True)

        self._state_dot = ctk.CTkLabel(self._ctrl_info, text="●", font=theme.font(8),
                                       text_color=theme.FAINT, width=8)
        self._state_dot.pack(side="left", pady=(2, 0))
        self._name_font = theme.font(14, "bold")
        self._name_full = "—"
        self._course_name = ctk.CTkLabel(self._ctrl_info, text="—", font=self._name_font,
                                         text_color=theme.TEXT, anchor="w")
        self._course_name.pack(side="left", padx=(9, 0))
        self._task_type = ctk.CTkLabel(self._ctrl_info, text="章节", font=theme.font(9),
                                       text_color=theme.MUTED, fg_color=theme.WEAK,
                                       corner_radius=6, padx=7, pady=2)
        self._task_type.pack(side="left", padx=(10, 0))
        self._state_pill = ctk.CTkLabel(self._ctrl_info, text="未开始", font=theme.font(9),
                                        text_color=theme.MUTED, fg_color=theme.WEAK,
                                        corner_radius=6, padx=7, pady=2)
        self._state_pill.pack(side="left", padx=(6, 0))
        self._ctrl_info.bind("<Configure>", self._on_info_resize)

        pick = Card(right)
        pick.pack(fill="x", pady=(theme.GAP, 0))

        head = ctk.CTkFrame(pick, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(head, text="本次任务", font=theme.font(12, "bold"),
                     text_color=theme.TEXT).pack(side="left")
        self._course_count = ctk.CTkLabel(head, text="未选课程", font=theme.font(10),
                                          text_color=theme.FAINT)
        self._course_count.pack(side="left", padx=(8, 0))
        text_button(head, "清空", self._clear_courses, height=24).pack(side="right")
        text_button(head, "全选", self._select_all_courses, height=24).pack(
            side="right", padx=(0, 6))
        self._speed_box = ctk.CTkComboBox(head, values=list(SPEEDS), width=72,
                                          state="readonly", font=theme.font(10),
                                          dropdown_font=theme.font(10))
        self._speed_box.set("1")
        self._speed_box.pack(side="right", padx=(0, 14))
        ctk.CTkLabel(head, text="倍速", font=theme.font(10),
                     text_color=theme.MUTED).pack(side="right", padx=(0, 6))

        ctk.CTkFrame(pick, height=1, fg_color=theme.LINE_SOFT,
                     corner_radius=0).pack(fill="x")
        self._course_box = ctk.CTkScrollableFrame(pick, height=104, fg_color="transparent",
                                                  scrollbar_button_color=theme.LINE,
                                                  scrollbar_button_hover_color=theme.MUTED)
        self._course_box.pack(fill="x", padx=10, pady=(6, 10))
        self._course_box.grid_columnconfigure(0, weight=1)
        self._course_box.grid_columnconfigure(1, weight=1)
        self.set_course_options([], [])

        log_card = Card(right)
        log_card.pack(fill="both", expand=True, pady=(theme.GAP, 0))

        head = ctk.CTkFrame(log_card, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(12, 8))
        ctk.CTkLabel(head, text="运行日志", font=theme.font(12, "bold"),
                     text_color=theme.TEXT).pack(side="left")
        self._live_dot = ctk.CTkLabel(head, text="●", font=theme.font(7),
                                      text_color=theme.FAINT, width=8)
        self._live_dot.pack(side="left", padx=(9, 4))
        ctk.CTkLabel(head, text="实时", font=theme.font(10),
                     text_color=theme.FAINT).pack(side="left")
        self._quick = ctk.CTkLabel(head, text="", font=theme.font(10),
                                   text_color=theme.FAINT)
        self._quick.pack(side="left", padx=(14, 0))
        text_button(head, "清空", self._on_clear_log, height=24).pack(side="right")

        ctk.CTkFrame(log_card, height=1, fg_color=theme.LINE_SOFT,
                     corner_radius=0).pack(fill="x")
        self.log = LogView(log_card)
        self.log.pack(fill="both", expand=True, padx=2, pady=(0, 8))
        self._refresh_quick()
        self._sync_state()

    # ------------------------------------------------------------------
    @staticmethod
    def _last_run_text() -> str:
        try:
            stamp = LOG_FILE.stat().st_mtime
        except OSError:
            return "还没有运行记录"
        return "上次运行  " + time.strftime("%m月%d日 %H:%M",
                                          time.localtime(stamp))

    def _refresh_quick(self) -> None:
        if not hasattr(self, "_quick"):
            return
        resume = self._resume if len(self._resume) <= 14 else self._resume[:13] + "…"
        self._quick.configure(
            text=f"版本 {self._version}  ·  断点 {resume}  ·  缓存 {self._cache} 条")

    def _sync_state(self) -> None:
        if not hasattr(self, "_state_pill"):
            return
        if self._running:
            text, color, bg = "进行中", theme.accent(), theme.accent_weak()
        elif self._total and self._done >= self._total:
            text, color, bg = "已完成", theme.OK, theme.OK_WEAK
        else:
            text, color, bg = "未开始", theme.MUTED, theme.WEAK
        self._state_pill.configure(text=text, text_color=color, fg_color=bg)
        self._state_dot.configure(text_color=color)
        self._row_state.configure(text=text,
                                  text_color=theme.OK if text == "已完成"
                                  else (theme.accent() if self._running else theme.TEXT))

    def _fit(self, name: str, limit: int) -> str:
        name = name or "—"
        return name if len(name) <= limit else name[: limit - 1] + "…"

    def _ellipsize(self, text: str, px: int) -> str:
        text = text or "—"
        if self._name_font.measure(text) <= px:
            return text
        cut = text
        while cut and self._name_font.measure(cut + "…") > px:
            cut = cut[:-1]
        return (cut + "…") if cut else "…"

    def _on_info_resize(self, _event=None) -> None:
        if not hasattr(self, "_ctrl_info"):
            return
        fixed = (8 + 9 + 10 + 6 + 6
                 + self._task_type.winfo_reqwidth()
                 + self._state_pill.winfo_reqwidth())
        avail = self._ctrl_info.winfo_width() - fixed
        if avail < 32:
            avail = 32
        text = self._ellipsize(self._name_full, avail)
        if self._course_name.cget("text") != text:
            self._course_name.configure(text=text)

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------
    def set_account_status(self, text: str, state: str = "idle") -> None:
        """顶部账号胶囊：state = ok / warn / idle。"""
        color = {"ok": theme.OK, "warn": theme.DANGER}.get(state, theme.FAINT)
        self.chip_account.set_state(text or "未配置账号", color=color)

    def set_login_running(self, running: bool) -> None:
        self._login_running = running
        if running:
            self._login_btn.configure(state="disabled", text="登录中…")
        else:
            self._login_btn.configure(state="disabled" if self._running else "normal",
                                      text="登录")

    def _on_login_click(self) -> None:
        if self._login_running or self._on_login is None:
            return
        self._on_login()

    def set_course_options(self, names, selected=None) -> None:
        """刷新课程勾选列表；names 没变就不重建控件（避免定时刷新时闪烁）。"""
        names = [name for name in (names or []) if name]
        signature = tuple(names)
        chosen = set(selected or [])
        if signature == self._options_signature:
            # 列表没变，只同步勾选状态（比如单门重试后回到原课程列表）
            if chosen:
                for name, var in self._course_vars.items():
                    var.set(name in chosen)
                self._update_course_count()
            return
        self._options_signature = signature
        for child in self._course_box.winfo_children():
            child.destroy()
        self._course_vars = {}
        if not names:
            ctk.CTkLabel(self._course_box, text="点上方「登录」读取课程列表",
                         font=theme.font(10), text_color=theme.FAINT, anchor="w").grid(
                row=0, column=0, columnspan=2, sticky="w", padx=8, pady=6)
            self._update_course_count()
            return
        chosen = set(selected or [])
        for index, name in enumerate(names):
            var = tk.BooleanVar(value=(not chosen) or (name in chosen))
            self._course_vars[name] = var
            box = ctk.CTkCheckBox(self._course_box, text=self._fit(name, 15), variable=var,
                                  font=theme.font(11), checkbox_width=16,
                                  checkbox_height=16, command=self._update_course_count)
            box.grid(row=index // 2, column=index % 2, sticky="w", padx=8, pady=3)
        self._update_course_count()

    def get_courses(self) -> list[str]:
        return [name for name, var in self._course_vars.items() if var.get()]

    def get_speed(self) -> str:
        try:
            value = str(self._speed_box.get()).strip()
        except Exception:
            return "1"
        return value if value in SPEEDS else "1"

    def set_speed(self, value) -> None:
        value = str(value or "1").strip()
        if value not in SPEEDS:
            value = "1"
        self._speed_value = value
        if self._speed_box.get() != value:
            self._speed_box.set(value)

    def _select_all_courses(self) -> None:
        for var in self._course_vars.values():
            var.set(True)
        self._update_course_count()

    def _clear_courses(self) -> None:
        for var in self._course_vars.values():
            var.set(False)
        self._update_course_count()

    def _update_course_count(self) -> None:
        total = len(self._course_vars)
        if not total:
            self._course_count.configure(text="未选课程")
        else:
            self._course_count.configure(text=f"已选 {len(self.get_courses())}/{total}")

    def set_pending(self, items) -> None:
        """items: [(课程名, 状态文字), ...]"""
        for child in self._pending_rows.winfo_children():
            child.destroy()
        items = list(items or [])
        self._pending_count.configure(text=str(len(items)))
        if not items:
            self._pending_empty.pack(fill="x", padx=18, pady=(6, 0))
            return
        self._pending_empty.pack_forget()
        for course, status in items:
            row = ctk.CTkFrame(self._pending_rows, fg_color="transparent")
            row.pack(fill="x", padx=(4, 4), pady=3)
            ctk.CTkLabel(row, text=self._fit(course, 9), font=theme.font(10, "bold"),
                         text_color=theme.TEXT, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=status, font=theme.font(9),
                         text_color=theme.WARN).pack(side="left", padx=(6, 0))
            if self._on_dismiss is not None:
                text_button(row, "忽略", lambda c=course: self._on_dismiss(c),
                            height=22).pack(side="right")
            if self._on_retry is not None:
                ghost_button(row, "重试", lambda c=course: self._on_retry(c),
                             height=22, width=44, font=theme.font(9)).pack(
                    side="right", padx=(0, 4))

    def set_course(self, name: str, done: int = 0, total: int = 0,
                   task_type: str = "章节") -> None:
        self._done, self._total = int(done), int(total)
        self._name_full = name or "—"
        self._task_type.configure(text=task_type or "章节")
        self._on_info_resize()
        if total:
            self._bar.set(min(max(done / total, 0.0), 1.0))
        else:
            self._bar.set(0)
        self._num_done.configure(text=str(self._done))
        self._num_total.configure(text=f"/ {self._total} 任务点")
        self._sync_state()

    def set_running(self, running: bool) -> None:
        self._running = running
        self._start_btn.configure(
            state="disabled" if running else "normal",
            fg_color=theme.shade(theme.accent(), 1.35) if running else theme.accent())
        self._stop_btn.configure(state="normal" if running else "disabled")
        self._live_dot.configure(text_color=theme.OK if running else theme.FAINT)
        state = "disabled" if running else "normal"
        self._speed_box.configure(state="readonly" if running else "readonly")
        for child in self._course_box.winfo_children():
            try:
                child.configure(state=state)
            except Exception:
                pass
        if not self._login_running:
            self._login_btn.configure(state=state, text="登录")
        self._sync_state()

    def set_chips(self, timer_on: bool, timer_text: str) -> None:
        self.chip_timer.set_state(timer_text, on=timer_on)

    def set_metrics(self, done: int | None = None, elapsed: int | None = None,
                    errors: int | None = None) -> None:
        if done is not None:
            self._row_done.configure(text=str(done))
        if elapsed is not None:
            hours, rest = divmod(int(elapsed), 3600)
            minutes, seconds = divmod(rest, 60)
            self._row_time.configure(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        if errors is not None:
            self._row_errors.configure(text=str(errors),
                                       text_color=theme.WARN if errors else theme.TEXT)

    def set_version(self, version: str) -> None:
        self._version = version
        self._refresh_quick()

    def set_resume(self, text: str) -> None:
        self._resume = text
        self._refresh_quick()

    def set_cache(self, count: int) -> None:
        self._cache = count
        self._refresh_quick()
