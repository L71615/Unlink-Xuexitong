# -*- coding: utf-8 -*-
"""UI 改版预览（独立脚本，不参与打包，不改动 gui/）。

用法:
    python mockups/preview_ui.py a   # 方向 A：工作台（浅色双栏）
    python mockups/preview_ui.py b   # 方向 B：控制台（深色日志区）

会渲染 1200x780 的窗口并把截图存到 mockups/proposal_<x>.png。
"""
from __future__ import annotations

import ctypes
import os
import sys
import time
import tkinter as tk
from pathlib import Path

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import customtkinter as ctk
from PIL import ImageGrab

# ---------------- 设计令牌（提案 v2） ----------------
BG = "#F5F6F9"
PANEL = "#FFFFFF"
SIDEBAR = "#FBFCFE"
LINE = "#E4E8EF"
LINE_SOFT = "#EEF1F6"
INK = "#0F172A"
INK_2 = "#475467"
INK_3 = "#667085"
INK_4 = "#98A2B3"
ACCENT = "#2F6BFF"
ACCENT_WEAK = "#EDF2FF"
OK = "#16A34A"
WARN = "#D97706"
DANGER = "#DC2626"

DARK = "#0E1726"
DARK_2 = "#152134"
DARK_LINE = "#233248"
DARK_INK = "#DCE5F2"
DARK_MUTED = "#8DA0BD"

UI = "微软雅黑"
MONO = "Cascadia Mono"

ICON = "Segoe Fluent Icons"
G = {
    "home": "\uE80F", "log": "\uE8FD", "score": "\uE930", "bank": "\uE8F1",
    "error": "\uE7BA", "settings": "\uE713", "help": "\uE897", "play": "\uE768",
    "sign": "\uE787", "stop": "\uE71A", "refresh": "\uE72C", "delete": "\uE74D",
    "user": "\uE77B", "clock": "\uE823", "chevron": "\uE76C", "add": "\uE710",
    "check": "\uE73E", "warn": "\uE7BA", "list": "\uE8FD", "book": "\uE8F1",
    "folder": "\uE8B7", "search": "\uE721",
}


def F(size: int, weight: str = "normal", mono: bool = False,
      icon: bool = False) -> ctk.CTkFont:
    if icon:
        return ctk.CTkFont(family=ICON, size=size)
    return ctk.CTkFont(family=MONO if mono else UI, size=size, weight=weight)


def label(parent, text, size=12, color=INK_2, weight="normal", **kw):
    lb = ctk.CTkLabel(parent, text=text, font=F(size, weight),
                      text_color=color, anchor="w")
    for k, v in kw.items():
        setattr(lb, k, v) if False else None
    return lb


def icon_label(parent, name, size=14, color=INK_3):
    return ctk.CTkLabel(parent, text=G[name], font=F(size, icon=True),
                        text_color=color)


def panel(parent, radius=12, color=PANEL, border=LINE):
    return ctk.CTkFrame(parent, fg_color=color, corner_radius=radius,
                        border_width=1, border_color=border)


def bar(parent, ratio: float, width: int = 200, height: int = 6,
        color=ACCENT, track="#E7EBF2"):
    c = tk.Canvas(parent, width=width, height=height, bg=parent.cget("fg_color")
                  if False else track, highlightthickness=0, bd=0)
    return c


