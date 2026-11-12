# -*- coding: utf-8 -*-
"""打包版工作目录的释放规则：升级要换掉程序资源，但不能碰用户数据。"""
import os
import sys
import tempfile
import unittest
from unittest import mock

import start


class UserDataTests(unittest.TestCase):
    def test_known_files_are_user_data(self):
        for name in ("account_info.json", "accounts.json", "course_process.json",
                     "course_name.json", "resume_state.json", "point_state.json",
                     "cour_backup.json", "face_url.json"):
            self.assertTrue(start._is_user_data("tool/" + name), name)

    def test_suffixes_and_dirs_are_user_data(self):
        self.assertTrue(start._is_user_data("tool/cookies.pkl"))
        self.assertTrue(start._is_user_data("tool/face_cookies.pkl"))
        self.assertTrue(start._is_user_data("tool/输出记录.log"))
        self.assertTrue(start._is_user_data("record/2026-11-12.json"))
        self.assertTrue(start._is_user_data("data/cache.bin"))
        self.assertTrue(start._is_user_data("tool\\cookies.pkl"))

    def test_shipped_assets_are_not_user_data(self):
        for name in ("tool/Help.txt", "tool/font_dict.txt", "tool/version_info",
                     "tool/account_info.example.json", "tool/speed.crx",
                     "tool/edge_driver/msedgedriver.exe", "quiz_ai.py"):
            self.assertFalse(start._is_user_data(name), name)


class PrepareWorkdirTests(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self.addCleanup(os.chdir, self._cwd)
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        self.src = os.path.join(self.tmp, "meipass")
        self.dst = os.path.join(self.tmp, "app")
        for base in (self.src, self.dst):
            os.makedirs(os.path.join(base, "task", "tool"), exist_ok=True)

    def write(self, root, relative, text):
        path = os.path.join(root, "task", *relative.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def read(self, root, relative):
        path = os.path.join(root, "task", *relative.split("/"))
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def run_prepare(self):
        with mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "_MEIPASS", self.src, create=True), \
                mock.patch.object(start, "base_dir", return_value=self.dst):
            start.prepare_workdir()

    def test_version_bump_refreshes_assets_but_keeps_user_data(self):
        self.write(self.src, "tool/Help.txt", "new help")
        self.write(self.src, "tool/font_dict.txt", "new fonts")
        self.write(self.src, "tool/course_process.json", "{}")
        self.write(self.dst, "tool/Help.txt", "old help")
        self.write(self.dst, "tool/font_dict.txt", "old fonts")
        self.write(self.dst, "tool/course_process.json", '{"done": 3}')
        self.write(self.dst, "tool/accounts.json", '["keep"]')
        self.write(self.dst, "tool/cookies.pkl", "keep")

        self.run_prepare()

        self.assertEqual(self.read(self.dst, "tool/Help.txt"), "new help")
        self.assertEqual(self.read(self.dst, "tool/font_dict.txt"), "new fonts")
        self.assertEqual(self.read(self.dst, "tool/course_process.json"), '{"done": 3}')
        self.assertEqual(self.read(self.dst, "tool/accounts.json"), '["keep"]')
        self.assertEqual(self.read(self.dst, "tool/cookies.pkl"), "keep")

    def test_marker_written_with_current_version(self):
        self.write(self.src, "tool/Help.txt", "new help")
        self.run_prepare()
        marker = os.path.join(self.dst, ".assets_version")
        with open(marker, encoding="utf-8") as handle:
            self.assertEqual(handle.read().strip(), start.APP_VERSION)

    def test_same_version_skips_copy(self):
        self.write(self.src, "tool/Help.txt", "new help")
        self.write(self.dst, "tool/Help.txt", "old help")
        with open(os.path.join(self.dst, ".assets_version"), "w", encoding="utf-8") as handle:
            handle.write(start.APP_VERSION)

        self.run_prepare()

        self.assertEqual(self.read(self.dst, "tool/Help.txt"), "old help")

    def test_source_only_files_still_created(self):
        self.write(self.src, "tool/version_info", start.APP_VERSION)
        self.run_prepare()
        self.assertEqual(self.read(self.dst, "tool/version_info"), start.APP_VERSION)


if __name__ == "__main__":
    unittest.main()
