# -*- coding: utf-8 -*-
"""倍速控制：每个视频都按实际 playbackRate 校准，不再只调一次。

学习通的播放器把倍速存在 `video.playbackRate` 里，平台限制时按 d/a 也不会再涨。
所以这里先读当前值，算出还差几档，调完再回读确认，避免「日志说 8X、实际 1X」。
"""
from __future__ import annotations

import time

import pyautogui
from selenium.webdriver import ActionChains

STEP = 0.1          # 播放器按一次 d/a 增减 0.1X
MAX_STEPS = 80      # 单次最多按 80 下（8X 差额），防止死循环


def plan_steps(current: float, target: float) -> tuple[str, int]:
    """返回 (按键, 次数)。键为 'd'（加速）或 'a'（减速），已到目标返回 ('', 0)。"""
    current, target = float(current), float(target)
    diff = target - current
    if abs(diff) < STEP / 2:
        return "", 0
    steps = min(int(round(abs(diff) / STEP)), MAX_STEPS)
    return ("d" if diff > 0 else "a"), steps


def get_playback_rate(driver) -> float | None:
    """读取当前 frame 里 video 的实际倍速；读不到返回 None。"""
    try:
        value = driver.execute_script(
            "var v = document.querySelector('video');"
            "return v ? v.playbackRate : null;")
    except Exception:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def apply_speed(driver, target) -> float:
    """把当前视频调到目标倍速，返回实际倍速（读不到时返回估算值）。"""
    try:
        target = float(target or 1)
    except (TypeError, ValueError):
        target = 1.0
    current = get_playback_rate(driver)
    if current is None:
        current = 1.0
    key, steps = plan_steps(current, target)
    if not steps:
        print(f"当前倍速已是 {current:.1f}X，无需调节", flush=True)
        return current

    print(f"调节倍速：{current:.1f}X → {target:g}X", flush=True)
    # 每按 10 下回读一次，再按剩余差额重新算；这样即使一次按键涨了 0.2X
    # 或平台在中途限速，也不会多按或少按。
    for _round in range(MAX_STEPS // 10):
        key, steps = plan_steps(current, target)
        if not steps:
            break
        batch = min(steps, 10)
        for _ in range(batch):
            _press(driver, key)
        now = get_playback_rate(driver)
        if now is None:
            break
        if abs(now - current) < STEP / 2:
            print("倍速没有变化，可能被平台限制", flush=True)
            break
        current = now

    final = get_playback_rate(driver)
    if final is None:
        final = current
    if abs(final - target) < STEP / 2:
        print(f"倍速已调到 {final:.1f}X", flush=True)
    else:
        print(f"实际倍速 {final:.1f}X（目标 {target:g}X，平台可能有限制）", flush=True)
    return final
