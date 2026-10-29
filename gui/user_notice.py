# -*- coding: utf-8 -*-
"""首次使用的用户须知弹窗。"""
from __future__ import annotations

import customtkinter as ctk

from gui import theme
from gui.widgets import primary_button, text_button

NOTICE_TEXT = """欢迎使用「{name}」

使用前请确认：

1. 本工具仅用于个人学习辅助，请遵守所在学校与平台的规定，因使用产生的后果由使用者自行承担。
2. 自动答题的答案来自题库与 AI，仅供参考，请勿在考试等场合完全依赖。
3. 建议倍速控制在 1–2 倍，过高倍速可能触发平台风控，甚至清空已完成的任务点。
4. 账号、密码和 API Key 以明文保存在本机 task/tool/account_info.json，请勿把这个文件发送给他人。
5. 程序运行期间请不要最小化浏览器窗口，部分任务点依赖窗口可见。

点击「知道了」即表示你已阅读并同意以上说明。"""


class UserNotice:
    def __init__(self, root, name, on_confirm, on_cancel):
        self.root = root
        self.name = name
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.remaining = 5
        self.window = None

    def show(self) -> None:
        win = ctk.CTkToplevel(self.root)
        self.window = win
        win.title("使用须知")
        win.geometry("560x470")
        win.resizable(False, False)
        win.configure(fg_color=theme.BG)
        win.transient(self.root)
        win.after(150, win.grab_set)
        win.after(200, win.lift)

        card = ctk.CTkFrame(win, fg_color=theme.PANEL, corner_radius=14,
                            border_width=1, border_color=theme.LINE)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(card, text="使用须知", font=theme.font(15, "bold"),
                     text_color=theme.TEXT, anchor="w").pack(
            fill="x", padx=20, pady=(18, 8))

        box = ctk.CTkTextbox(card, font=theme.font(11), fg_color="transparent",
                             border_width=0, wrap="word", text_color=theme.TEXT_SOFT)
        box.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        box.insert("end", NOTICE_TEXT.format(name=self.name))
        box.configure(state="disabled")

        bar = ctk.CTkFrame(card, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=(0, 14))
        text_button(bar, "退出", lambda: self._cancel(win), color=theme.MUTED).pack(side="right")
        self.confirm = primary_button(bar, f"知道了（{self.remaining}s）",
                                      lambda: self._confirm(win), height=34)
        self.confirm.configure(state="disabled")
        self.confirm.pack(side="right", padx=(0, 8))
        self._countdown(win)

    def _countdown(self, win) -> None:
        self.remaining -= 1
        if self.remaining > 0:
            self.confirm.configure(text=f"知道了（{self.remaining}s）")
            win.after(1000, lambda: self._countdown(win))
        else:
            self.confirm.configure(text="知道了", state="normal")

    def _confirm(self, win) -> None:
        win.destroy()
        self.on_confirm()

    def _cancel(self, win) -> None:
        win.destroy()
        self.on_cancel()
