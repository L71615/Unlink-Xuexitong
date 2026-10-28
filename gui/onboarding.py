# -*- coding: utf-8 -*-
"""首次启动的环境检查向导。"""
from __future__ import annotations

import os
import queue
import threading

import customtkinter as ctk

from gui import theme
from gui.widgets import Card, ghost_button, primary_button

EDGE_PATHS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)
CHROME_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)
BUNDLED_DRIVER = os.path.join("task", "tool", "edge_driver", "msedgedriver.exe")


class Onboarding:
    """环境检查弹窗：四项检查 + 去设置 / 开始使用。"""

    def __init__(self, root, config, on_settings, on_start=None):
        self.root = root
        self.config = config
        self.on_settings = on_settings
        self.on_start = on_start
        self.window = None
        self._rows = {}
        self._results = {}
        self._queue: queue.Queue = queue.Queue()

    # ------------------------------------------------------------------
    def show(self) -> None:
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            return

        window = ctk.CTkToplevel(self.root)
        self.window = window
        window.title("开始之前")
        window.geometry("600x500")
        window.resizable(False, False)
        window.configure(fg_color=theme.BG)
        window.transient(self.root)
        window.after(150, window.grab_set)
        window.after(200, window.lift)

        card = Card(window)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(card, text="开始之前", font=theme.font(18, "bold"),
                     text_color=theme.TEXT, anchor="w").pack(
            fill="x", padx=22, pady=(20, 2))
        ctk.CTkLabel(card, text="先确认一下运行环境，缺什么会给出入口", font=theme.font(11),
                     text_color=theme.MUTED, anchor="w").pack(fill="x", padx=22, pady=(0, 12))

        self._rows_box = ctk.CTkFrame(card, fg_color="transparent")
        self._rows_box.pack(fill="x", padx=16)

        for key, title, desc in (
            ("browser", "浏览器", "需要安装 Edge 或 Chrome"),
            ("driver", "浏览器驱动", "Edge 可以直接用项目自带的驱动"),
            ("account", "账号配置", "需要填写学习通账号和课程"),
            ("network", "网络", "需要能访问学习通"),
        ):
            self._rows[key] = self._make_row(self._rows_box, key, title, desc)

        bottom = ctk.CTkFrame(card, fg_color="transparent")
        bottom.pack(fill="x", padx=22, pady=(14, 18), side="bottom")

        self._skip = ctk.CTkCheckBox(
            bottom, text="下次启动不再提示", font=theme.font(11),
            text_color=theme.MUTED, checkbox_width=18, checkbox_height=18,
            corner_radius=4, border_width=1, fg_color=theme.accent(),
            hover_color=theme.accent())
        self._skip.select()
        self._skip.pack(side="left")

        primary_button(bottom, "开始使用", self._finish, height=36).pack(side="right")
        ghost_button(bottom, "去设置", self._open_settings, height=36).pack(
            side="right", padx=(0, 8))

        threading.Thread(target=self._run_checks, daemon=True).start()
        self.window.after(120, self._poll)

    def _poll(self) -> None:
        """主线程轮询检测结果，避免在子线程里操作 Tk。"""
        try:
            while True:
                key, state, text = self._queue.get_nowait()
                self._apply(key, state, text)
        except queue.Empty:
            pass
        if self.window is None or not self.window.winfo_exists():
            return
        self.window.after(120, self._poll)

    def _make_row(self, master, key, title, desc):
        row = ctk.CTkFrame(master, fg_color="transparent")
        row.pack(fill="x", pady=4)
        row.grid_columnconfigure(1, weight=1)

        dot = ctk.CTkLabel(row, text="●", font=theme.font(9), text_color=theme.FAINT,
                           width=14)
        dot.grid(row=0, column=0, padx=(6, 8), pady=8, sticky="n")

        text_col = ctk.CTkFrame(row, fg_color="transparent")
        text_col.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(text_col, text=title, font=theme.font(12, "bold"),
                     text_color=theme.TEXT, anchor="w").pack(anchor="w")
        ctk.CTkLabel(text_col, text=desc, font=theme.font(10.5),
                     text_color=theme.MUTED, anchor="w").pack(anchor="w", pady=(1, 0))

        status = ctk.CTkLabel(row, text="检测中…", font=theme.font(10.5),
                              text_color=theme.FAINT, anchor="e")
        status.grid(row=0, column=2, padx=(8, 10), pady=8, sticky="e")
        return {"dot": dot, "status": status, "row": row}

    # ------------------------------------------------------------------
    def _set(self, key, state, text):
        """子线程只往队列里放结果，由主线程更新界面。"""
        self._queue.put((key, state, text))

    def _apply(self, key, state, text):
        row = self._rows.get(key)
        if not row:
            return
        color = {"ok": theme.OK, "warn": theme.DANGER,
                 "info": theme.WARN, "pending": theme.FAINT}[state]
        row["dot"].configure(text_color=color)
        row["status"].configure(text=text, text_color=color)

    def _run_checks(self) -> None:
        account = self.config.load_account() or {}

        found = [path for path in EDGE_PATHS + CHROME_PATHS if os.path.exists(path)]
        if found:
            name = "Edge" if "Edge" in found[0] else "Chrome"
            self._set("browser", "ok", f"已找到 {name}")
        else:
            self._set("browser", "warn", "没找到浏览器")

        driver = (account.get("driver_path") or "").strip()
        if driver and os.path.exists(driver):
            self._set("driver", "ok", "已配置驱动")
        elif os.path.exists(BUNDLED_DRIVER):
            self._set("driver", "ok", "使用内置 Edge 驱动")
        else:
            self._set("driver", "info", "将自动下载驱动")

        if (account.get("phone_number") or "").strip():
            self._set("account", "ok", "已填写账号")
        else:
            self._set("account", "warn", "还没填写账号")

        try:
            import requests

            requests.head("https://i.chaoxing.com", timeout=4)
            self._set("network", "ok", "可以访问学习通")
        except Exception:
            self._set("network", "info", "暂时连不上，可稍后重试")

    # ------------------------------------------------------------------
    def _open_settings(self) -> None:
        self._close(save=False)
        self.on_settings()

    def _finish(self) -> None:
        self._close(save=True)

    def _close(self, save: bool) -> None:
        if save and self._skip.get():
            account = self.config.load_account() or {}
            account["onboarded"] = 1
            self.config.save_account(account)
        if self.window is not None:
            self.window.destroy()
            self.window = None
        if self.on_start:
            self.on_start()
