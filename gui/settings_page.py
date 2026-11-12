# -*- coding: utf-8 -*-
"""设置页：账号、浏览器、功能、高级选项。课程与倍速在主页选择。"""
from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from gui import theme
from gui.widgets import (Card, Hint, PageHeader, ProgressBar, SectionTitle,
                         text_button, primary_button)
from core import accounts, updater
from version import APP_NAME, APP_VERSION

BROWSERS = ("不指定浏览器", "edge", "chrome")
QUESTION_CHOICES = ("DeepSeek AI", "随机答题", "不刷题")
VIDEO_CHOICES = ("DeepSeek AI", "随机答题")
DISCUSSION_CHOICES = ("DeepSeek AI", "跳过讨论")
AFTER_FINISH = ("仅自动保存", "强制自动提交", "搜到60%的题自动提交",
                "搜到70%的题自动提交", "搜到80%的题自动提交",
                "搜到90%的题自动提交", "搜到100%的题自动提交")
HOMEWORK_CHOICES = ("手动选择", "自动选择")


def _entry(parent, **kwargs):
    kwargs.setdefault("fg_color", theme.PANEL)
    kwargs.setdefault("border_color", theme.LINE)
    kwargs.setdefault("border_width", 1)
    kwargs.setdefault("corner_radius", 8)
    kwargs.setdefault("height", 34)
    kwargs.setdefault("font", theme.font(11.5))
    kwargs.setdefault("text_color", theme.TEXT)
    return ctk.CTkEntry(parent, **kwargs)


def _combo(parent, values, readonly=True, **kwargs):
    kwargs.setdefault("values", list(values))
    kwargs.setdefault("font", theme.font(11.5))
    kwargs.setdefault("height", 34)
    kwargs.setdefault("corner_radius", 8)
    kwargs.setdefault("border_width", 1)
    kwargs.setdefault("border_color", theme.LINE)
    kwargs.setdefault("fg_color", theme.PANEL)
    kwargs.setdefault("button_color", theme.PANEL)
    kwargs.setdefault("button_hover_color", theme.LINE_SOFT)
    kwargs.setdefault("dropdown_fg_color", theme.PANEL)
    kwargs.setdefault("dropdown_hover_color", theme.LINE_SOFT)
    kwargs.setdefault("text_color", theme.TEXT)
    if readonly:
        kwargs.setdefault("state", "readonly")
    return ctk.CTkComboBox(parent, **kwargs)


def _switch(parent, command=None):
    return ctk.CTkSwitch(parent, text="", width=38, height=20,
                         progress_color=theme.accent(),
                         button_color=theme.PANEL,
                         button_hover_color=theme.PANEL,
                         fg_color=theme.LINE,
                         border_width=0,
                         command=command)


