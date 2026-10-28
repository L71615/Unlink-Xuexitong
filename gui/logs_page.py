# -*- coding: utf-8 -*-
"""刷课日志 / 测试成绩 / 题库查询 / 报错日志 / 帮助 页面。"""
from __future__ import annotations

import os
import pickle
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from core import resume as resume_store
from gui import theme
from gui.widgets import (Card, Hint, PageHeader, ProgressBar, SectionTitle,
                         ghost_button, text_button)


def _entry(parent, **kwargs):
    kwargs.setdefault("fg_color", theme.PANEL)
    kwargs.setdefault("border_color", theme.LINE)
    kwargs.setdefault("border_width", 1)
    kwargs.setdefault("corner_radius", 8)
    kwargs.setdefault("height", 34)
    kwargs.setdefault("font", theme.font(12))
    kwargs.setdefault("text_color", theme.TEXT)
    return ctk.CTkEntry(parent, **kwargs)


class RecordPage(ctk.CTkFrame):
    """刷课日志 / 测试成绩共用的记录页。"""

    def __init__(self, master, config, kind: str, title: str, subtitle: str, **kwargs):
        kwargs.setdefault("fg_color", theme.BG)
        super().__init__(master, **kwargs)
        self.config = config
        self.kind = kind
        self._title = title
        self._subtitle = subtitle
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        PageHeader(self, self._title, self._subtitle).grid(
            row=0, column=0, sticky="ew", padx=30, pady=(24, 0))

        bar = Card(self)
        bar.grid(row=1, column=0, sticky="ew", padx=30, pady=(16, 0))
        bar.grid_columnconfigure(0, weight=1)

        self.course = ctk.CTkComboBox(
            bar, values=[], font=theme.font(12), height=34, corner_radius=8,
            border_width=1, border_color=theme.LINE, fg_color=theme.PANEL,
            button_color=theme.PANEL, button_hover_color=theme.LINE_SOFT,
            dropdown_fg_color=theme.PANEL, dropdown_hover_color=theme.LINE_SOFT,
            text_color=theme.TEXT, command=lambda _v: self.refresh())
        self.course.grid(row=0, column=0, sticky="ew", padx=(16, 10), pady=(14, 8))

        ghost_button(bar, "查询", self.refresh, icon="search",
                     height=34, width=88).grid(row=0, column=1, padx=(0, 8), pady=(14, 8))
        text_button(bar, "重置断点", self._reset_resume, color=theme.MUTED,
                    height=34).grid(row=0, column=2, padx=(0, 4), pady=(14, 8))
        text_button(bar, "删除记录", self._delete, color=theme.DANGER,
                    height=34).grid(row=0, column=3, padx=(0, 12), pady=(14, 8))

        self.progress_wrap = ctk.CTkFrame(bar, fg_color="transparent")
        self.progress_wrap.grid(row=1, column=0, columnspan=4, sticky="ew",
                                padx=16, pady=(0, 14))
        self.progress_label = Hint(self.progress_wrap, "", size=11)
        self.progress_label.pack(side="left", padx=(0, 10))
        self.progress = ProgressBar(self.progress_wrap, height=6)
        self.progress.pack(side="left", fill="x", expand=True)
        self.progress.set(0)
        if self.kind != "刷课":
            self.progress_wrap.grid_remove()

        card = Card(self)
        card.grid(row=2, column=0, sticky="nsew", padx=30, pady=(16, 22))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)

        self.text = ctk.CTkTextbox(card, font=theme.font(11), fg_color=theme.PANEL,
                                   border_width=0, corner_radius=0, wrap="word",
                                   text_color=theme.TEXT_SOFT)
        self.text.grid(row=0, column=0, sticky="nsew", padx=16, pady=14)
        self.text.configure(state="disabled")

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        account = self.config.get_account() or self.config.load_account()
        courses = self.config.load_courses(account.get("phone_number", ""))
        if courses:
            current = self.course.get()
            self.course.configure(values=tuple(courses))
            if current not in courses:
                self.course.set(courses[0])
        else:
            self.course.configure(values=("",))
            self.course.set("")

        course = self.course.get()
        path = fr'task\record\《{course}》的{self.kind}记录.txt'
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = f"暂未查询到《{course}》的{self.kind}记录"

        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", content)
        self.text.configure(state="disabled")

        if self.kind == "刷课":
            self._refresh_progress(course)

    def _refresh_progress(self, course: str) -> None:
        try:
            data = self.config.get_course_process()
            done, total = data.get(course, (0, 0))
        except Exception:
            done, total = 0, 0

        account = self.config.get_account() or self.config.load_account()
        info = resume_store.snapshot(account.get("phone_number", "")).get(course, {})
        state = {"done": "已完成", "running": "上次中断",
                 "error": "上次出错"}.get(info.get("status", ""), "")
        chapter = info.get("chapter", "")
        detail = state or chapter or "未开始"
        suffix = f" · 断点：{detail}"

        if total:
            self.progress.set(min(max(done / total, 0), 1))
            self.progress_label.configure(
                text=f"进度 {done} / {total}（{done / total * 100:.1f}%）{suffix}")
        else:
            self.progress.set(0)
            self.progress_label.configure(text=f"暂无进度数据{suffix}")

    def _reset_resume(self) -> None:
        account = self.config.get_account() or self.config.load_account()
        phone = account.get("phone_number", "")
        course = self.course.get()
        if not course:
            return
        if not messagebox.askyesno(
                "重置断点", f"重置《{course}》的断点？\n下次会重新从这门课的开头刷。"):
            return
        resume_store.reset(phone, course)
        messagebox.showinfo("已重置", "断点已清除")
        self.refresh()

    def _delete(self) -> None:
        course = self.course.get()
        path = fr'task\record\《{course}》的{self.kind}记录.txt'
        if not os.path.exists(path):
            messagebox.showwarning("提示", f"找不到《{course}》的{self.kind}记录")
            return
        if messagebox.askyesno("确认", "确定删除这份记录吗？删除后无法恢复"):
            os.remove(path)
            messagebox.showinfo("提示", "记录已删除")
            self.refresh()


