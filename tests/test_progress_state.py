# -*- coding: utf-8 -*-
"""1.2.0 新增：任务点级断点与进度记录的行为测试。"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import progress
from task.tool import common


class ProgressTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_path = progress.PATH
        progress.PATH = os.path.join(self._tmp.name, "point_state.json")
        progress.set_account("18100000000")

    def tearDown(self):
        progress.PATH = self._old_path
        progress.set_account("")
        self._tmp.cleanup()

    def test_accounts_are_isolated(self):
        progress.record_chapter("课A", "https://mooc1.chaoxing.com/mycourse/studentstudy?chapterId=1")
        progress.set_account("18200000000")
        self.assertEqual(progress.chapter_url("课A"), "")
        progress.set_account("18100000000")
        self.assertIn("studentstudy", progress.chapter_url("课A"))

    def test_bad_url_is_ignored(self):
        progress.record_chapter("课A", "https://i.chaoxing.com/")
        self.assertEqual(progress.chapter_url("课A"), "")

    def test_chapter_then_point(self):
        progress.record_chapter("课A", "https://mooc1.chaoxing.com/mycourse/studentstudy?chapterId=1")
        progress.save_point("课A", "10:00", "https://player/index.html?objectid=x")
        info = progress.get("课A")
        self.assertEqual(info["point_time"], 600)
        self.assertEqual(info["point_url"], "https://player/index.html?objectid=x")
        self.assertIn("studentstudy", info["chapter_url"])

    def test_switching_point_resets_position(self):
        progress.save_point("课A", "10:00", "https://player?objectid=a")
        progress.save_point("课A", "0:30", "https://player?objectid=b")
        info = progress.get("课A")
        self.assertEqual(info["point_url"], "https://player?objectid=b")
        self.assertEqual(info["point_time"], 30)

    def test_position_is_throttled(self):
        progress.save_point("课A", "10:00", "https://player?objectid=a")
        progress.save_point("课A", "10:05", "https://player?objectid=a")
        self.assertEqual(progress.get("课A")["point_time"], 600)
        progress.save_point("课A", "10:20", "https://player?objectid=a")
        self.assertEqual(progress.get("课A")["point_time"], 620)

    def test_restore_needs_same_point(self):
        driver = FakeDriver()
        progress.save_point("课A", "10:00", "https://player?objectid=a")
        self.assertEqual(progress.restore(driver, "课A", "https://player?objectid=b"), 0.0)
        self.assertIsNone(driver.seeked)
        self.assertEqual(progress.restore(driver, "课A", "https://player?objectid=a"), 600)
        self.assertEqual(driver.seeked, 600)

    def test_seconds_parsing(self):
        self.assertEqual(progress._seconds("0:59"), 59)
        self.assertEqual(progress._seconds("1:02:03"), 3723)
        self.assertEqual(progress._seconds(""), 0)


class FakeDriver:
    def __init__(self):
        self.seeked = None

    def execute_script(self, script, *args):
        if args:
            self.seeked = args[0]
        return None


class SaveProcessTest(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        os.makedirs(os.path.join("task", "tool"), exist_ok=True)
        self.path = os.path.join("task", "tool", "course_process.json")
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"课A": [3, 10]}, handle, ensure_ascii=False)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _load(self):
        with open(self.path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def test_unknown_progress_does_not_change_file(self):
        self.assertFalse(common.save_process("课A"))
        self.assertEqual(self._load()["课A"], [3, 10])

    def test_zero_total_is_rejected(self):
        self.assertFalse(common.save_process("课A", 5, 0))
        self.assertEqual(self._load()["课A"], [3, 10])

    def test_real_progress_is_written(self):
        self.assertTrue(common.save_process("课A", 7, 10))
        self.assertEqual(self._load()["课A"], [7, 10])

    def test_done_greater_than_total_is_rejected(self):
        self.assertFalse(common.save_process("课A", 11, 10))
        self.assertEqual(self._load()["课A"], [3, 10])


if __name__ == "__main__":
    unittest.main()
