# -*- coding: utf-8 -*-
"""在线更新：查 GitHub Release → 下载 zip → 交给批处理替换自身 → 重启。

为什么不自己替换自己：Windows 不允许覆盖正在运行的 exe，也不允许覆盖已被
进程加载的 ``_internal/*.dll``。所以先解压到临时目录，再写一个**纯 ASCII**
的 ``apply.cmd``：它等本进程退出后 robocopy 覆盖安装目录，最后启动新 exe。

批处理里不写任何中文——cmd 按系统代码页（936）读文件，UTF-8 中文会变乱码。
中文路径一律走命令行参数（``%~1`` / ``%~3``）传入，cmd 参数本身支持 Unicode。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass

from version import APP_VERSION

REPO = "L71615/Unlink-Xuexitong"
LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
USER_AGENT = "CourseHelper-Updater"
WORK_DIR_NAME = "CourseHelper-update"
# 发布包的固定命名，API 被限流时靠它拼下载地址
ASSET_TEMPLATE = "CourseHelper-{version}-win64.zip"

DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200

# 纯 ASCII：%~dp0 = 脚本所在目录，%~1 = 安装目录，%~2 = 旧进程 PID，%~3 = exe 全路径
APPLY_SCRIPT = r"""@echo off
setlocal EnableExtensions EnableDelayedExpansion
set /a WAIT=0
:wait
tasklist /FI "PID eq %~2" 2>nul | find "%~2" >nul
if not errorlevel 1 (
  if !WAIT! lss 120 (
    ping -n 2 127.0.0.1 >nul
    set /a WAIT+=1
    goto wait
  )
)
ping -n 4 127.0.0.1 >nul
set /a TRIES=0
:copy
robocopy "%~dp0payload" "%~1" /E /R:3 /W:1 /NFL /NDL /NJH /NJS >nul
if errorlevel 8 (
  set /a TRIES+=1
  if !TRIES! lss 10 (
    ping -n 3 127.0.0.1 >nul
    goto copy
  )
)
del "%~1\.assets_version" >nul 2>&1
if exist "%~3" start "" "%~3"
:end
(goto) 2>nul & del "%~f0"
"""


class UpdateError(RuntimeError):
    """更新流程中的可预期失败，消息直接展示给用户。"""


@dataclass(frozen=True)
class Release:
    version: str
    zip_url: str
    notes: str = ""
    size: int = 0
    file_name: str = ""


def parse_version(text: str) -> tuple[int, int, int]:
    """从 ``v1.4.0`` / ``1.4.0`` / ``1.4`` 里取出三段版本，取不到按 0 处理。"""
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", str(text or ""))
    if not match:
        return (0, 0, 0)
    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch or 0))


def is_newer(remote: str, current: str = APP_VERSION) -> bool:
    return parse_version(remote) > parse_version(current)


def can_self_update() -> bool:
    """只有打包版才能替换自身；源码运行请 git pull。"""
    return bool(getattr(sys, "frozen", False))


def work_dir() -> str:
    return os.path.join(tempfile.gettempdir(), WORK_DIR_NAME)


def check_latest(timeout: float = 12.0) -> Release | None:
    """请求最新 Release；有新版本返回 Release，已是最新返回 None。"""
    try:
        return _check_via_api(timeout)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        pass
    # 未登录的 GitHub API 每小时只有 60 次额度，撞上限时退回读网页的 302 跳转
    try:
        tag = _tag_from_redirect(timeout)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return None
    if not tag:
        return None
    return _release_from_tag(tag)


def _check_via_api(timeout: float) -> Release | None:
    request = urllib.request.Request(
        LATEST_API,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    tag = str(data.get("tag_name") or "")
    if not is_newer(tag, APP_VERSION):
        return None
    for asset in data.get("assets") or []:
        name = str(asset.get("name") or "")
        if not name.lower().endswith(".zip"):
            continue
        url = str(asset.get("browser_download_url") or "")
        if not url:
            continue
        return Release(tag.lstrip("vV"), url, str(data.get("body") or ""),
                       int(asset.get("size") or 0), name)
    raise UpdateError("最新版本没有上传 zip 安装包")


def _tag_from_redirect(timeout: float = 12.0) -> str:
    """不走 API 也能拿到最新 tag：读 ``releases/latest`` 的跳转目标。"""
    request = urllib.request.Request(RELEASES_PAGE, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        final = response.geturl()
    tag = (final or "").rstrip("/").rsplit("/", 1)[-1]
    return tag if tag[:1] in ("v", "V") else ""


def _release_from_tag(tag: str) -> Release | None:
    """没有 API 数据时按发布命名规则拼出下载地址。"""
    version = tag.lstrip("vV")
    if not is_newer(version, APP_VERSION):
        return None
    name = ASSET_TEMPLATE.format(version=version)
    url = f"https://github.com/{REPO}/releases/download/{tag}/{name}"
    return Release(version, url, "", 0, name)


def download(url: str, dest: str, progress=None, timeout: float = 30.0) -> str:
    """下载到 dest；progress(done, total) 会在每块数据后回调一次。"""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    folder = os.path.dirname(dest)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with open(dest, "wb") as handle:
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                done += len(chunk)
                if progress is not None:
                    progress(done, total)
    return dest


def _single_top(names: list[str]) -> str:
    """zip 里所有条目都在同一个顶层目录下时返回该目录名，否则返回空串。"""
    cleaned = [name.replace("\\", "/").strip("/") for name in names]
    cleaned = [name for name in cleaned if name]
    if not cleaned:
        return ""
    tops = {name.split("/")[0] for name in cleaned}
    if len(tops) != 1:
        return ""
    top = tops.pop()
    if not all(name.startswith(top + "/") for name in cleaned):
        return ""  # 顶层只有一个文件，没有目录可剥
    return top


def extract_from(source, dest: str) -> str:
    """解压并剥掉 zip 的顶层目录（发布包是 ``课业助手/...``）。

    source 可以是 zip 路径，也可以是已经打开的文件对象。
    """
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(source) as archive:
        top = _single_top([item.filename for item in archive.infolist()])
        for item in archive.infolist():
            name = item.filename.replace("\\", "/").strip("/")
            if not name or item.is_dir():
                continue
            if top:
                if name == top:
                    continue
                if name.startswith(top + "/"):
                    name = name[len(top) + 1:]
            target = os.path.join(dest, *name.split("/"))
            parent = os.path.dirname(target)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with archive.open(item) as handle, open(target, "wb") as output:
                shutil.copyfileobj(handle, output)
    return dest


def extract(zip_path: str, dest: str) -> str:
    return extract_from(zip_path, dest)


# 发布包里带着空模板、但更新时必须保留用户本机数据的文件
RUNTIME_FILES = ("course_process.json", "account_info.json", "accounts.json",
                 "输出记录.log", "error.log")


def _strip_runtime(payload: str) -> None:
    """删掉 payload 里的运行时数据，避免 robocopy 把它们覆盖成空模板。

    ``build_exe.py`` 会往包里塞一个空的 ``task/tool/course_process.json``；
    直接复制过去等于把用户的刷课进度清零。
    """
    tool_dir = os.path.join(payload, "task", "tool")
    for name in RUNTIME_FILES:
        path = os.path.join(tool_dir, name)
        if os.path.isfile(path):
            os.remove(path)


def prepare_update(release: Release, progress=None) -> str:
    """下载并解压到 ``%TEMP%\\CourseHelper-update``，返回 payload 目录。"""
    root = work_dir()
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root, exist_ok=True)
    archive = os.path.join(root, "package.zip")
    download(release.zip_url, archive, progress)
    payload = os.path.join(root, "payload")
    extract(archive, payload)
    if not os.path.isdir(payload) or not os.listdir(payload):
        raise UpdateError("安装包解压后是空的，可能下载不完整")
    _strip_runtime(payload)
    return payload


def _detached_flags() -> int:
    """给更新脚本一个隐藏的控制台。

    不能用 DETACHED_PROCESS：没有控制台时 tasklist/ping/robocopy 这些
    控制台程序的管道会挂住，脚本卡死。CREATE_NO_WINDOW 有控制台但不显示窗口。
    """
    if os.name != "nt":
        return 0
    return CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP


def apply_update(payload: str, app_dir: str, exe_path: str) -> str:
    """写 apply.cmd 并启动它；调用方随后必须立即退出程序。"""
    if os.name != "nt":
        raise UpdateError("自动更新目前只支持 Windows")
    folder = os.path.dirname(payload) or work_dir()
    script = os.path.join(folder, "apply.cmd")
    with open(script, "w", encoding="ascii", newline="\r\n") as handle:
        handle.write(APPLY_SCRIPT)
    subprocess.Popen(
        ["cmd.exe", "/c", script, app_dir, str(os.getpid()), exe_path],
        cwd=folder, close_fds=True, creationflags=_detached_flags())
    return script


def install(release: Release, app_dir: str | None = None,
            exe_path: str | None = None, progress=None) -> str:
    """完整流程：下载 → 解压 → 启动替换脚本。返回脚本路径。"""
    app_dir = app_dir or os.path.dirname(os.path.abspath(sys.executable))
    exe_path = exe_path or sys.executable
    payload = prepare_update(release, progress)
    return apply_update(payload, app_dir, exe_path)


def open_release_page() -> None:
    """打不开 GitHub 时让用户自己去下载页。"""
    import webbrowser

    webbrowser.open(RELEASES_PAGE)


def summarize_notes(notes: str, limit: int = 200) -> str:
    """更新说明太长时截断，弹窗里放得下。"""
    text = re.sub(r"\s*\n\s*", " · ", str(notes or "")).strip()
    return text[:limit] + ("…" if len(text) > limit else "")
