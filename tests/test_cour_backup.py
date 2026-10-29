# -*- coding: utf-8 -*-
"""单门重试的课程列表备份/恢复测试（不启动 GUI）。"""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import start


class FakeConfig:
    def __init__(self, account):
        self.account = dict(account)
        self.saved = []

    def load_account(self):
        return dict(self.account)

    def save_account(self, account):
        self.account = dict(account)
        self.saved.append(dict(account))
        return True


class Dummy:
    _save_cour_backup = start.App._save_cour_backup
    _load_cour_backup = start.App._load_cour_backup
    _clear_cour_backup = start.App._clear_cour_backup
    _restore_cour = start.App._restore_cour
    _recover_cour_backup = start.App._recover_cour_backup


def make_app(account):
    app = Dummy()
    app.config = FakeConfig(account)
    app.account = dict(account)
    app._cour_backup = None
    app._all_courses = list(account.get("cour") or [])
    return app


class CourBackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "cour_backup.json")
        self.patch = patch.object(start, "COUR_BACKUP", self.path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_save_and_load_roundtrip(self):
        app = make_app({"cour": ["A", "B"]})
        self.assertTrue(start.App._save_cour_backup(app, ["A", "B"]))
        self.assertEqual(start.App._load_cour_backup(app), ["A", "B"])

    def test_load_invalid_file_returns_none(self):
        app = make_app({"cour": ["A"]})
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        self.assertIsNone(start.App._load_cour_backup(app))

    def test_restore_puts_courses_back_and_removes_backup(self):
        app = make_app({"cour": ["A"]})
        app._cour_backup = ["A", "B", "C"]
        start.App._restore_cour(app)
        self.assertEqual(app.config.account["cour"], ["A", "B", "C"])
        self.assertEqual(app._all_courses, ["A", "B", "C"])
        self.assertFalse(os.path.exists(self.path))

    def test_recover_after_crash(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(["A", "B"], handle)
        app = make_app({"cour": ["A"]})
        start.App._recover_cour_backup(app)
        self.assertEqual(app.account["cour"], ["A", "B"])
        self.assertEqual(app.config.account["cour"], ["A", "B"])
        self.assertFalse(os.path.exists(self.path))

    def test_restore_without_backup_does_nothing(self):
        app = make_app({"cour": ["A"]})
        start.App._restore_cour(app)
        self.assertEqual(app.config.saved, [])


if __name__ == "__main__":
    unittest.main()
