# -*- coding: utf-8 -*-
"""任务点级断点：记录每门课最近所在的章节页、任务点 URL 和播放位置。

状态文件：task/tool/point_state.json
{
  "points": {
    "18133021033::大学生安全教育⑦": {
      "chapter_url": "https://mooc1.chaoxing.com/mycourse/studentstudy?...",
      "point_url":   "https://mooc1.chaoxing.com/ananas/modules/video/index.html?...&objectid=xxx",
      "point_time":  623.5,
      "updated_at":  "2026-11-09 12:30:00"
    }
  }
}

做法是「记录现场、回到现场」：URL 都是从真实页面读出来的，不靠猜
选择器，所以对不同章节模板都成立。
"""
from __future__ import annotations

import json
import os
import threading
import time

PATH = "task/tool/point_state.json"
_lock = threading.RLock()
_account = ""

SEEK_JS = ("var v=document.querySelector('video');"
           "if(v){try{v.currentTime=arguments[0];}catch(e){}}"
           "return v?v.currentTime:null;")


class _Unset:
    def __repr__(self):
        return "<unset>"


_UNSET = _Unset()


def set_account(phone: str) -> None:
    """刷课开始前调用；不同账号的断点互不干扰。"""
    global _account
    _account = (phone or "").strip() or "default"


def _key(course: str) -> str:
    return f"{_account or 'default'}::{course}"


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


def get(course: str) -> dict:
    data = _read()
    points = data.get("points", {})
    if not isinstance(points, dict):
        return {}
    info = points.get(_key(course), {})
    return dict(info) if isinstance(info, dict) else {}


def clear(course: str | None = None) -> None:
    """清掉一门课（或当前账号全部）的播放位置记录。"""
    data = _read()
    points = data.setdefault("points", {})
    if course:
        points.pop(_key(course), None)
    else:
        prefix = (_account or "default") + "::"
        for key in [k for k in points if k.startswith(prefix)]:
            points.pop(key, None)
    _write(data)


def _save(course: str, **fields) -> None:
    data = _read()
    points = data.setdefault("points", {})
    info = points.setdefault(_key(course), {})
    info.update(fields)
    info["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _write(data)


# ----------------------------------------------------------------------
# 章节页 URL
# ----------------------------------------------------------------------
def record_chapter(course: str, url: str) -> None:
    """记下当前章节页地址（用于下次直接回到这一章）。"""
    url = (url or "").strip()
    if not url or "chaoxing.com" not in url:
        return
    if "/mycourse/studentstudy" not in url and "knowledge/cards" not in url:
        return
    if get(course).get("chapter_url") == url:
        return
    _save(course, chapter_url=url, point_url="", point_time=0)


def chapter_url(course: str) -> str:
    return str(get(course).get("chapter_url") or "")


# ----------------------------------------------------------------------
# 视频播放位置
# ----------------------------------------------------------------------
def here(driver) -> str:
    """当前 frame 的地址；播放器 iframe 的地址里带 objectid，可当任务点标识。"""
    try:
        return driver.execute_script("return location.href;") or ""
    except Exception:
        return ""


def _seconds(text: str) -> float:
    """把播放器显示的 12:03 / 1:02:03 转成秒。"""
    text = (text or "").strip()
    if not text:
        return 0.0
    parts = text.split(":")
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        return 0.0
    total = 0.0
    for value in parts:
        total = total * 60 + value
    return total


def _fmt(seconds: float) -> str:
    seconds = int(max(0, seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def restore(driver, course: str, point_url: str) -> float:
    """如果当前视频就是上次没看完的那个，跳回上次的位置。"""
    info = get(course)
    saved_url = str(info.get("point_url") or "")
    position = float(info.get("point_time") or 0)
    if not saved_url or not point_url or saved_url != point_url or position <= 5:
        return 0.0
    try:
        driver.execute_script(SEEK_JS, position)
    except Exception:
        return 0.0
    print(f"从上次看到的位置继续播放：{_fmt(position)}", flush=True)
    return position


def save_point(course: str, current_text: str, point_url: str = "") -> None:
    """播放中定期记录位置；换任务点时自动归零，避免把位置带串。"""
    position = _seconds(current_text)
    if position <= 0:
        return
    info = get(course)
    saved_url = str(info.get("point_url") or "")
    if point_url and saved_url and saved_url != point_url:
        _save(course, point_url=point_url, point_time=position)
        return
    last = float(info.get("point_time") or 0)
    if 0 <= position - last < 8:
        return
    _save(course, point_url=point_url or saved_url, point_time=position)
