# -*- coding: utf-8 -*-
"""学习通刷课助手 —— 界面主程序。"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime

from tkinter import messagebox

import customtkinter as ctk

from core import resume as resume_store
from core.config_manager import ConfigManager
from gui import theme
from gui.home_page import HomePage
from gui.logs_page import ErrorPage, HelpPage, QuestionBankPage, RecordPage
from gui.onboarding import Onboarding
from gui.settings_page import SettingsPage
from gui.sidebar import Sidebar
from gui.sign_window import SignWindow
from gui.timer_window import TimerWindow
from gui.user_notice import UserNotice

APP_NAME = "学习通刷课助手"
APP_VERSION = "1.0.0"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def base_dir() -> str:
    """源码运行时是项目目录；打包后是 exe 所在目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def prepare_workdir() -> None:
    """切到程序目录；打包版把内置的 task 资源释放到 exe 旁边。

    只补缺失的文件，不覆盖用户自己的配置、记录和缓存。
    """
    target = base_dir()
    os.chdir(target)
    if not getattr(sys, "frozen", False):
        return

    source = getattr(sys, "_MEIPASS", "")
    if not source:
        return

    marker = os.path.join(target, ".assets_version")
    try:
        with open(marker, "r", encoding="utf-8") as handle:
            if handle.read().strip() == APP_VERSION:
                return
    except OSError:
        pass

    src_task = os.path.join(source, "task")
    dst_task = os.path.join(target, "task")
    if os.path.isdir(src_task):
        for root, _dirs, files in os.walk(src_task):
            relative = os.path.relpath(root, src_task)
            destination = dst_task if relative == "." else os.path.join(dst_task, relative)
            os.makedirs(destination, exist_ok=True)
            for name in files:
                src_file = os.path.join(root, name)
                dst_file = os.path.join(destination, name)
                if not os.path.exists(dst_file):
                    try:
                        shutil.copy2(src_file, dst_file)
                    except OSError:
                        pass
    try:
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write(APP_VERSION)
    except OSError:
        pass


def _setup_logging() -> None:
    handlers = []
    try:
        handlers.append(logging.FileHandler("输出记录.log", encoding="utf-8"))
    except OSError:
        try:
            path = os.path.join(tempfile.gettempdir(), "xuexitong_gui.log")
            handlers.append(logging.FileHandler(path, encoding="utf-8"))
        except OSError:
            pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers or [logging.NullHandler()],
    )