class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, config, on_saved, open_timer, timer_text,
                 **kwargs):
        kwargs.setdefault("fg_color", theme.BG)
        super().__init__(master, **kwargs)
        self.config = config
        self._on_saved = on_saved
        self._open_timer = open_timer
        self._timer_text = timer_text
        self._busy = False
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = PageHeader(self, "设置", "账号与运行偏好；课程、倍速在主页选择")
        header.grid(row=0, column=0, sticky="ew",
                    padx=(theme.PAGE_PAD, theme.PAGE_PAD + 6), pady=(22, 0))
        primary_button(header.right, "保存设置", self.save, icon="save").pack(side="right")

        body = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                      scrollbar_button_color=theme.LINE,
                                      scrollbar_button_hover_color=theme.FAINT)
        body.grid(row=1, column=0, sticky="nsew",
                  padx=(theme.PAGE_PAD - 6, theme.PAGE_PAD + 6), pady=(10, 16))
        body.grid_columnconfigure(0, weight=1, uniform="col")
        body.grid_columnconfigure(1, weight=1, uniform="col")

        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(6, 10), pady=6)
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 6), pady=6)

        self._build_account(left)
        self._build_config(left)
        self._build_function(left)
        self._build_advanced(right)
        self._build_about(right)
        self.load()

    def _card(self, parent, title: str) -> Card:
        card = Card(parent)
        card.pack(fill="x", pady=(0, 14))
        card.grid_columnconfigure(1, weight=1)
        SectionTitle(card, title).grid(row=0, column=0, columnspan=3,
                                       sticky="w", padx=18, pady=(16, 8))
        return card

    def _row(self, card, row: int, text: str, widget, extra=None):
        ctk.CTkLabel(card, text=text, font=theme.font(11), text_color=theme.MUTED,
                     anchor="w", width=72).grid(row=row, column=0, sticky="w",
                                                padx=(18, 10), pady=6)
        widget.grid(row=row, column=1, sticky="ew", pady=6,
                    padx=(0, 6) if extra is not None else (0, 18))
        if extra is not None:
            extra.grid(row=row, column=2, sticky="w", padx=(0, 14), pady=6)

    # ------------------------------------------------------------------
    def _build_account(self, parent) -> None:
        card = self._card(parent, "账号信息")

        self.phone = _entry(card)
        self._row(card, 1, "账号", self.phone)

        self.password = _entry(card, show="*")
        self._row(card, 2, "密码", self.password,
                  text_button(card, "显示", self._toggle_password, height=28))

        self.account_pick = _combo(card, [], command=self._on_pick_account)
        self.account_pick.set("")
        self._row(card, 3, "已存账号", self.account_pick,
                  text_button(card, "删除", self._delete_account, height=28))

        Hint(card, "保存账号后到主页点「登录」读取课程，再勾选要刷的课；倍速也在主页选").grid(
            row=4, column=0, columnspan=3, sticky="w", padx=18, pady=(2, 14))

    # ------------------------------------------------------------------
    # 多账号
    # ------------------------------------------------------------------
    def _refresh_account_combo(self, selected: str = "") -> None:
        """把账号簿里的手机号填进下拉框，并选中当前账号。"""
        saved = accounts.phones()
        self.account_pick.configure(values=saved or [""])
        pick = selected or accounts.current() or (saved[0] if saved else "")
        self.account_pick.set(pick if pick in saved else "")

    def _on_pick_account(self, choice) -> None:
        """选中已存账号：自动填手机号和密码（不写盘，保存时才生效）。"""
        phone = (choice or "").strip()
        item = accounts.get(phone)
        if not item:
            return
        self.phone.delete(0, tk.END)
        self.phone.insert(0, phone)
        password = accounts.password_of(phone)
        if password:
            self.password.delete(0, tk.END)
            self.password.insert(0, password)

    def _delete_account(self) -> None:
        phone = (self.account_pick.get() or "").strip()
        if not phone:
            messagebox.showinfo("提示", "先在上方选择要删除的账号")
            return
        if not messagebox.askokcancel("删除账号", f"从账号簿里删除 {phone}？\n（不会删除该账号的刷课进度）"):
            return
        accounts.remove(phone)
        self._refresh_account_combo()
        self.account_pick.set("")

    def _build_config(self, parent) -> None:
        card = self._card(parent, "浏览器")

        self.browser = _combo(card, BROWSERS, command=self._on_browser_change)
        self._row(card, 1, "浏览器", self.browser)

        self.driver = _entry(card)
        self._row(card, 2, "驱动地址", self.driver)

        text_button(card, "选择驱动文件", self._pick_driver, height=26).grid(
            row=3, column=1, sticky="w", padx=(0, 18), pady=(0, 14))

    def _build_function(self, parent) -> None:
        card = self._card(parent, "功能")
        self.mode = tk.IntVar(value=1)
        for i, (value, text) in enumerate(((1, "自动刷课答题"), (2, "自动完成作业"))):
            ctk.CTkRadioButton(card, text=text, variable=self.mode, value=value,
                               font=theme.font(11.5), text_color=theme.TEXT,
                               fg_color=theme.accent(), hover_color=theme.accent(),
                               command=self._on_mode_change).grid(
                row=1 + i, column=0, columnspan=3, sticky="w", padx=18, pady=5)
        ctk.CTkRadioButton(card, text="自动完成考试（开发中）", variable=self.mode, value=3,
                           font=theme.font(11.5), text_color=theme.FAINT,
                           fg_color=theme.FAINT, state="disabled").grid(
            row=3, column=0, columnspan=3, sticky="w", padx=18, pady=(5, 6))
        Hint(card, "作业模式只作答并暂存，不会自动提交").grid(
            row=4, column=0, columnspan=3, sticky="w", padx=18, pady=(0, 14))

    def _build_advanced(self, parent) -> None:
        card = self._card(parent, "高级设置")
        self.advanced_card = card

        self.brush = ctk.CTkFrame(card, fg_color="transparent")
        self.brush.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.brush.grid_columnconfigure(1, weight=1)

        self.choice = _combo(self.brush, QUESTION_CHOICES, command=self._on_choice_change)
        self._row(self.brush, 0, "章节测验", self.choice)

        self.after_finish = _combo(self.brush, AFTER_FINISH)
        self._row(self.brush, 1, "答完题后", self.after_finish)

        self.video_choice = _combo(self.brush, VIDEO_CHOICES)
        self._row(self.brush, 2, "视频题目", self.video_choice)

        self.discussion = _combo(self.brush, DISCUSSION_CHOICES)
        self._row(self.brush, 3, "讨论", self.discussion)

        self.api = _entry(self.brush, show="*")
        self._row(self.brush, 4, "API Key", self.api,
                  text_button(self.brush, "显示", self._toggle_api, height=28))

        self.switch_face = _switch(self.brush)
        self._row(self.brush, 5, "自动处理人脸", self.switch_face)
        self.switch_skip = _switch(self.brush)
        self._row(self.brush, 6, "秒过视频", self.switch_skip)
        self.switch_lock = _switch(self.brush)
        self._row(self.brush, 7, "防锁屏", self.switch_lock)
        self.switch_top = _switch(self.brush)
        self._row(self.brush, 8, "窗口置顶", self.switch_top)

        timer_box = ctk.CTkFrame(self.brush, fg_color="transparent")
        self.timer_switch = _switch(timer_box, command=self._on_timer_switch)
        self.timer_switch.pack(side="left")
        text_button(timer_box, "设置时间", self._open_timer, height=28).pack(
            side="left", padx=(10, 0))
        self._row(self.brush, 9, "定时刷课", timer_box)

        self.timer_hint = Hint(self.brush, "未设置定时")
        self.timer_hint.grid(row=10, column=0, columnspan=3, sticky="w",
                             padx=18, pady=(0, 14))

        self.homework = ctk.CTkFrame(card, fg_color="transparent")
        self.homework.grid(row=2, column=0, columnspan=3, sticky="ew")
        self.homework.grid_columnconfigure(1, weight=1)
        self.homework_choice = _combo(self.homework, HOMEWORK_CHOICES)
        self._row(self.homework, 0, "选择作业", self.homework_choice)
        self.homework_api = _entry(self.homework, show="*")
        self._row(self.homework, 1, "API Key", self.homework_api,
                  text_button(self.homework, "显示", self._toggle_homework_api, height=28))
        Hint(self.homework, "作业会逐个打开，作答后点「暂时保存」").grid(
            row=2, column=0, columnspan=3, sticky="w", padx=18, pady=(0, 14))
        self.homework.grid_remove()

    def _build_about(self, parent) -> None:
        card = self._card(parent, "版本")

        self.version_label = ctk.CTkLabel(
            card, text=f"{APP_NAME} {APP_VERSION}", font=theme.font(11.5),
            text_color=theme.TEXT, anchor="w")
        self.update_button = text_button(card, "检查更新", self.check_update, height=28)
        self._row(card, 1, "当前版本", self.version_label, self.update_button)

        self.update_hint = Hint(card, "点「检查更新」可一键升到最新版")
        self.update_hint.grid(row=2, column=0, columnspan=3, sticky="w",
                              padx=18, pady=(0, 8))

        self.update_bar = ProgressBar(card, 6)
        self.update_bar.grid(row=3, column=0, columnspan=3, sticky="ew",
                             padx=18, pady=(0, 10))
        self.update_bar.grid_remove()

        text_button(card, "更新失败时去发布页手动下载", updater.open_release_page,
                    height=26).grid(row=4, column=0, columnspan=3, sticky="w",
                                    padx=18, pady=(0, 14))

    # ------------------------------------------------------------------
    # 检查更新
    # ------------------------------------------------------------------
    def check_update(self) -> None:
        if self._busy:
            return
        if not updater.can_self_update():
            messagebox.showinfo(
                "检查更新",
                "当前是源码运行，git pull 就能拿到最新代码。\n"
                "打包成 exe 之后，这个按钮才会真正替换文件。")
            return
        self._busy = True
        self.update_button.configure(state="disabled", text="检查中…")
        self.update_hint.configure(text="正在连接 GitHub…")
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self) -> None:
        try:
            release = updater.check_latest()
        except Exception as error:
            self._ui(self._check_failed, error)
            return
        self._ui(self._check_done, release)

    def _check_done(self, release) -> None:
        if release is None:
            self._release_busy()
            self.update_hint.configure(text=f"已是最新版本 {APP_VERSION}")
            messagebox.showinfo("检查更新", f"当前已是最新版本 {APP_VERSION}")
            return
        notes = updater.summarize_notes(release.notes)
        detail = f"\n\n更新内容：{notes}" if notes else ""
        if not messagebox.askokcancel(
                "发现新版本",
                f"最新版本 {release.version}（当前 {APP_VERSION}）{detail}\n\n"
                "程序会退出，替换文件后自动重启。现在更新吗？"):
            self._release_busy()
            return
        self.update_button.configure(text="下载中…")
        self.update_hint.configure(text=f"正在下载 {release.version}…")
        self.update_bar.grid()
        self.update_bar.set(0)
        threading.Thread(target=self._download_worker, args=(release,),
                         daemon=True).start()

    def _check_failed(self, error: Exception) -> None:
        self._release_busy()
        self.update_hint.configure(text="检查失败，可以点下面去发布页手动下载")
        messagebox.showerror(
            "检查更新失败",
            f"连不上 GitHub：{error}\n\n"
            "网络不通时，点「更新失败时去发布页手动下载」自己下 zip 覆盖即可。")

    def _download_worker(self, release) -> None:
        def progress(done: int, total: int) -> None:
            if total:
                self._ui(self._show_progress, done, total)

        try:
            updater.install(release, progress=progress)
        except Exception as error:
            self._ui(self._download_failed, error)
            return
        self._ui(self._ready_to_restart)

    def _show_progress(self, done: int, total: int) -> None:
        self.update_bar.set(done / float(total or 1))
        self.update_hint.configure(
            text=f"正在下载 {done / 1048576:.1f} / {total / 1048576:.1f} MB")

    def _download_failed(self, error: Exception) -> None:
        self._release_busy()
        self.update_bar.grid_remove()
        self.update_hint.configure(text="下载失败，可以点下面去发布页手动下载")
        messagebox.showerror("更新失败", f"下载或解压失败：{error}")

    def _ready_to_restart(self) -> None:
        self.update_bar.set(1.0)
        self.update_hint.configure(text="更新已就绪，正在重启…")
        messagebox.showinfo("更新完成", "程序会立刻退出，约两秒后自动重启为新版本。")
        try:
            self.winfo_toplevel().destroy()
        finally:
            os._exit(0)

    def _release_busy(self) -> None:
        self._busy = False
        self.update_button.configure(state="normal", text="检查更新")

    def _ui(self, callback, *args) -> None:
        """后台线程不碰 Tk，统一扔回主循环执行。"""
        try:
            self.after(0, lambda: callback(*args))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 交互
    # ------------------------------------------------------------------
    def _toggle_password(self) -> None:
        self.password.configure(show="" if self.password.cget("show") == "*" else "*")

    def _toggle_api(self) -> None:
        self.api.configure(show="" if self.api.cget("show") == "*" else "*")

    def _toggle_homework_api(self) -> None:
        self.homework_api.configure(
            show="" if self.homework_api.cget("show") == "*" else "*")

    def _on_browser_change(self, choice: str) -> None:
        self.driver.configure(state="normal")
        self.driver.delete(0, tk.END)
        if choice == "edge":
            self.driver.insert(0, r"edgedriver_win64\msedgedriver.exe")
        elif choice == "chrome":
            self.driver.insert(0, r"chromedriver-win64\chromedriver.exe")
        else:
            self.driver.insert(0, "无需填写")
            self.driver.configure(state="disabled")

    def _pick_driver(self) -> None:
        path = filedialog.askopenfilename(title="选择浏览器驱动", filetypes=[("驱动", "*.exe")])
        if path:
            self.driver.configure(state="normal")
            self.driver.delete(0, tk.END)
            self.driver.insert(0, path)

    def _on_choice_change(self, _value=None) -> None:
        if self.choice.get() == "DeepSeek AI":
            self.after_finish.grid()
        else:
            self.after_finish.grid_remove()

    def _on_timer_switch(self) -> None:
        if self.timer_switch.get():
            self._open_timer()
        else:
            self.timer_hint.configure(text="未设置定时")

    def _on_mode_change(self) -> None:
        if self.mode.get() == 2:
            self.brush.grid_remove()
            self.homework.grid()
        else:
            self.homework.grid_remove()
            self.brush.grid()

    # ------------------------------------------------------------------
    # 载入 / 保存
    # ------------------------------------------------------------------
    def load(self) -> None:
        account = self.config.load_account()
        self.phone.delete(0, tk.END)
        self.phone.insert(0, account.get("phone_number", ""))
        self.password.delete(0, tk.END)
        self.password.insert(0, account.get("password", ""))

        # 首次升级：把 account_info.json 里的账号登记进账号簿
        try:
            accounts.migrate_from_account_info(account)
        except Exception:
            pass
        self._refresh_account_combo(account.get("phone_number", ""))

        self.browser.set(account.get("browser") or "不指定浏览器")
        self.driver.delete(0, tk.END)
        driver = account.get("driver_path", "")
        self.driver.insert(0, driver or ("无需填写" if self.browser.get() == "不指定浏览器"
                                         else ""))
        if self.browser.get() == "不指定浏览器":
            self.driver.configure(state="disabled")

        mode = account.get("radio_var", 1)
        self.mode.set(mode if mode in (1, 2) else 1)
        self.choice.set(account.get("choice") or "DeepSeek AI")
        self.after_finish.set(account.get("after_finish_question") or "仅自动保存")
        self.video_choice.set(account.get("video_title_choice") or "随机答题")
        self.discussion.set(account.get("discussion_choice") or "跳过讨论")
        self.api.delete(0, tk.END)
        self.api.insert(0, account.get("API", ""))
        self.homework_choice.set(account.get("homework") or "手动选择")
        self.homework_api.delete(0, tk.END)
        self.homework_api.insert(0, account.get("API", ""))

        pairs = ((self.switch_face, "pass_face"),
                 (self.switch_skip, "pass_vido"), (self.switch_lock, "lock_screen"),
                 (self.switch_top, "topmost"))
        for switch, key in pairs:
            switch.select() if account.get(key) else switch.deselect()

        if account.get("timer_active"):
            self.timer_switch.select()
        else:
            self.timer_switch.deselect()
        self.timer_hint.configure(text=self._timer_text() or "未设置定时")

        self._on_mode_change()
        self._on_choice_change()

    def save(self) -> None:
        if not self._validate():
            return
        account = self.config.get_account().copy()
        account.setdefault("file_name", ["python", "main.py"])
        account["user_notice"] = "False"
        account["browser"] = self.browser.get()
        account["driver_path"] = "" if self.browser.get() == "不指定浏览器" \
            else self.driver.get().strip()
        account["phone_number"] = self.phone.get().strip()
        account["password"] = self.password.get().strip()
        account["choice"] = self.choice.get()
        account["after_finish_question"] = self.after_finish.get()
        account["video_title_choice"] = self.video_choice.get()
        account["discussion_choice"] = self.discussion.get()
        account["API"] = (self.api.get() if self.mode.get() == 1
                          else self.homework_api.get()).strip()
        account["homework"] = self.homework_choice.get()
        account["task_type"] = "章节" if self.mode.get() == 1 else "作业"
        account["radio_var"] = self.mode.get()
        account["pass_face"] = int(self.switch_face.get())
        account["pass_vido"] = int(self.switch_skip.get())
        account["lock_screen"] = int(self.switch_lock.get())
        account["topmost"] = int(self.switch_top.get())

        if not messagebox.askokcancel("保存", "确认保存这些设置吗？"):
            return
        if not self.config.save_account(account):
            messagebox.showerror("保存失败", "写入配置失败，请检查文件权限")
            return
        try:
            accounts.upsert(account["phone_number"], account["password"])
        except Exception:
            pass
        self._refresh_account_combo(account["phone_number"])
        self._on_saved(account)
        messagebox.showinfo("已保存", "设置已保存。到主页点「登录」读取课程列表")

    def _validate(self) -> bool:
        if not self.phone.get().strip():
            messagebox.showerror("缺少信息", "请填写账号")
            return False
        if not self.password.get().strip():
            messagebox.showerror("缺少信息", "请填写密码")
            return False
        if not self.browser.get():
            messagebox.showerror("缺少信息", "请选择浏览器")
            return False
        if self.browser.get() != "不指定浏览器" and not self.driver.get().strip():
            messagebox.showerror("缺少信息", "请填写驱动地址")
            return False
        if self.mode.get() == 1:
            if "DeepSeek AI" in (self.choice.get(), self.video_choice.get(),
                                 self.discussion.get()) and not self.api.get().strip():
                messagebox.showerror("缺少信息", "使用 DeepSeek 需要填写 API Key")
                return False
        elif not self.homework_api.get().strip():
            messagebox.showerror("缺少信息", "作业模式需要填写 DeepSeek API Key")
            return False
        return True
