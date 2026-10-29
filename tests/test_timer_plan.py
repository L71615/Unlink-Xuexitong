# -*- coding: utf-8 -*-
"""定时窗口计算测试。"""
import unittest
from datetime import date, datetime, timedelta

from core import timer_plan


class ParseTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(timer_plan.parse_hms("04:00"), timer_plan.parse_hms("04:00:00"))
        self.assertEqual(timer_plan.parse_hms("23:59:59").hour, 23)

    def test_parse_invalid(self):
        for value in ("", "24:00", "04:60", "abc", None, "4"):
            self.assertIsNone(timer_plan.parse_hms(value))


class WindowTests(unittest.TestCase):
    def test_normal_window(self):
        now = datetime(2026, 10, 29, 4, 0, 30)
        start, end = timer_plan.window(now, "04:00", "06:00")
        self.assertEqual(start, datetime(2026, 10, 29, 4, 0))
        self.assertEqual(end, datetime(2026, 10, 29, 6, 0))
        self.assertTrue(timer_plan.in_window(now, "04:00", "06:00"))
        self.assertFalse(timer_plan.in_window(datetime(2026, 10, 29, 6, 0), "04:00", "06:00"))

    def test_overnight_early_morning_belongs_to_previous_day(self):
        now = datetime(2026, 10, 29, 1, 0)
        start, end = timer_plan.window(now, "22:00", "06:00")
        self.assertEqual(start, datetime(2026, 10, 28, 22, 0))
        self.assertEqual(end, datetime(2026, 10, 29, 6, 0))
        self.assertTrue(timer_plan.in_window(now, "22:00", "06:00"))

    def test_overnight_morning_after_end_is_next_window(self):
        now = datetime(2026, 10, 29, 7, 0)
        start, end = timer_plan.window(now, "22:00", "06:00")
        self.assertEqual(start, datetime(2026, 10, 29, 22, 0))
        self.assertEqual(end, datetime(2026, 10, 30, 6, 0))
        self.assertFalse(timer_plan.in_window(now, "22:00", "06:00"))

    def test_equal_start_end_treated_as_full_day(self):
        now = datetime(2026, 10, 29, 12, 0)
        start, end = timer_plan.window(now, "04:00", "04:00")
        self.assertEqual(start, datetime(2026, 10, 29, 4, 0))
        self.assertEqual(end, datetime(2026, 10, 30, 4, 0))


class DueTests(unittest.TestCase):
    def test_due_in_window(self):
        now = datetime(2026, 10, 29, 4, 5)
        fire, start, end = timer_plan.due(now, "04:00", "06:00")
        self.assertTrue(fire)
        self.assertEqual(start, datetime(2026, 10, 29, 4, 0))
        self.assertEqual(end, datetime(2026, 10, 29, 6, 0))

    def test_catch_up_late_start(self):
        now = datetime(2026, 10, 29, 5, 30)
        fire, _start, _end = timer_plan.due(now, "04:00", "06:00")
        self.assertTrue(fire, "窗口内晚到也应该补跑")

    def test_not_due_twice_same_cycle(self):
        now = datetime(2026, 10, 29, 4, 5)
        fire, start, _end = timer_plan.due(now, "04:00", "06:00", last_cycle=date(2026, 10, 29))
        self.assertFalse(fire)
        self.assertEqual(start, datetime(2026, 10, 29, 4, 0))

    def test_not_due_after_end(self):
        now = datetime(2026, 10, 29, 6, 0)
        fire, _start, _end = timer_plan.due(now, "04:00", "06:00")
        self.assertFalse(fire)

    def test_invalid_times_never_fire(self):
        fire, start, end = timer_plan.due(datetime(2026, 10, 29, 4, 0), "xx", "06:00")
        self.assertFalse(fire)
        self.assertIsNone(start)
        self.assertIsNone(end)


class NextStartTests(unittest.TestCase):
    def test_before_start(self):
        now = datetime(2026, 10, 29, 2, 0)
        self.assertEqual(timer_plan.next_start(now, "04:00", "06:00"),
                         datetime(2026, 10, 29, 4, 0))

    def test_inside_window_points_to_tomorrow(self):
        now = datetime(2026, 10, 29, 4, 30)
        self.assertEqual(timer_plan.next_start(now, "04:00", "06:00"),
                         datetime(2026, 10, 30, 4, 0))

    def test_overnight_after_end(self):
        now = datetime(2026, 10, 29, 7, 0)
        self.assertEqual(timer_plan.next_start(now, "22:00", "06:00"),
                         datetime(2026, 10, 29, 22, 0))

    def test_remaining_text(self):
        self.assertEqual(timer_plan.remaining_text(timedelta(hours=3, minutes=12)), "3 小时 12 分")
        self.assertEqual(timer_plan.remaining_text(timedelta(minutes=5)), "5 分钟")
        self.assertEqual(timer_plan.remaining_text(timedelta(seconds=20)), "不到 1 分钟")


if __name__ == "__main__":
    unittest.main()
