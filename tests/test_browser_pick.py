# -*- coding: utf-8 -*-
"""驱动选择与版本比对的回归测试：不联网、不启动浏览器。"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core import browser as browser_module


class VersionParsingTests(unittest.TestCase):
    def test_parse_reads_first_three_parts(self):
        self.assertEqual(browser_module.parse_version("156.0.4314.50"), (156, 0, 4314))

    def test_parse_pads_short_versions(self):
        self.assertEqual(browser_module.parse_version("120"), (120, 0, 0))
        self.assertEqual(browser_module.parse_version("120.5"), (120, 5, 0))

    def test_parse_rejects_empty_or_garbage(self):
        self.assertIsNone(browser_module.parse_version(""))
        self.assertIsNone(browser_module.parse_version(None))
        self.assertIsNone(browser_module.parse_version("abc.def"))

    def test_patch_difference_is_accepted(self):
        self.assertTrue(
            browser_module.versions_match("156.0.4314.50", "156.0.4314.42"))

    def test_build_difference_is_rejected(self):
        self.assertFalse(
            browser_module.versions_match("156.0.4314.50", "155.0.4314.50"))
        self.assertFalse(
            browser_module.versions_match("156.0.4314.50", "156.0.4000.50"))

    def test_unknown_version_never_matches(self):
        self.assertFalse(browser_module.versions_match(None, "156.0.4314.42"))


class DriverPickTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.driver = Path(self.tmp.name) / "msedgedriver.exe"
        self.driver.write_bytes(b"stub")
        patches = [
            mock.patch.object(browser_module, "BUNDLED_DRIVER", self.driver),
            mock.patch.object(browser_module, "ROOT", Path(self.tmp.name)),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_matching_bundled_driver_is_used(self):
        with mock.patch.object(browser_module, "browser_version", return_value="156.0.4314.50"), \
                mock.patch.object(browser_module, "driver_version", return_value="156.0.4314.42"):
            source, path = browser_module.resolve_driver("edge", "")
        self.assertEqual(source, "bundled")
        self.assertEqual(path, str(self.driver))

    def test_mismatched_bundled_driver_falls_back_to_manager(self):
        with mock.patch.object(browser_module, "browser_version", return_value="157.0.1.1"), \
                mock.patch.object(browser_module, "driver_version", return_value="156.0.4314.42"):
            source, path = browser_module.resolve_driver("edge", "")
        self.assertEqual(source, "manager")
        self.assertEqual(path, "")

    def test_unknown_browser_version_keeps_bundled_driver(self):
        with mock.patch.object(browser_module, "browser_version", return_value=None):
            source, _ = browser_module.resolve_driver("edge", "")
        self.assertEqual(source, "bundled")

    def test_chrome_never_uses_the_bundled_edge_driver(self):
        source, path = browser_module.resolve_driver("chrome", "")
        self.assertEqual(source, "manager")
        self.assertEqual(path, "")

    def test_custom_driver_wins(self):
        custom = Path(self.tmp.name) / "custom_driver.exe"
        custom.write_bytes(b"stub")
        source, path = browser_module.resolve_driver("edge", str(custom))
        self.assertEqual(source, "custom")
        self.assertEqual(path, str(custom))

    def test_missing_bundled_driver_falls_back(self):
        self.driver.unlink()
        source, _ = browser_module.resolve_driver("edge", "")
        self.assertEqual(source, "manager")


class DriverStateTests(unittest.TestCase):
    def test_state_reports_versions_and_match(self):
        with mock.patch.object(browser_module, "browser_version", return_value="156.0.4314.50"), \
                mock.patch.object(browser_module, "driver_version", return_value="156.0.4314.42"), \
                mock.patch.object(browser_module, "resolve_driver",
                                  return_value=("bundled", r"D:\tmp\msedgedriver.exe")):
            state = browser_module.driver_state("edge", "")
        self.assertEqual(state["browser_version"], "156.0.4314.50")
        self.assertEqual(state["driver_version"], "156.0.4314.42")
        self.assertTrue(state["matched"])

    def test_unknown_browser_name_falls_back_to_edge(self):
        with mock.patch.object(browser_module, "browser_version", return_value=None), \
                mock.patch.object(browser_module, "resolve_driver",
                                  return_value=("manager", "")):
            state = browser_module.driver_state("safari", "")
        self.assertEqual(state["browser"], "edge")
        self.assertIsNone(state["matched"])


if __name__ == "__main__":
    unittest.main()
