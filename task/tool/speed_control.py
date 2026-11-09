# -*- coding: utf-8 -*-
"""倍速控制：直接改 video.playbackRate，并挂守卫防止播放器把速度弹回 1.0X。

学习通的播放器把倍速存在 ``video.playbackRate`` 里。老做法是模拟按 d/a 键，
但这要求播放器窗口有焦点、并且播放器自己监听了键盘事件——新版 vjs 控制条
往往不响应，于是出现「日志说调到 2X、实际还是 1X」。

现在改成三层：
1. 用 JS 直接写 ``playbackRate``（不依赖焦点，也不依赖扩展是否加载成功）；
2. 给 video 挂 ``ratechange``/``play`` 钩子 + 1 秒定时器，把被平台弹回去的速度再压回去；
3. JS 无效时才退回按键，作为最后的兜底。
"""
from __future__ import annotations

import time

import pyautogui
from selenium.webdriver import ActionChains

STEP = 0.1          # 播放器按一次 d/a 增减 0.1X
MAX_STEPS = 80      # 单次最多按 80 下（8X 差额），防止死循环
TOLERANCE = 0.05    # 回读值与目标的允许误差

# 找到 video（当前文档找不到就递归找同源 iframe），把目标倍速写进去并挂守卫。
_SET_RATE_JS = r"""
var target = arguments[0];
window.__xxt_rate_target = target;

function pickVideo(doc, depth) {
  var v = doc.querySelector('video');
  if (v) return v;
  if (depth <= 0) return null;
  var frames = doc.querySelectorAll('iframe');
  for (var i = 0; i < frames.length; i++) {
    try {
      var found = pickVideo(frames[i].contentDocument, depth - 1);
      if (found) return found;
    } catch (e) {}
  }
  return null;
}

function enforce(v) {
  var t = window.__xxt_rate_target;
  if (!t || !v) return;
  try { v.defaultPlaybackRate = t; } catch (e) {}
  if (Math.abs(v.playbackRate - t) > 0.01) {
    try { v.playbackRate = t; } catch (e) {}
  }
  if (!v.__xxt_rate_hooked) {
    v.__xxt_rate_hooked = true;
    var push = function () {
      var t2 = window.__xxt_rate_target;
      if (t2 && Math.abs(this.playbackRate - t2) > 0.01) {
        try { this.playbackRate = t2; } catch (e) {}
      }
    };
    v.addEventListener('ratechange', push);
    v.addEventListener('play', push);
    v.addEventListener('playing', push);
  }
}

var video = pickVideo(document, 2);
if (!video) return null;
enforce(video);
if (!window.__xxt_rate_timer) {
  window.__xxt_rate_timer = setInterval(function () {
    var v = pickVideo(document, 2);
    if (v) enforce(v);
  }, 1000);
}
return video.playbackRate;
"""

# 只读：返回 {rate, count}，读不到 video 时返回 null。
_READ_RATE_JS = r"""
function pickVideo(doc, depth) {
  var v = doc.querySelector('video');
  if (v) return v;
  if (depth <= 0) return null;
  var frames = doc.querySelectorAll('iframe');
  for (var i = 0; i < frames.length; i++) {
    try {
      var found = pickVideo(frames[i].contentDocument, depth - 1);
      if (found) return found;
    } catch (e) {}
  }
  return null;
}
var v = pickVideo(document, 2);
if (!v) return null;
return {rate: v.playbackRate, count: document.querySelectorAll('video').length};
"""


def plan_steps(current: float, target: float) -> tuple[str, int]:
    """返回 (按键, 次数)。键为 'd'（加速）或 'a'（减速），已到目标返回 ('', 0)。"""
    current, target = float(current), float(target)
    diff = target - current
    if abs(diff) < STEP / 2:
        return "", 0
    steps = min(int(round(abs(diff) / STEP)), MAX_STEPS)
    return ("d" if diff > 0 else "a"), steps


def _as_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_playback_rate(driver) -> float | None:
    """读取当前 frame 里 video 的实际倍速；读不到返回 None（不再假装 1.0X）。"""
    try:
        value = driver.execute_script(_READ_RATE_JS)
    except Exception:
        return None
    if isinstance(value, dict):
        return _as_float(value.get("rate"))
    return _as_float(value)


def set_playback_rate(driver, target: float) -> float | None:
    """直接写 playbackRate 并挂防回弹守卫；成功返回写入后的回读值。"""
    try:
        value = driver.execute_script(_SET_RATE_JS, float(target))
    except Exception as error:
        print(f"倍速 JS 注入失败：{error}", flush=True)
        return None
    return _as_float(value)


def _press(driver, key: str) -> None:
    try:
        pyautogui.press(key)
    except Exception:
        pass
    try:
        ActionChains(driver).send_keys(key).perform()
    except Exception:
        pass
    time.sleep(0.08)


def _press_to(driver, current: float, target: float) -> float | None:
    """按键兜底：按下差额次数，每 10 下回读一次。返回最后一次回读值。"""
    now = current
    for _round in range(MAX_STEPS // 10):
        key, steps = plan_steps(now, target)
        if not steps:
            return now
        for _ in range(min(steps, 10)):
            _press(driver, key)
        read = get_playback_rate(driver)
        if read is None:
            return None
        if abs(read - now) < STEP / 2:
            return read
        now = read
    return now


def apply_speed(driver, target) -> float:
    """把当前视频调到目标倍速，返回实际倍速。"""
    target = _as_float(target) or 1.0
    before = get_playback_rate(driver)
    written = set_playback_rate(driver, target)
    if written is not None and abs(written - target) <= TOLERANCE:
        print(f"倍速已设置 {written:.1f}X（已挂防回弹守卫）", flush=True)
        return written

    # JS 没写上，退回按键；再不行就如实报告，不再谎报成功
    start = written if written is not None else (before if before is not None else 1.0)
    after = _press_to(driver, start, target)
    final = get_playback_rate(driver)
    if final is None:
        final = after
    if final is None:
        print(f"读不到播放器状态（目标 {target:g}X），本轮跳过倍速校准", flush=True)
        return target
    if abs(final - target) <= TOLERANCE:
        print(f"倍速已调到 {final:.1f}X", flush=True)
    else:
        print(f"实际倍速 {final:.1f}X（目标 {target:g}X，JS 与按键都未生效）", flush=True)
    return final
