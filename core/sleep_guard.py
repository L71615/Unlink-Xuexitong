"""阻止系统休眠/息屏的最小实现。

以前「防锁屏」是每几秒用 pyautogui 抖一下鼠标，会打断用户正常用电脑，
也会和自动化点击抢焦点。这里改成调用 Windows 原生
``SetThreadExecutionState``：只对当前线程声明「系统与显示器需要保持唤醒」，
不移动鼠标、不抢焦点、不需要管理员。

非 Windows 平台直接返回 False，调用方不需要分支。
"""
from __future__ import annotations

import ctypes
import sys

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

_active = False


def _kernel32():
    if not sys.platform.startswith("win"):
        return None
    try:
        return ctypes.windll.kernel32
    except Exception:
        return None


def keep_display_awake() -> bool:
    """申请「系统与显示器保持唤醒」，可重复调用；返回是否生效。"""
    global _active
    kernel32 = _kernel32()
    if kernel32 is None:
        return False
    try:
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        result = kernel32.SetThreadExecutionState(flags)
    except Exception:
        return False
    if result:
        _active = True
        return True
    return False


def release_display_awake() -> bool:
    """撤销唤醒申请，让系统恢复正常的休眠策略。"""
    global _active
    kernel32 = _kernel32()
    if kernel32 is None or not _active:
        return False
    try:
        kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    except Exception:
        return False
    _active = False
    return True
