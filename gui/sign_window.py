# -*- coding: utf-8 -*-
"""自动签到监控窗口：只处理普通签到与位置签到。"""
from __future__ import annotations

import threading
import tkinter as tk

import customtkinter as ctk

from gui import theme
from gui.widgets import Hint, ghost_button, primary_button
from task.xxt import constants, login as login_mod, monitor, storage

sign_txt = None


def bootstrap(phone: str | None = None, password: str | None = None):
    """优先用本地保存的登录信息，失效则用账号密码重新登录。"""
    client = login_mod.restore_client(sign_text=sign_txt)
    if client is not None:
        storage.log(f"已使用本地保存的登录信息（{client.name or client.uid}），无需重新输入",
                    sign_text=sign_txt)
        return client
    client, msg = login_mod.do_login(phone, password)
    if client is not None:
        storage.log(msg, sign_text=sign_txt)
        return client
    storage.log(f"登录失败：{msg}", sign_text=sign_txt)
    return None


def start_sign_monitor(account, stop_event=None, sign_text=None) -> None:
    global sign_txt
    sign_txt = sign_text
    client = bootstrap(account.get("phone_number", ""), account.get("password", ""))
    if client is None:
        return
    try:
        monitor.monitor(client, interval=constants.CHECK_INTERVAL,
                        stop_event=stop_event, sign_text=sign_txt)
    except Exception as error:
        storage.log(f"监控异常退出：{error}", sign_text=sign_txt)


class SignWindow:
    def __init__(self, master, account_info, **kwargs):
        self.master = master
        self.account_info = account_info
        self.stop_event = threading.Event()
        self.thread = None

        self.window = ctk.CTkToplevel(master)
        self.window.title("自动签到")
        self.window.geometry("480x470")
        self.window.configure(fg_color=theme.BG)
        self.window.transient(master)
        self.window.after(150, self.window.lift)
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        card = ctk.CTkFrame(self.window, fg_color=theme.PANEL, corner_radius=14,
                            border_width=1, border_color=theme.LINE)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(16, 6))
        ctk.CTkLabel(top, text="签到监控", font=theme.font(14, "bold"),
                     text_color=theme.TEXT).pack(side="left")
        self.state = ctk.CTkLabel(top, text="未启动", font=theme.font(11),
                                  text_color=theme.MUTED)
        self.state.pack(side="right")

        Hint(card, "只支持普通签到和位置签到，其它类型需要手动完成").pack(
            fill="x", padx=18, pady=(0, 10))

        self.text = ctk.CTkTextbox(card, font=theme.font(10.5, mono=True),
                                   fg_color=theme.BG, border_width=0,
                                   corner_radius=10, wrap="word",
                                   text_color=theme.TEXT_SOFT)
        self.text.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        bar = ctk.CTkFrame(card, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=(0, 14))
        self.start_btn = primary_button(bar, "启动监控", self.start_monitor,
                                        icon="play", height=36)
        self.start_btn.pack(side="left")
        self.stop_btn = ghost_button(bar, "停止", self.stop_monitor, height=36)
        self.stop_btn.pack(side="left", padx=(8, 0))
        self.stop_btn.configure(state="disabled")

    # ------------------------------------------------------------------
    def start_monitor(self) -> None:
        self.stop_event.clear()
        self.text.delete("1.0", "end")
        self.state.configure(text="运行中", text_color=theme.OK)
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        def run():
            try:
                start_sign_monitor(self.account_info, self.stop_event, self.text)
            except Exception as error:
                self.text.after(0, self.text.insert, "end", f"[错误] {error}\n")
            finally:
                self.text.after(0, self._mark_stopped)

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def _mark_stopped(self) -> None:
        self.state.configure(text="已停止", text_color=theme.MUTED)
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def stop_monitor(self) -> None:
        self.stop_event.set()
        self.text.insert("end", "已请求停止签到监控\n")
        self._mark_stopped()

    def on_close(self) -> None:
        self.stop_event.set()
        self.window.destroy()
