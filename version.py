# -*- coding: utf-8 -*-
"""版本与程序名的唯一来源。

要发新版本只改这里的 APP_VERSION：界面标题、资源释放标记、打包产物名、
exe 文件属性里的版本号全部跟着走，不用再翻别的文件。
"""

APP_NAME = "课业助手"
EXE_NAME = "课业助手"
APP_VERSION = "1.1.4"


def version_tuple() -> tuple[int, int, int, int]:
    """PyInstaller 版本文件用的四段式版本号（1.1.0 -> (1, 1, 0, 0)）。"""
    parts: list[int] = []
    for piece in APP_VERSION.split(".")[:3]:
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2], 0
