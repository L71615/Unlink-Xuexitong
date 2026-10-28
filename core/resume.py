# -*- coding: utf-8 -*-
"""断点续刷：记录每门课的运行状态和最后刷到的章节。

状态文件：task/tool/resume_state.json
{
  "accounts": {
    "138****": {
      "大学生安全教育⑦": {
        "status": "running",          # running / done / error
        "chapter": "第 3 章 ...",
        "updated_at": "2026-10-28 15:20:01",
        "message": ""
      }
    }
  }
}
"""
from __future__ import annotations

import json
import os
import threading
import time

PATH = os.path.join("task", "tool", "resume_state.json")
_lock = threading.RLock()


def _read() -> dict:
    try:
        with open(PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _write(data: dict) -> None:
    tmp = PATH + ".tmp"
    with _lock:
        try:
            os.makedirs(os.path.dirname(PATH), exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
            os.replace(tmp, PATH)
        except OSError:
            pass


def snapshot(phone: str) -> dict:
    """读取某个账号下所有课程的状态（给界面用）。"""
    data = _read()
    return dict(data.get("accounts", {}).get(phone or "", {}))


def reset(phone: str, course: str | None = None) -> None:
    """清掉某门课（或整个账号）的断点。"""
    data = _read()
    accounts = data.setdefault("accounts", {})
    if course is None:
        accounts.pop(phone or "", None)
    else:
        accounts.get(phone or "", {}).pop(course, None)
    _write(data)


class Resume:
    """刷课进程里用的断点记录器。"""

    def __init__(self, phone: str = ""):
        self.phone = phone or "default"

    # ------------------------------------------------------------------
    def _bucket(self, data: dict) -> dict:
        return data.setdefault("accounts", {}).setdefault(self.phone, {})

    def info(self, course: str) -> dict:
        return snapshot(self.phone).get(course, {})

    def status(self, course: str) -> str:
        return self.info(course).get("status", "")

    def is_done(self, course: str) -> bool:
        return self.status(course) == "done"

    def skip_done(self, courses: list[str]) -> list[str]:
        """过滤已完成课程；正在进行的课程排到最前面。"""
        alive = [name for name in courses if not self.is_done(name)]
        running = [name for name in alive if self.status(name) == "running"]
        rest = [name for name in alive if name not in running]
        return running + rest

    # ------------------------------------------------------------------
    def _update(self, course: str, **fields) -> None:
        data = _read()
        bucket = self._bucket(data)
        info = bucket.setdefault(course, {})
        info.update(fields)
        info["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _write(data)

    def touch(self, course: str, chapter: str = "") -> None:
        """标记课程进行中，并记录当前章节。"""
        info = self.info(course)
        if info.get("status") == "running" and info.get("chapter") == chapter:
            # 章节没变就不重复写盘，减少 IO
            return
        self._update(course, status="running", chapter=chapter or info.get("chapter", ""),
                     message="")

    def mark_done(self, course: str, message: str = "") -> None:
        self._update(course, status="done", message=message)

    def mark_error(self, course: str, message: str = "") -> None:
        self._update(course, status="error", message=message)
