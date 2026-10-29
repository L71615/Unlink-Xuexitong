# -*- coding: utf-8 -*-
"""定时刷课的时间计算。

界面每秒 tick 一次，用 ``now == "04:00:00"`` 判断会漏触发；
这里把「开始/结束」换算成时间窗，支持跨天和错过补跑：

- 窗口从 start 开始，到 end 结束；end <= start 视为跨天；
- 当前时刻落在窗口内且今天这个窗口还没启动过，就算到期；
- 凌晨仍在昨天开始的跨天窗口里时，归到昨天那一轮。
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta


def parse_hms(value: str) -> time | None:
    """把 ``HH:MM`` / ``HH:MM:SS`` 解析成 time，非法返回 None。"""
    try:
        parts = [int(part) for part in str(value).strip().split(":")]
    except (TypeError, ValueError):
        return None
    if len(parts) == 2:
        parts.append(0)
    if len(parts) != 3:
        return None
    hour, minute, second = parts
    if not (0 <= hour < 24 and 0 <= minute < 60 and 0 <= second < 60):
        return None
    return time(hour, minute, second)


def window(now: datetime, start: str, end: str) -> tuple[datetime, datetime] | None:
    """返回 ``now`` 所在（或接下来最近）的定时窗口。"""
    start_clock = parse_hms(start)
    end_clock = parse_hms(end)
    if start_clock is None or end_clock is None:
        return None

    start_dt = datetime.combine(now.date(), start_clock)
    end_dt = datetime.combine(now.date(), end_clock)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)

    if now < start_dt:
        prev_start = start_dt - timedelta(days=1)
        prev_end = end_dt - timedelta(days=1)
        # 凌晨还在昨天 22:00 开始、今天 06:00 结束的窗口里
        if prev_end > now:
            return prev_start, prev_end
        return start_dt, end_dt
    return start_dt, end_dt


def in_window(now: datetime, start: str, end: str) -> bool:
    bounds = window(now, start, end)
    return bool(bounds and bounds[0] <= now < bounds[1])


def due(now: datetime, start: str, end: str,
        last_cycle: date | None = None) -> tuple[bool, datetime | None, datetime | None]:
    """判断现在是否该启动。

    返回 ``(是否到期, 本轮开始时间, 本轮结束时间)``。
    ``last_cycle`` 是本轮开始日期，用来防止同一天重复启动。
    """
    bounds = window(now, start, end)
    if bounds is None:
        return False, None, None
    start_dt, end_dt = bounds
    if start_dt <= now < end_dt and last_cycle != start_dt.date():
        return True, start_dt, end_dt
    return False, start_dt, end_dt


def next_start(now: datetime, start: str, end: str) -> datetime | None:
    """下一次会启动的时间；当前已在窗口内则返回明天这一轮。"""
    bounds = window(now, start, end)
    if bounds is None:
        return None
    start_dt, _end_dt = bounds
    if now < start_dt:
        return start_dt
    return start_dt + timedelta(days=1)


def remaining_text(delta: timedelta) -> str:
    """把剩余时间写成 ``3 小时 12 分`` 这类短文本。"""
    total = max(int(delta.total_seconds()), 0)
    hours, rest = divmod(total, 3600)
    minutes = rest // 60
    if hours:
        return f"{hours} 小时 {minutes:02d} 分"
    if minutes:
        return f"{minutes} 分钟"
    return "不到 1 分钟"