class App:
    def __init__(self) -> None:
        _setup_logging()
        self.logger = logging.getLogger(__name__)

        self.config = ConfigManager()
        self.account = self.config.load_account() or {}
        self.version = self.config.get_version()

        theme.configure(self.account.get("font_type") or "Microsoft YaHei",
                        self.account.get("font_size") or 13,
                        self.account.get("accent") or theme.DEFAULT_ACCENT)

        ctk.set_appearance_mode("light")
        self.root = ctk.CTk()
        self.root.configure(fg_color=theme.BG)
        self.root.title(f"{APP_NAME} {self.version}")
        self.root.minsize(1080, 720)
        self._center(1200, 780)
        self._set_icon()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        if self.account.get("topmost"):
            self.root.attributes("-topmost", True)

        # 运行状态
        self.running = False
        self.processes: dict[int, subprocess.Popen] = {}
        self.started_at: float | None = None
        self.errors = 0
        self._baseline_done = 0
        self._login_seen: dict[str, bool] = {}
        self._all_courses = list(self.account.get("cour") or [])
        self.timer_active = bool(self.account.get("timer_active"))
        self.timer_start = self.account.get("timer_start") or "04:00:00"
        self.timer_end = self.account.get("timer_end") or "03:00:00"
        self._sign_window = None
        self._tick_count = 0

        self.timer_window = TimerWindow(self.root, self._on_timer_set,
                                        self._on_timer_cancel)
        self._build()
        self._refresh_static()
        if self.account.get("user_notice", "True") == "True":
            self.show_notice()
        elif not self.account.get("onboarded"):
            self.root.after(400, self.show_onboarding)
        self._tick()

    # ------------------------------------------------------------------
    # 窗口
    # ------------------------------------------------------------------
    def _center(self, width: int, height: int) -> None:
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max((screen_w - width) // 2, 0)
        y = max((screen_h - height) // 2 - 20, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _set_icon(self) -> None:
        """在内存里画一个图标，不依赖外部文件。"""
        try:
            from PIL import Image, ImageDraw, ImageFont, ImageTk

            size = 64
            image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle([1, 1, size - 1, size - 1], radius=15,
                                   fill=theme.accent())
            try:
                font = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 38, index=0)
            except Exception:
                font = ImageFont.load_default()
            left, top, right, bottom = draw.textbbox((0, 0), "学", font=font)
            draw.text(((size - (right - left)) / 2 - left,
                       (size - (bottom - top)) / 2 - top),
                      "学", font=font, fill="#FFFFFF")
            self._icon_photo = ImageTk.PhotoImage(image)
            self.root.iconphoto(True, self._icon_photo)
        except Exception:
            pass

    def _build(self) -> None:
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.sidebar = Sidebar(self.root, self.version, self.show_page)
        self.sidebar.grid(row=0, column=0, sticky="ns")

        self.container = ctk.CTkFrame(self.root, fg_color=theme.BG, corner_radius=0)
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        self.home = HomePage(self.container, self.start, self.open_sign,
                             self.stop, self.clear_log)
        self.records = RecordPage(self.container, self.config, "刷课", "刷课日志",
                                  "每完成一个任务点都会记在这里")
        self.scores = RecordPage(self.container, self.config, "成绩", "测试成绩",
                                 "章节测验的提交结果")
        self.bank = QuestionBankPage(self.container, self.config)
        self.errors_page = ErrorPage(self.container)
        self.help_page = HelpPage(self.container, self.config, self.show_onboarding)
        self.settings_page = SettingsPage(self.container, self.config,
                                          self.on_settings_saved,
                                          self.open_timer, self.timer_text)

        self.pages = {
            "home": self.home,
            "log": self.records,
            "score": self.scores,
            "bank": self.bank,
            "error": self.errors_page,
            "settings": self.settings_page,
            "help": self.help_page,
        }
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        self.show_page("home")

    def show_page(self, key: str) -> None:
        page = self.pages.get(key)
        if page is None:
            return
        page.tkraise()
        self.sidebar.set_active(key)
        if key == "log":
            self.records.refresh()
        elif key == "score":
            self.scores.refresh()
        elif key == "bank":
            self.bank.refresh()
        elif key == "error":
            self.errors_page.refresh()

    # ------------------------------------------------------------------
    # 状态刷新
    # ------------------------------------------------------------------
    def _course_process(self, course: str) -> tuple[int, int]:
        try:
            data = self.config.get_course_process()
            done, total = data.get(course, (0, 0))
            return int(done), int(total)
        except Exception:
            return 0, 0

    def _refresh_static(self) -> None:
        account = self.config.load_account() or {}
        self.account = account
        self._all_courses = list(account.get("cour") or [])
        self.sidebar.set_user(account.get("phone_number", ""))
        self.home.set_version(self.version)
        self.home.set_cache(len(self._cache_files()))
        course = (account.get("cour") or [""])[0]
        done, total = self._course_process(course)
        self.home.set_course(course, done, total, account.get("task_type", "章节"))
        self.home.set_resume(self._resume_text(course, account.get("phone_number", "")))
        self.home.set_metrics(done=0, elapsed=0, errors=0)
        self.home.set_chips(self.timer_active, self._chip_text(),
                            bool(account.get("multi_device")))

    def _resume_text(self, course: str, phone: str = "") -> str:
        info = resume_store.snapshot(phone or self.account.get("phone_number", "")).get(course, {})
        status = info.get("status", "")
        if status == "done":
            return "已完成"
        if info.get("chapter"):
            updated = (info.get("updated_at") or "")[5:16]
            return f"{info['chapter'][:14]} · {updated}"
        if status == "running":
            return "上次中断"
        if status == "error":
            return "上次出错"
        return "未开始"

    def _cache_files(self) -> list[str]:
        folder = os.path.join("task", "record")
        if not os.path.isdir(folder):
            return []
        return [n for n in os.listdir(folder) if n.endswith(".pkl") and "ques1" in n]

    def timer_text(self) -> str:
        if not self.timer_active:
            return "未设置定时"
        return f"{self.timer_start} → {self.timer_end}"

    def _chip_text(self) -> str:
        if not self.timer_active:
            return "定时 未开启"
        return f"定时 {self.timer_start[:5]}–{self.timer_end[:5]}"

    def _tick(self) -> None:
        self._tick_count += 1
        if self.running and self.started_at:
            self.home.set_metrics(elapsed=int(time.time() - self.started_at),
                                  errors=self.errors)
            done, total = self._course_process(self._current_course())
            self.home.set_metrics(done=max(done - self._baseline_done, 0))
            self.home.set_course(self._current_course(), done, total,
                                 self.account.get("task_type", "章节"))

        now = datetime.now().strftime("%H:%M:%S")
        if self.timer_active:
            if now == self.timer_start and not self.running:
                self.start()
            elif now == self.timer_end and self.running:
                self.stop()

        if self._tick_count % 5 == 0:
            self.home.set_cache(len(self._cache_files()))
            self.home.set_resume(self._resume_text(
                self._current_course(), self.account.get("phone_number", "")))
        self.home.set_chips(self.timer_active, self._chip_text(),
                            bool(self.account.get("multi_device")))
        self.root.after(1000, self._tick)

    def _current_course(self) -> str:
        courses = self.account.get("cour") or [""]
        return courses[0] if courses else ""

    # ------------------------------------------------------------------
    # 日志
    # ------------------------------------------------------------------
    def log(self, text: str, level: str = "normal") -> None:
        try:
            self.logger.info(ANSI_RE.sub("", text))
        except Exception:
            pass
        self.root.after(0, self.home.log.append, text, level)

    def clear_log(self) -> None:
        self.home.log.clear()

    # ------------------------------------------------------------------
    # 刷课
    # ------------------------------------------------------------------
    def start(self) -> None:
        account = self.config.load_account() or {}
        if not account.get("phone_number"):
            messagebox.showerror("还没配置", "请先到「设置」里填写账号信息")
            return
        if self.running:
            return
        self.account = account
        phone = account.get("phone_number", "")
        courses = account.get("cour") or []
        snapshot = resume_store.snapshot(phone)
        if courses and all(snapshot.get(name, {}).get("status") == "done" for name in courses):
            if not messagebox.askyesno(
                    "课程都已标记完成",
                    "这些课程都已标记完成。要重置断点、从头再刷一遍吗？\n\n"
                    "选「否」就保持现状，不会启动。"):
                return
            resume_store.reset(phone)
            self._refresh_static()
            self.log("已重置全部断点，将重新开始", "warn")
        self.running = True
        self.started_at = time.time()
        self.errors = 0
        done, _total = self._course_process(self._current_course())
        self._baseline_done = done
        self.home.set_running(True)
        self.log(f"开始刷课：{'、'.join(account.get('cour') or [])}", "ok")
        threading.Thread(target=self._launch, daemon=True).start()

    def _launch(self) -> None:
        try:
            if self.account.get("multi_device"):
                self._launch_multi()
            else:
                self.run_program()
        except Exception as error:
            self.log(f"启动失败：{error}", "err")
            self.root.after(0, self.stop)

    def _launch_multi(self) -> None:
        courses = list(self._all_courses)
        for course in courses:
            if not self.running:
                break
            self.account["cour"] = [course]
            self.config.save_account(self.account)
            self._login_seen[course] = False
            self.run_program(course)
            deadline = time.time() + 180
            while self.running and not self._login_seen.get(course) \
                    and time.time() < deadline:
                time.sleep(0.5)
        self.account["cour"] = courses
        self.config.save_account(self.account)

    def run_program(self, course: str | None = None):
        if getattr(sys, "frozen", False):
            command = [sys.executable, "--worker"]
        else:
            command = self.account.get("file_name") or [sys.executable, "main.py"]
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        try:
            proc = subprocess.Popen(command, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, env=env)
        except Exception as error:
            self.log(f"无法启动主程序：{error}", "err")
            return None
        self.processes[proc.pid] = proc
        threading.Thread(target=self._pump, args=(proc, course), daemon=True).start()
        return proc

    def _pump(self, proc, course: str | None) -> None:
        prefix = f"[{course}] " if course else ""
        try:
            for raw in iter(proc.stdout.readline, b""):
                line = raw.decode("utf-8", "replace")
                line = ANSI_RE.sub("", line).rstrip()
                if not line.strip():
                    continue
                if "❌" in line:
                    level = "err"
                    self.errors += 1
                elif "✅" in line or "🎉" in line or "已完成" in line:
                    level = "ok"
                elif "⚠" in line or "正在" in line:
                    level = "warn"
                else:
                    level = "normal"
                self.log(prefix + line, level)
                if "正在登录中" in line and course:
                    self._login_seen[course] = True
                if "❌" in line:
                    self.root.after(0, self.stop)
                    break
        finally:
            try:
                proc.stdout.close()
            except Exception:
                pass
            try:
                proc.wait()
            except Exception:
                pass
            self.processes.pop(proc.pid, None)
            if not self.processes:
                self.root.after(0, self._worker_finished)

    def _worker_finished(self) -> None:
        """所有刷课进程退出后，把界面状态复位（避免停在「运行中」）。"""
        if self.processes:
            return
        if self.running:
            self.running = False
            self.home.set_running(False)
            self.log("刷课进程已结束", "warn")
        self._refresh_static()

    def stop(self) -> None:
        if not self.running and not self.processes:
            return
        self.running = False
        for pid, proc in list(self.processes.items()):
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                                   capture_output=True)
                else:
                    proc.terminate()
            except Exception:
                pass
        self.processes.clear()
        self.home.set_running(False)
        self.log("已结束刷课", "warn")

    # ------------------------------------------------------------------
    # 签到 / 定时 / 设置
    # ------------------------------------------------------------------
    def open_sign(self) -> None:
        account = self.config.load_account() or {}
        if not account.get("phone_number"):
            messagebox.showerror("还没配置", "请先到「设置」里填写账号信息")
            return
        if self._sign_window is not None and self._sign_window.window.winfo_exists():
            self._sign_window.window.lift()
            return
        self._sign_window = SignWindow(self.root, account)

    def open_timer(self) -> None:
        self.timer_window.open(self.timer_start, self.timer_end)

    def _on_timer_set(self, start: str, end: str) -> None:
        self.timer_start, self.timer_end = start, end
        self.timer_active = True
        account = self.config.load_account() or {}
        account["timer_start"] = start
        account["timer_end"] = end
        account["timer_active"] = 1
        self.config.save_account(account)
        self.account = account
        self.home.set_chips(True, self._chip_text(), bool(account.get("multi_device")))
        self.log(f"已开启定时：{start} → {end}", "ok")

    def _on_timer_cancel(self) -> None:
        self.timer_active = False
        account = self.config.load_account() or {}
        account["timer_active"] = 0
        self.config.save_account(account)
        self.account = account
        self.home.set_chips(False, self._chip_text(), bool(account.get("multi_device")))
        self.log("已关闭定时刷课", "warn")

    def on_settings_saved(self, account: dict) -> None:
        self.account = account
        self.timer_active = bool(account.get("timer_active"))
        self.timer_start = account.get("timer_start") or self.timer_start
        self.timer_end = account.get("timer_end") or self.timer_end
        self._refresh_static()

    def show_notice(self) -> None:
        UserNotice(self.root, on_confirm=self._notice_done,
                   on_cancel=self.root.destroy).show()

    def _notice_done(self) -> None:
        account = self.config.load_account() or {}
        account["user_notice"] = "False"
        self.config.save_account(account)
        self.account = account
        if not account.get("onboarded"):
            self.root.after(300, self.show_onboarding)

    def show_onboarding(self) -> None:
        Onboarding(self.root, self.config, self._onboarding_settings).show()

    def _onboarding_settings(self) -> None:
        self.show_page("settings")

    def on_close(self) -> None:
        self.stop()
        self.root.destroy()


if __name__ == "__main__":
    prepare_workdir()
    if "--worker" in sys.argv:
        import main as worker

        worker.run_main()
    else:
        app = App()
        for arg in sys.argv[1:]:
            if arg in app.pages:
                app.show_page(arg)
    app.root.mainloop()
