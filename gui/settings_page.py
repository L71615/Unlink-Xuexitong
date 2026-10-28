# -*- coding: utf-8 -*-
"""设置页：配置、账号、功能、高级选项、界面。"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from gui import theme
from gui.widgets import (Card, Hint, PageHeader, SectionTitle, text_button,
                         primary_button)

BROWSERS = ("不指定浏览器", "edge", "chrome")
QUESTION_CHOICES = ("DeepSeek AI", "随机答题", "不刷题")
VIDEO_CHOICES = ("DeepSeek AI", "随机答题")
DISCUSSION_CHOICES = ("DeepSeek AI", "跳过讨论")
SPEEDS = ("1", "2", "3", "4", "5", "6", "8", "10", "16")
AFTER_FINISH = ("仅自动保存", "强制自动提交", "搜到60%的题自动提交",
                "搜到70%的题自动提交", "搜到80%的题自动提交",
                "搜到90%的题自动提交", "搜到100%的题自动提交")
HOMEWORK_CHOICES = ("手动选择", "自动选择")
FONT_FAMILIES = ("Microsoft YaHei", "微软雅黑", "宋体", "楷体", "黑体", "Helvetica")
FONT_SIZES = tuple(str(i) for i in range(9, 17))


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
        self._course_vars: list[tk.StringVar] = []
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = PageHeader(self, "设置", "配置保存在 task/tool/account_info.json")
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(24, 0))
        primary_button(header.right, "保存设置", self.save, icon="save").pack(side="right")

        body = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                      scrollbar_button_color=theme.LINE,
                                      scrollbar_button_hover_color=theme.FAINT)
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=(10, 16))
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
        self._build_interface(right)
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

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=3, column=0, columnspan=3, sticky="ew", padx=18, pady=(6, 0))
        ctk.CTkLabel(head, text="课程", font=theme.font(11), text_color=theme.MUTED,
                     anchor="w").pack(side="left")
        text_button(head, "+ 添加", self._add_course, height=26).pack(side="right")

        self.course_box = ctk.CTkFrame(card, fg_color="transparent")
        self.course_box.grid(row=4, column=0, columnspan=3, sticky="ew", padx=18)

        Hint(card, "最多 3 门，名称要与学习通里完全一致").grid(
            row=5, column=0, columnspan=3, sticky="w", padx=18, pady=(2, 14))

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

        self.speed = _combo(self.brush, SPEEDS, command=self._on_speed_change)
        self._row(self.brush, 4, "倍速", self.speed)

        self.api = _entry(self.brush, show="*")
        self._row(self.brush, 5, "API Key", self.api,
                  text_button(self.brush, "显示", self._toggle_api, height=28))

        self.switch_face = _switch(self.brush)
        self._row(self.brush, 6, "跳过人脸", self.switch_face)
        self.switch_multi = _switch(self.brush, command=self._on_multi_warn)
        self._row(self.brush, 7, "多端学习", self.switch_multi)
        self.switch_skip = _switch(self.brush, command=self._on_skip_video)
        self._row(self.brush, 8, "秒过视频", self.switch_skip)
        self.switch_lock = _switch(self.brush)
        self._row(self.brush, 9, "防锁屏", self.switch_lock)

        timer_box = ctk.CTkFrame(self.brush, fg_color="transparent")
        self.timer_switch = _switch(timer_box, command=self._on_timer_switch)
        self.timer_switch.pack(side="left")
        text_button(timer_box, "设置时间", self._open_timer, height=28).pack(
            side="left", padx=(10, 0))
        self._row(self.brush, 10, "定时刷课", timer_box)

        self.timer_hint = Hint(self.brush, "未设置定时")
        self.timer_hint.grid(row=11, column=0, columnspan=3, sticky="w",
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

    def _build_interface(self, parent) -> None:
        card = self._card(parent, "界面")
        self.font_family = _combo(card, FONT_FAMILIES, readonly=False)
        self._row(card, 1, "字体", self.font_family)
        self.font_size = _combo(card, FONT_SIZES)
        self._row(card, 2, "字号", self.font_size)
        self.accent = _combo(card, tuple(theme.ACCENTS.keys()))
        self._row(card, 3, "主题色", self.accent)
        self.switch_top = _switch(card)
        self._row(card, 4, "窗口置顶", self.switch_top)
        Hint(card, "字体、字号、主题色下次启动生效").grid(
            row=5, column=0, columnspan=3, sticky="w", padx=18, pady=(0, 14))

    # ------------------------------------------------------------------
    # 课程行
    # ------------------------------------------------------------------
    def _add_course(self) -> None:
        if len(self._course_vars) >= 3:
            messagebox.showwarning("提示", "最多添加 3 门课程")
            return
        self._course_vars.append(tk.StringVar(value=""))
        self._render_courses()

    def _remove_course(self, index: int) -> None:
        if len(self._course_vars) <= 1:
            return
        self._course_vars.pop(index)
        self._render_courses()

    def _render_courses(self) -> None:
        for widget in self.course_box.winfo_children():
            widget.destroy()
        for index, var in enumerate(self._course_vars):
            row = ctk.CTkFrame(self.course_box, fg_color="transparent")
            row.pack(fill="x", pady=2)
            row.grid_columnconfigure(0, weight=1)
            entry = _entry(row, textvariable=var)
            entry.grid(row=0, column=0, sticky="ew")
            if len(self._course_vars) > 1:
                text_button(row, "删除", lambda i=index: self._remove_course(i),
                            color=theme.DANGER, height=28).grid(row=0, column=1,
                                                                padx=(6, 0))

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

    def _on_speed_change(self, value) -> None:
        if value.isdigit() and int(value) > 2:
            messagebox.showinfo("提示", "倍速过高可能让已完成的任务点被清空，谨慎使用")

    def _on_multi_warn(self) -> None:
        if self.switch_multi.get():
            messagebox.showwarning(
                "注意", "开启多端学习会同时跑多门课，有可能清空进度，"
                        "除非实在刷不完，建议一科一科来")

    def _on_skip_video(self) -> None:
        if self.switch_skip.get():
            self.speed.set("1")
            self.speed.configure(state="disabled")
        else:
            self.speed.configure(state="readonly")

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

        courses = [c for c in (account.get("cour") or [""])][:3] or [""]
        self._course_vars = [tk.StringVar(value=c) for c in courses]
        self._render_courses()

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
        self.speed.set(account.get("speed") or "1")
        self.api.insert(0, account.get("API", ""))
        self.homework_choice.set(account.get("homework") or "手动选择")
        self.homework_api.insert(0, account.get("API", ""))

        self.font_family.set(account.get("font_type") or "Microsoft YaHei")
        self.font_size.set(str(account.get("font_size") or 13))
        self.accent.set(account.get("accent") or theme.DEFAULT_ACCENT)

        pairs = ((self.switch_face, "pass_face"), (self.switch_multi, "multi_device"),
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
        courses = [var.get().strip() for var in self._course_vars if var.get().strip()]
        account["cour"] = courses
        account["choice"] = self.choice.get()
        account["after_finish_question"] = self.after_finish.get()
        account["video_title_choice"] = self.video_choice.get()
        account["discussion_choice"] = self.discussion.get()
        account["API"] = (self.api.get() if self.mode.get() == 1
                          else self.homework_api.get()).strip()
        account["speed"] = self.speed.get()
        account["homework"] = self.homework_choice.get()
        account["task_type"] = "章节" if self.mode.get() == 1 else "作业"
        account["radio_var"] = self.mode.get()
        account["font_type"] = self.font_family.get()
        account["font_size"] = self.font_size.get()
        account["accent"] = self.accent.get()
        account["pass_face"] = int(self.switch_face.get())
        account["multi_device"] = int(self.switch_multi.get())
        account["pass_vido"] = int(self.switch_skip.get())
        account["lock_screen"] = int(self.switch_lock.get())
        account["topmost"] = int(self.switch_top.get())

        if not messagebox.askokcancel("保存", "确认保存这些设置吗？"):
            return
        if not self.config.save_account(account):
            messagebox.showerror("保存失败", "写入配置失败，请检查文件权限")
            return
        self.config.save_courses(account["phone_number"], courses)
        self._on_saved(account)
        messagebox.showinfo("已保存", "设置已保存")

    def _validate(self) -> bool:
        if not self.phone.get().strip():
            messagebox.showerror("缺少信息", "请填写账号")
            return False
        if not self.password.get().strip():
            messagebox.showerror("缺少信息", "请填写密码")
            return False
        if not any(var.get().strip() for var in self._course_vars):
            messagebox.showerror("缺少信息", "请填写至少一门课程")
            return False
        if not self.browser.get():
            messagebox.showerror("缺少信息", "请选择浏览器")
            return False
        if self.browser.get() != "不指定浏览器" and not self.driver.get().strip():
            messagebox.showerror("缺少信息", "请填写驱动地址")
            return False
        if self.mode.get() == 1:
            if not self.speed.get():
                messagebox.showerror("缺少信息", "请选择倍速")
                return False
            if "DeepSeek AI" in (self.choice.get(), self.video_choice.get(),
                                 self.discussion.get()) and not self.api.get().strip():
                messagebox.showerror("缺少信息", "使用 DeepSeek 需要填写 API Key")
                return False
        elif not self.homework_api.get().strip():
            messagebox.showerror("缺少信息", "作业模式需要填写 DeepSeek API Key")
            return False
        return True