class QuestionBankPage(ctk.CTkFrame):
    """题库查询：展示本地缓存的题目与答案。"""

    def __init__(self, master, config, **kwargs):
        kwargs.setdefault("fg_color", theme.BG)
        super().__init__(master, **kwargs)
        self.config = config
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = PageHeader(self, "题库查询", "答题时命中过的题目会缓存在本地")
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(24, 0))
        ghost_button(header.right, "刷新", self.refresh).pack(side="right", padx=(8, 0))
        ghost_button(header.right, "清空缓存", self._clear, icon="delete").pack(side="right")

        self.summary = Hint(self, "")
        self.summary.grid(row=1, column=0, sticky="w", padx=30, pady=(12, 0))

        card = Card(self)
        card.grid(row=2, column=0, sticky="nsew", padx=30, pady=(10, 22))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)
        self.text = ctk.CTkTextbox(card, font=theme.font(11), fg_color=theme.PANEL,
                                   border_width=0, corner_radius=0, wrap="word",
                                   text_color=theme.TEXT_SOFT)
        self.text.grid(row=0, column=0, sticky="nsew", padx=16, pady=14)
        self.text.configure(state="disabled")

    def _cache_files(self):
        folder = os.path.join("task", "record")
        if not os.path.isdir(folder):
            return []
        return [os.path.join(folder, name) for name in os.listdir(folder)
                if name.endswith(".pkl") and "ques1" in name]

    def refresh(self) -> None:
        files = self._cache_files()
        lines = []
        for path in files:
            try:
                with open(path, "rb") as f:
                    data = pickle.load(f)["value"]
            except Exception:
                continue
            lines.append(f"问题：{data.get('question', '')}\n"
                         f"{data.get('options', '')}\n"
                         f"答案：{data.get('answer', '')}\n")
        self.summary.configure(text=f"共 {len(lines)} 条缓存" if lines else "暂无缓存的题目")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", "\n".join(lines) or "暂无缓存的题目")
        self.text.configure(state="disabled")

    def _clear(self) -> None:
        files = self._cache_files()
        if not files:
            messagebox.showinfo("提示", "没有需要清理的缓存")
            return
        if not messagebox.askyesno("确认", f"确定清空 {len(files)} 条题目缓存吗？"):
            return
        for path in files:
            try:
                os.remove(path)
            except OSError:
                pass
        self.refresh()


class ErrorPage(ctk.CTkFrame):
    """报错日志。"""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", theme.BG)
        super().__init__(master, **kwargs)
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = PageHeader(self, "报错日志", "程序运行中的异常会记录在这里")
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(24, 0))
        ghost_button(header.right, "刷新", self.refresh).pack(side="right", padx=(8, 0))
        ghost_button(header.right, "清空", self._clear, icon="delete").pack(side="right")

        self.summary = Hint(self, "")
        self.summary.grid(row=1, column=0, sticky="w", padx=30, pady=(12, 0))

        card = Card(self)
        card.grid(row=2, column=0, sticky="nsew", padx=30, pady=(10, 22))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)
        self.text = ctk.CTkTextbox(card, font=theme.font(10.5, mono=True),
                                   fg_color=theme.PANEL, border_width=0,
                                   corner_radius=0, wrap="word",
                                   text_color=theme.TEXT_SOFT)
        self.text.grid(row=0, column=0, sticky="nsew", padx=16, pady=14)
        self.text.configure(state="disabled")

    def refresh(self) -> None:
        try:
            with open("error.log", "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = ""
        self.summary.configure(text="有异常记录" if content.strip() else "暂无报错记录")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", content or "暂无报错记录")
        self.text.configure(state="disabled")

    def _clear(self) -> None:
        if not messagebox.askyesno("确认", "确定清空报错日志吗？"):
            return
        try:
            open("error.log", "w", encoding="utf-8").close()
        except OSError:
            pass
        self.refresh()


class HelpPage(ctk.CTkFrame):
    def __init__(self, master, config, on_check=None, **kwargs):
        kwargs.setdefault("fg_color", theme.BG)
        super().__init__(master, **kwargs)
        self.config = config
        self._on_check = on_check
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = PageHeader(self, "帮助", "常见问题与使用说明")
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(24, 0))
        if self._on_check is not None:
            ghost_button(header.right, "环境检查", self._on_check).pack(side="right")
        card = Card(self)
        card.grid(row=1, column=0, sticky="nsew", padx=30, pady=(16, 22))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)
        self.text = ctk.CTkTextbox(card, font=theme.font(11), fg_color=theme.PANEL,
                                   border_width=0, corner_radius=0, wrap="word",
                                   text_color=theme.TEXT_SOFT)
        self.text.grid(row=0, column=0, sticky="nsew", padx=16, pady=14)
        self.text.insert("end", self.config.get_help_text())
        self.text.configure(state="disabled")
