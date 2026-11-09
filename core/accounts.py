# -*- coding: utf-8 -*-
"""多账号簿：保存多个学习通账号，切换时只改「当前账号」。

设计要点：
- ``task/tool/account_info.json`` 仍然是「当前生效账号」的唯一真相，
  刷课流程、断点、cookie、课程列表全都以它为准；
- 本文件（``task/tool/accounts.json``）只是账号名录，切换 = 把某个账号的
  手机号/密码写回 ``account_info.json``；
- 密码用 Windows DPAPI 加密后存盘（只有本机当前用户能解），
  在非 Windows 或加密失败时退化为明文，并在文件里标明方式。
"""
from __future__ import annotations

import base64
import json
import os
import sys
import threading
import time

PATH = os.path.join("task", "tool", "accounts.json")
_lock = threading.RLock()

_DPAPI_PREFIX = "dpapi:"
_PLAIN_PREFIX = "plain:"


# ---------------------------------------------------------------------------
# DPAPI（不依赖 pywin32，直接用 ctypes 调 CryptProtectData）
# ---------------------------------------------------------------------------
def _load_ctypes():
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_char))]

    def to_blob(data: bytes):
        buffer = ctypes.create_string_buffer(data, len(data))
        return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer

    return ctypes, DATA_BLOB, to_blob


def protect(text: str) -> str:
    """加密密码，返回带前缀的字符串。"""
    if not text:
        return ""
    if sys.platform != "win32":
        return _PLAIN_PREFIX + text
    try:
        ctypes, DATA_BLOB, to_blob = _load_ctypes()
        entropy = b"XuexitongShuake"
        blob_in, keep_in = to_blob(text.encode("utf-8"))
        blob_entropy, keep_entropy = to_blob(entropy)
        blob_out = DATA_BLOB()
        ok = ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(blob_in), None, ctypes.byref(blob_entropy),
            None, None, 0, ctypes.byref(blob_out))
        if not ok:
            return _PLAIN_PREFIX + text
        try:
            raw = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return _DPAPI_PREFIX + base64.b64encode(raw).decode("ascii")
    except Exception:
        return _PLAIN_PREFIX + text


def unprotect(token: str) -> str:
    """解密密码；无法解密（换了机器/换了用户）时返回空字符串。"""
    if not token:
        return ""
    if token.startswith(_PLAIN_PREFIX):
        return token[len(_PLAIN_PREFIX):]
    if not token.startswith(_DPAPI_PREFIX):
        return token
    if sys.platform != "win32":
        return ""
    try:
        ctypes, DATA_BLOB, to_blob = _load_ctypes()
        raw = base64.b64decode(token[len(_DPAPI_PREFIX):])
        blob_in, keep_in = to_blob(raw)
        blob_entropy, keep_entropy = to_blob(b"XuexitongShuake")
        blob_out = DATA_BLOB()
        ok = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, ctypes.byref(blob_entropy),
            None, None, 0, ctypes.byref(blob_out))
        if not ok:
            return ""
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData).decode("utf-8")
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# 文件读写
# ---------------------------------------------------------------------------
def _read() -> dict:
    try:
        with open(PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"version": 1, "current": "", "items": []}
    if not isinstance(data, dict):
        return {"version": 1, "current": "", "items": []}
    data.setdefault("version", 1)
    data.setdefault("current", "")
    items = data.get("items")
    data["items"] = items if isinstance(items, list) else []
    return data


def _write(data: dict) -> bool:
    tmp = PATH + ".tmp"
    with _lock:
        try:
            os.makedirs(os.path.dirname(PATH), exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
            os.replace(tmp, PATH)
            return True
        except OSError:
            return False


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------
def items() -> list[dict]:
    """账号列表，按最近使用时间倒序。"""
    data = _read()
    return sorted(data["items"], key=lambda it: it.get("last_used") or "", reverse=True)


def phones() -> list[str]:
    return [it.get("phone", "") for it in items() if it.get("phone")]


def get(phone: str) -> dict:
    for item in _read()["items"]:
        if item.get("phone") == phone:
            return dict(item)
    return {}


def current() -> str:
    return _read().get("current", "")


def password_of(phone: str) -> str:
    return unprotect(get(phone).get("password", ""))


def upsert(phone: str, password: str = "", label: str = "", course_label: str = "") -> bool:
    """新增或更新一个账号；密码为空时保留旧密码。"""
    phone = (phone or "").strip()
    if not phone:
        return False
    with _lock:
        data = _read()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        found = None
        for item in data["items"]:
            if item.get("phone") == phone:
                found = item
                break
        if found is None:
            found = {"phone": phone, "label": label or phone}
            data["items"].append(found)
        if password:
            found["password"] = protect(password)
        if label:
            found["label"] = label
        if course_label:
            found["course_label"] = course_label
        found["last_used"] = now
        data["current"] = phone
        return _write(data)


def remove(phone: str) -> bool:
    with _lock:
        data = _read()
        before = len(data["items"])
        data["items"] = [it for it in data["items"] if it.get("phone") != phone]
        if data.get("current") == phone:
            data["current"] = data["items"][0].get("phone", "") if data["items"] else ""
        return _write(data) if len(data["items"]) != before else True


def set_current(phone: str) -> bool:
    with _lock:
        data = _read()
        data["current"] = phone or ""
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        for item in data["items"]:
            if item.get("phone") == phone:
                item["last_used"] = now
        return _write(data)


def migrate_from_account_info(account: dict) -> None:
    """首次升级时，把 account_info.json 里的账号登记进账号簿。"""
    phone = (account or {}).get("phone_number", "").strip()
    if not phone or get(phone):
        return
    upsert(phone, account.get("password", ""), label=phone)
