# -*- coding: utf-8 -*-
"""版本号单一来源的契约测试：改版本只需要动 version.py。"""
import re
import unittest

import version
from core.config_manager import ConfigManager


class VersionSourceTests(unittest.TestCase):
    def test_version_is_three_part_semver(self):
        self.assertRegex(version.APP_VERSION, r"^\d+\.\d+\.\d+$")

    def test_version_tuple_matches_string(self):
        major, minor, patch, build = version.version_tuple()
        self.assertEqual(build, 0)
        self.assertEqual(f"{major}.{minor}.{patch}", version.APP_VERSION)

    def test_exe_name_is_chinese_product_name(self):
        self.assertEqual(version.EXE_NAME, version.APP_NAME)

    def test_config_manager_reports_same_version(self):
        self.assertEqual(ConfigManager().get_version(), version.APP_VERSION)

    def test_no_hardcoded_version_left_in_entrypoints(self):
        """start.py / build_exe.py 里不该再出现写死的版本号。"""
        pattern = re.compile(r"APP_VERSION\s*=\s*[\"']\d")
        for name in ("start.py", "build_exe.py"):
            with open(name, "r", encoding="utf-8") as handle:
                source = handle.read()
            self.assertIsNone(pattern.search(source), f"{name} 里还有写死的版本号")


if __name__ == "__main__":
    unittest.main()
