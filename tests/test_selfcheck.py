# -*- coding: utf-8 -*-
"""启动环境自检的回归测试：不联网、不启动浏览器。"""
import unittest

from core import selfcheck


class SelfcheckTests(unittest.TestCase):
    def test_python_requirement_passes_here(self):
        self.assertTrue(selfcheck._python().ok)

    def test_api_key_missing_is_non_critical(self):
        check = selfcheck._api_key({})
        self.assertFalse(check.ok)
        self.assertFalse(check.critical)
        self.assertTrue(selfcheck._api_key({"API": "sk-test"}).ok)

    def test_auto_browser_skips_path_check(self):
        self.assertTrue(selfcheck._browser("不指定浏览器").ok)
        self.assertTrue(selfcheck._browser("").ok)

    def test_unknown_browser_is_not_a_failure(self):
        self.assertTrue(selfcheck._browser("safari").ok)

    def test_writable_check_returns_a_result(self):
        check = selfcheck._writable()
        self.assertEqual(check.name, "配置写入权限")
        self.assertIsInstance(check.ok, bool)

    def test_run_returns_the_core_checks(self):
        names = {check.name for check in selfcheck.run({})}
        self.assertIn("Python 版本", names)
        self.assertIn("customtkinter", names)
        self.assertIn("浏览器驱动", names)
        self.assertIn("配置写入权限", names)

    def test_failures_filters_ok_checks(self):
        checks = [selfcheck.Check("a", True), selfcheck.Check("b", False)]
        self.assertEqual([check.name for check in selfcheck.failures(checks)], ["b"])


if __name__ == "__main__":
    unittest.main()