def rounded_bar(parent, ratio: float, width: int = 200, height: int = 6,
                color=ACCENT, track="#E7EBF2", bg=PANEL):
    pb = ctk.CTkProgressBar(parent, width=width, height=height,
                            corner_radius=max(2, height // 2),
                            fg_color=track, progress_color=color,
                            border_width=0)
    pb.set(ratio)
    return pb


def pill(parent, text, fg=INK_3, bg="#F2F4F8", size=11):
    return ctk.CTkLabel(parent, text=text, font=F(size), text_color=fg,
                        fg_color=bg, corner_radius=8, padx=8, pady=3)


def sidebar(root, active="home"):
    rail = ctk.CTkFrame(root, fg_color=SIDEBAR, corner_radius=0, width=232)
    rail.pack(side="left", fill="y")
    rail.pack_propagate(False)
    tk.Frame(rail, width=1, bg=LINE).pack(side="right", fill="y")

    brand = ctk.CTkFrame(rail, fg_color="transparent")
    brand.pack(fill="x", padx=18, pady=(20, 0))
    mark = ctk.CTkLabel(brand, text="课", font=F(16, "bold"), text_color=PANEL,
                        fg_color=ACCENT, corner_radius=9, width=34, height=34)
    mark.pack(side="left")
    txt = ctk.CTkFrame(brand, fg_color="transparent")
    txt.pack(side="left", padx=(10, 0))
    ctk.CTkLabel(txt, text="课业助手", font=F(13, "bold"), text_color=INK,
                 anchor="w").pack(anchor="w")
    ctk.CTkLabel(txt, text="v1.0.0", font=F(10), text_color=INK_4,
                 anchor="w").pack(anchor="w")

    def group(title, items, top=22):
        ctk.CTkLabel(rail, text=title, font=F(10), text_color=INK_4,
                     anchor="w").pack(fill="x", padx=22, pady=(top, 6))
        for key, name in items:
            on = key == active
            row = ctk.CTkFrame(rail, fg_color=ACCENT_WEAK if on else "transparent",
                               corner_radius=9, height=36)
            row.pack(fill="x", padx=12, pady=1)
            row.pack_propagate(False)
            icon_label(row, key, 14, ACCENT if on else INK_3).pack(
                side="left", padx=(12, 9))
            ctk.CTkLabel(row, text=name, font=F(12, "bold" if on else "normal"),
                         text_color=ACCENT if on else INK_2,
                         anchor="w").pack(side="left")

    group("学习", [("home", "主页"), ("log", "刷课日志"), ("score", "测试成绩"),
                  ("bank", "题库查询")], top=20)
    group("其他", [("error", "报错日志"), ("settings", "设置"), ("help", "帮助")])

    card = ctk.CTkFrame(rail, fg_color=PANEL, corner_radius=10,
                        border_width=1, border_color=LINE)
    card.pack(side="bottom", fill="x", padx=12, pady=12)
    inner = ctk.CTkFrame(card, fg_color="transparent")
    inner.pack(fill="x", padx=12, pady=10)
    av = ctk.CTkLabel(inner, text="1", font=F(11, "bold"), text_color=ACCENT,
                      fg_color=ACCENT_WEAK, width=28, height=28, corner_radius=14)
    av.pack(side="left")
    u = ctk.CTkFrame(inner, fg_color="transparent")
    u.pack(side="left", padx=(9, 0))
    ctk.CTkLabel(u, text="已登录", font=F(11), text_color=INK, anchor="w").pack(anchor="w")
    ctk.CTkLabel(u, text="181****1033", font=F(10, mono=True),
                 text_color=INK_4, anchor="w").pack(anchor="w")
    return rail


def header(parent, title, sub, chips):
    box = ctk.CTkFrame(parent, fg_color="transparent")
    box.pack(fill="x")
    left = ctk.CTkFrame(box, fg_color="transparent")
    left.pack(side="left", anchor="w")
    ctk.CTkLabel(left, text=title, font=F(21, "bold"), text_color=INK,
                 anchor="w").pack(anchor="w")
    ctk.CTkLabel(left, text=sub, font=F(11), text_color=INK_3,
                 anchor="w").pack(anchor="w", pady=(2, 0))
    right = ctk.CTkFrame(box, fg_color="transparent")
    right.pack(side="right", anchor="n")
    for text, on in chips:
        dot = "#C9CED8"
        p = ctk.CTkFrame(right, fg_color="#FFFFFF", corner_radius=8,
                         border_width=1, border_color=LINE)
        p.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(p, text="●", font=F(7), text_color=ACCENT if on else dot,
                     text_color_disabled=None).pack(side="left", padx=(9, 5), pady=4)
        ctk.CTkLabel(p, text=text, font=F(10), text_color=INK_2).pack(
            side="left", padx=(0, 9), pady=4)
    return box


def log_view(parent, dark=False, height=0):
    bg = DARK if dark else "#FCFDFE"
    fg = DARK_INK if dark else INK_2
    t = tk.Text(parent, bg=bg, fg=fg, bd=0, highlightthickness=0, wrap="word",
                padx=16, pady=10, font=(MONO, 10), spacing1=2, spacing3=2,
                insertwidth=0, cursor="arrow")
    t.tag_configure("time", foreground=DARK_MUTED if dark else INK_4)
    t.tag_configure("ok", foreground="#4ADE80" if dark else OK)
    t.tag_configure("warn", foreground="#FBBF24" if dark else WARN)
    t.tag_configure("err", foreground="#F87171" if dark else DANGER)
    t.tag_configure("accent", foreground="#93B4FF" if dark else ACCENT)
    lines = [
        ("01:54:12", "开始刷课 · 大学生安全教育⑦", ""),
        ("01:54:13", "已加载账号 181****1033 · 章节模式", ""),
        ("01:54:15", "已定位课程，共 65 个任务点", ""),
        ("01:54:17", "检测到断点：65/65，从断点继续", "accent"),
        ("01:54:19", "调节倍速 1.0x · 完成", "ok"),
        ("01:54:22", "打开任务点 第 4 章 · 视频 03", ""),
        ("01:54:25", "视频时长 12:38 · 开始播放", ""),
        ("01:54:27", "检测到人脸弹窗 maskDiv", "warn"),
        ("01:54:29", "人脸自动处理 → 成功", "ok"),
        ("01:54:31", "章节测验 3 题 · 本地缓存命中 3", "ok"),
        ("01:54:33", "提交答案 · 已保存", ""),
        ("01:54:36", "视频完成 · 记录进度 41/65", ""),
        ("01:54:38", "切换任务点 第 4 章 · 文档 01", ""),
        ("01:54:41", "文档已读完 · 记录进度 42/65", ""),
        ("01:54:43", "章节测验 4 题 · 本地缓存命中 2", "ok"),
        ("01:54:45", "题目未命中，请求 DeepSeek ...", "accent"),
        ("01:54:47", "已返回 2 条答案 · 保存到缓存", "ok"),
        ("01:54:49", "提交答案 · 已保存", ""),
        ("01:54:51", "签到轮询 · 未检测到签到任务", ""),
        ("01:54:53", "进度 65/65 · 100%", "accent"),
        ("01:54:54", "本轮结束 · 用时 00:12:47", ""),
    ]
    for ts, msg, tag in lines:
        t.insert("end", ts + "  ", ("time",))
        t.insert("end", msg + "\n", (tag,) if tag else ())
    t.configure(state="disabled")
    return t


def preview_a(root):
    main = ctk.CTkFrame(root, fg_color=BG, corner_radius=0)
    main.pack(side="left", fill="both", expand=True)

    inner = ctk.CTkFrame(main, fg_color="transparent")
    inner.pack(fill="both", expand=True, padx=26, pady=(20, 22))

    header(inner, "主页", "让机器去刷，你去做别的", [("定时 未开启", False),
                                                 ("多端 关闭", False)])

    body = ctk.CTkFrame(inner, fg_color="transparent")
    body.pack(fill="both", expand=True, pady=(18, 0))

    # ---- 左栏：一整块运行面板，避免"卡片悬浮" ----
    left = ctk.CTkFrame(body, fg_color="transparent", width=300)
    left.pack(side="left", fill="y")
    left.pack_propagate(False)

    col = panel(left)
    col.pack(fill="both", expand=True)
    ctk.CTkLabel(col, text="本次运行", font=F(11), text_color=INK_3,
                 anchor="w").pack(fill="x", padx=18, pady=(16, 0))
    num = ctk.CTkFrame(col, fg_color="transparent")
    num.pack(fill="x", padx=18)
    ctk.CTkLabel(num, text="65", font=F(34, "bold"), text_color=INK,
                 anchor="w").pack(side="left")
    ctk.CTkLabel(num, text="/ 65 任务点", font=F(11), text_color=INK_4,
                 anchor="w").pack(side="left", padx=(8, 0), pady=(12, 0))
    rounded_bar(col, 1.0, width=1, height=6).pack(fill="x", padx=18, pady=(8, 18))

    for k, v, c in (("用时", "00:12:47", INK), ("异常", "0", INK),
                    ("状态", "已完成", OK)):
        row = ctk.CTkFrame(col, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=5)
        ctk.CTkLabel(row, text=k, font=F(11), text_color=INK_3,
                     anchor="w").pack(side="left")
        ctk.CTkLabel(row, text=v, font=F(11, "bold"), text_color=c,
                     anchor="e").pack(side="right")

    ctk.CTkFrame(col, height=1, fg_color=LINE_SOFT).pack(fill="x", padx=18,
                                                         pady=(14, 0))
    top = ctk.CTkFrame(col, fg_color="transparent")
    top.pack(fill="x", padx=18, pady=(14, 0))
    ctk.CTkLabel(top, text="待处理课程", font=F(11), text_color=INK_3,
                 anchor="w").pack(side="left")
    pill(top, "0", INK_3, "#F2F4F8", 10).pack(side="right")
    ctk.CTkLabel(col, text="没有待处理的课程", font=F(11), text_color=INK_4,
                 anchor="w").pack(fill="x", padx=18, pady=(8, 0))

    ctk.CTkFrame(col, fg_color="transparent").pack(fill="both", expand=True)
    ctk.CTkFrame(col, height=1, fg_color=LINE_SOFT).pack(fill="x", padx=18)
    ctk.CTkLabel(col, text="上次运行  10月29日 01:54", font=F(10),
                 text_color=INK_4, anchor="w").pack(fill="x", padx=18, pady=12)

    # ---- 右栏 ----
    right = ctk.CTkFrame(body, fg_color="transparent")
    right.pack(side="left", fill="both", expand=True, padx=(16, 0))

    ctrl = panel(right)
    ctrl.pack(fill="x")
    crow = ctk.CTkFrame(ctrl, fg_color="transparent")
    crow.pack(fill="x", padx=18, pady=14)
    dot = ctk.CTkLabel(crow, text="●", font=F(9), text_color=OK)
    dot.pack(side="left", pady=(2, 0))
    names = ctk.CTkFrame(crow, fg_color="transparent")
    names.pack(side="left", padx=(8, 0))
    ctk.CTkLabel(names, text="大学生安全教育⑦", font=F(14, "bold"),
                 text_color=INK, anchor="w").pack(anchor="w")
    sub = ctk.CTkFrame(names, fg_color="transparent")
    sub.pack(anchor="w", pady=(2, 0))
    pill(sub, "章节", INK_3, "#F2F4F8", 9).pack(side="left")
    ctk.CTkLabel(sub, text="65 / 65", font=F(10, mono=True),
                 text_color=INK_4).pack(side="left", padx=(8, 0))

    btns = ctk.CTkFrame(crow, fg_color="transparent")
    btns.pack(side="right")
    b1 = ctk.CTkButton(btns, text="  开始刷课", image=None, font=F(12, "bold"),
                       fg_color=ACCENT, hover_color="#1F5AE0", text_color="#FFFFFF",
                       corner_radius=9, height=36, width=108, compound="left")
    b1.pack(side="left")
    b2 = ctk.CTkButton(btns, text="  自动签到", font=F(12), fg_color="#FFFFFF",
                       hover_color="#F2F5FA", text_color=INK_2, corner_radius=9,
                       height=36, width=100, border_width=1, border_color=LINE)
    b2.pack(side="left", padx=8)
    b3 = ctk.CTkButton(btns, text="结束", font=F(12), fg_color="transparent",
                       hover_color="#FEECEC", text_color=DANGER, corner_radius=9,
                       height=36, width=56)
    b3.pack(side="left")

    logcard = panel(right)
    logcard.pack(fill="both", expand=True, pady=(14, 0))
    lh = ctk.CTkFrame(logcard, fg_color="transparent")
    lh.pack(fill="x", padx=16, pady=(12, 8))
    ctk.CTkLabel(lh, text="运行日志", font=F(12, "bold"), text_color=INK).pack(side="left")
    ctk.CTkLabel(lh, text="● 实时", font=F(10), text_color=OK).pack(side="left", padx=(10, 0))
    ctk.CTkLabel(lh, text="版本 1.0.0 · 断点 已完成 · 缓存 121 条", font=F(10),
                 text_color=INK_4).pack(side="left", padx=(14, 0))
    ctk.CTkLabel(lh, text="清空", font=F(10), text_color=INK_4).pack(side="right")
    tk.Frame(logcard, height=1, bg=LINE_SOFT).pack(fill="x")
    lv = log_view(logcard)
    lv.pack(fill="both", expand=True)


def preview_b(root):
    main = ctk.CTkFrame(root, fg_color=BG, corner_radius=0)
    main.pack(side="left", fill="both", expand=True)
    inner = ctk.CTkFrame(main, fg_color="transparent")
    inner.pack(fill="both", expand=True, padx=26, pady=(20, 22))

    header(inner, "主页", "让机器去刷，你去做别的", [("定时 未开启", False),
                                                 ("多端 关闭", False)])

    # 顶部一条控制条
    ctrl = ctk.CTkFrame(inner, fg_color=PANEL, corner_radius=12,
                        border_width=1, border_color=LINE)
    ctrl.pack(fill="x", pady=(18, 0))
    row = ctk.CTkFrame(ctrl, fg_color="transparent")
    row.pack(fill="x", padx=18, pady=13)
    ctk.CTkLabel(row, text="●", font=F(9), text_color=OK).pack(side="left", pady=(2, 0))
    ctk.CTkLabel(row, text="大学生安全教育⑦", font=F(14, "bold"),
                 text_color=INK).pack(side="left", padx=(9, 0))
    pill(row, "章节", INK_3, "#F2F4F8", 9).pack(side="left", padx=(10, 0))
    pill(row, "已完成", OK, "#EDF8F1", 9).pack(side="left", padx=(6, 0))

    # 内联指标（不用卡片）
    meter = ctk.CTkFrame(row, fg_color="transparent")
    meter.pack(side="left", padx=(26, 0))
    for k, v, c in (("本次完成", "0", INK), ("用时", "00:12:47", INK),
                    ("异常", "0", INK)):
        ctk.CTkLabel(meter, text=k, font=F(10), text_color=INK_4).pack(side="left")
        ctk.CTkLabel(meter, text=v, font=F(11, "bold"), text_color=c).pack(
            side="left", padx=(5, 0))
        ctk.CTkFrame(meter, width=1, height=12, fg_color=LINE).pack(
            side="left", padx=12)

    btns = ctk.CTkFrame(row, fg_color="transparent")
    btns.pack(side="right")
    ctk.CTkButton(btns, text="开始刷课", font=F(12, "bold"), fg_color=ACCENT,
                  hover_color="#1F5AE0", text_color="#FFFFFF", corner_radius=9,
                  height=36, width=100).pack(side="left")
    ctk.CTkButton(btns, text="自动签到", font=F(12), fg_color="#FFFFFF",
                  hover_color="#F2F5FA", text_color=INK_2, corner_radius=9,
                  height=36, width=96, border_width=1,
                  border_color=LINE).pack(side="left", padx=8)
    ctk.CTkButton(btns, text="结束", font=F(12), fg_color="transparent",
                  hover_color="#FEECEC", text_color=DANGER, corner_radius=9,
                  height=36, width=52).pack(side="left")

    # 深色控制台
    con = ctk.CTkFrame(inner, fg_color=DARK, corner_radius=12, border_width=1,
                       border_color=DARK_LINE)
    con.pack(fill="both", expand=True, pady=(14, 0))
    chead = ctk.CTkFrame(con, fg_color="transparent")
    chead.pack(fill="x", padx=18, pady=(14, 10))
    ctk.CTkLabel(chead, text="运行日志", font=F(12, "bold"),
                 text_color=DARK_INK).pack(side="left")
    ctk.CTkLabel(chead, text="● live", font=F(10),
                 text_color="#4ADE80").pack(side="left", padx=(10, 0))
    ctk.CTkLabel(chead, text="65 / 65 · 100%", font=F(10, mono=True),
                 text_color=DARK_MUTED).pack(side="left", padx=(16, 0))
    ctk.CTkLabel(chead, text="清空", font=F(10), text_color=DARK_MUTED).pack(side="right")

    rounded_bar(con, 1.0, width=1, height=4, track=DARK_LINE, bg=DARK).pack(
        fill="x", padx=18)
    tk.Frame(con, height=1, bg=DARK_LINE).pack(fill="x", pady=(12, 0))

    foot = ctk.CTkFrame(con, fg_color="transparent")
    foot.pack(side="bottom", fill="x", padx=18, pady=(0, 12))
    fr = ctk.CTkFrame(foot, fg_color="transparent")
    fr.pack(fill="x")
    for k, v in (("本次完成", "0"), ("已运行", "00:12:47"), ("异常", "0"),
                 ("断点", "已完成"), ("缓存", "121 条")):
        ctk.CTkLabel(fr, text=k, font=F(10), text_color=DARK_MUTED).pack(side="left")
        ctk.CTkLabel(fr, text=v, font=F(10, "bold"), text_color=DARK_INK).pack(
            side="left", padx=(5, 0))
        ctk.CTkFrame(fr, width=1, height=11, fg_color=DARK_LINE).pack(
            side="left", padx=10)

    lv = log_view(con, dark=True)
    lv.pack(fill="both", expand=True, padx=2, pady=(4, 0))


def main():
    variant = (sys.argv[1] if len(sys.argv) > 1 else "a").lower()
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.title("课业助手 · UI 预览")
    root.geometry("1180x760+120+80")
    root.configure(fg_color=BG)
    root.attributes("-topmost", True)

    sidebar(root, "home")
    (preview_a if variant == "a" else preview_b)(root)

    root.update_idletasks()
    root.update()
    time.sleep(0.7)
    root.update()
    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    out = Path(__file__).with_name("proposal_%s.png" % variant)
    ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(out)
    print("saved %s  bbox=%s size=%dx%d" % (out, (x, y), w, h))
    root.destroy()


if __name__ == "__main__":
    main()
