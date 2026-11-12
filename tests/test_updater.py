# -*- coding: utf-8 -*-
"""在线更新的契约测试：版本比较、解压剥层、批处理内容、启动参数。

真正替换文件的行为在 Windows 上靠 apply.cmd 完成，这里只锁定：
1. 版本比较不会误判（1.9.0 不能被 1.10.0 判成旧版）；
2. 解压后要去掉发布包的顶层 ``课业助手/``，否则文件会套一层目录；
3. 批处理必须是纯 ASCII（cmd 按 936 读文件，中文会乱码）；
4. 启动脚本时参数顺序固定：安装目录、PID、exe 路径。
"""
import io
import os
import tempfile
import unittest
import zipfile
from unittest import mock

from core import updater


class VersionTests(unittest.TestCase):
    def test_parse_three_part(self):
        self.assertEqual(updater.parse_version("1.4.0"), (1, 4, 0))

    def test_parse_with_v_prefix(self):
        self.assertEqual(updater.parse_version("v1.4.2"), (1, 4, 2))

    def test_parse_two_part_defaults_patch(self):
        self.assertEqual(updater.parse_version("1.4"), (1, 4, 0))

    def test_parse_garbage_is_zero(self):
        self.assertEqual(updater.parse_version("latest"), (0, 0, 0))
        self.assertEqual(updater.parse_version(""), (0, 0, 0))
        self.assertEqual(updater.parse_version(None), (0, 0, 0))

    def test_numeric_not_lexical_check(self):
        self.assertTrue(updater.is_newer("1.10.0", "1.9.0"))
        self.assertFalse(updater.is_newer("1.9.0", "1.10.0"))

    def test_same_version_is_not_newer(self):
        self.assertFalse(updater.is_newer("1.4.0", "1.4.0"))
        self.assertFalse(updater.is_newer("v1.4.0", "1.4.0"))

    def test_older_is_not_newer(self):
        self.assertFalse(updater.is_newer("1.3.1", "1.4.0"))


class ZipLayoutTests(unittest.TestCase):
    def _make_zip(self, names):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name in names:
                archive.writestr(name, name.encode("utf-8"))
        buffer.seek(0)
        return buffer

    def test_single_top_detected(self):
        names = ["课业助手/课业助手.exe", "课业助手/_internal/base.dll"]
        self.assertEqual(updater._single_top(names), "课业助手")

    def test_backslash_paths_normalized(self):
        names = ["课业助手\\课业助手.exe", "课业助手\\task\\tool\\a.json"]
        self.assertEqual(updater._single_top(names), "课业助手")

    def test_multiple_tops_kept_flat(self):
        self.assertEqual(updater._single_top(["a.txt", "b.txt"]), "")

    def test_single_file_has_no_top_dir(self):
        self.assertEqual(updater._single_top(["readme.txt"]), "")

    def test_extract_strips_top_directory(self):
        buffer = self._make_zip(["课业助手/课业助手.exe",
                                 "课业助手/_internal/base.dll",
                                 "课业助手/task/tool/a.json"])
        with tempfile.TemporaryDirectory() as folder:
            updater.extract_from(buffer, folder)
            self.assertTrue(os.path.isfile(os.path.join(folder, "课业助手.exe")))
            self.assertTrue(os.path.isfile(os.path.join(folder, "_internal", "base.dll")))
            self.assertTrue(os.path.isfile(os.path.join(folder, "task", "tool", "a.json")))
            self.assertFalse(os.path.isdir(os.path.join(folder, "课业助手")))

    def test_extract_keeps_flat_zip(self):
        buffer = self._make_zip(["a.txt", "sub/b.txt"])
        with tempfile.TemporaryDirectory() as folder:
            updater.extract_from(buffer, folder)
            self.assertTrue(os.path.isfile(os.path.join(folder, "a.txt")))
            self.assertTrue(os.path.isfile(os.path.join(folder, "sub", "b.txt")))


class ApplyScriptTests(unittest.TestCase):
    def test_script_is_pure_ascii(self):
        """cmd 按系统代码页读脚本，混进中文会执行成乱码。"""
        updater.APPLY_SCRIPT.encode("ascii")

    def test_script_waits_for_old_process(self):
        self.assertIn('tasklist /FI "PID eq %~2"', updater.APPLY_SCRIPT)

    def test_script_copies_payload_over_install_dir(self):
        self.assertIn('robocopy "%~dp0payload" "%~1"', updater.APPLY_SCRIPT)

    def test_script_clears_assets_marker(self):
        """.assets_version 不清掉，新版本不会重新释放内置资源。"""
        self.assertIn(r'del "%~1\.assets_version"', updater.APPLY_SCRIPT)

    def test_script_restarts_only_real_exe(self):
        self.assertIn('if exist "%~3" start "" "%~3"', updater.APPLY_SCRIPT)

    def test_script_deletes_itself(self):
        self.assertIn(r'del "%~f0"', updater.APPLY_SCRIPT)

    def test_no_detached_process_flag(self):
        """DETACHED_PROCESS 下没有控制台，tasklist 的管道会挂住。"""
        self.assertTrue(updater._detached_flags() & updater.CREATE_NO_WINDOW)
        self.assertFalse(updater._detached_flags() & updater.DETACHED_PROCESS)


class ApplyUpdateTests(unittest.TestCase):
    def test_popen_arguments_order(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = os.path.join(folder, "payload")
            os.makedirs(payload)
            with mock.patch("core.updater.subprocess.Popen") as popen:
                script = updater.apply_update(payload, r"D:\安装目录", r"D:\安装目录\课业助手.exe")
            self.assertTrue(os.path.isfile(script))
            argv = popen.call_args[0][0]
            self.assertEqual(argv[:3], ["cmd.exe", "/c", script])
            self.assertEqual(argv[3], r"D:\安装目录")
            self.assertEqual(argv[4], str(os.getpid()))
            self.assertEqual(argv[5], r"D:\安装目录\课业助手.exe")

    def test_written_script_decodes_as_ascii(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = os.path.join(folder, "payload")
            os.makedirs(payload)
            with mock.patch("core.updater.subprocess.Popen"):
                script = updater.apply_update(payload, r"D:\app", r"D:\app\a.exe")
            with open(script, "rb") as handle:
                handle.read().decode("ascii")


class CheckLatestTests(unittest.TestCase):
    class _Response:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    def _patch(self, payload: bytes):
        return mock.patch("core.updater.urllib.request.urlopen",
                          return_value=self._Response(payload))

    def test_returns_release_when_newer(self):
        import json
        body = json.dumps({
            "tag_name": "v9.9.9",
            "body": "修了答题定位",
            "assets": [{"name": "CourseHelper-9.9.9-win64.zip",
                        "browser_download_url": "https://example.com/a.zip",
                        "size": 123}],
        }).encode("utf-8")
        with self._patch(body):
            release = updater.check_latest()
        self.assertIsNotNone(release)
        self.assertEqual(release.version, "9.9.9")
        self.assertEqual(release.zip_url, "https://example.com/a.zip")
        self.assertEqual(release.size, 123)

    def test_returns_none_when_same_version(self):
        import json
        body = json.dumps({"tag_name": "v1.0.0",
                           "assets": [{"name": "x.zip",
                                       "browser_download_url": "https://example.com/a.zip"}]}).encode("utf-8")
        with mock.patch("core.updater.APP_VERSION", "1.0.0"), self._patch(body):
            self.assertIsNone(updater.check_latest())

    def test_raises_when_no_zip_asset(self):
        import json
        body = json.dumps({"tag_name": "v9.9.9", "assets": []}).encode("utf-8")
        with self._patch(body):
            with self.assertRaises(updater.UpdateError):
                updater.check_latest()


class NotesTests(unittest.TestCase):
    def test_multiline_collapsed(self):
        self.assertEqual(updater.summarize_notes("第一行\n第二行"), "第一行 · 第二行")

    def test_long_notes_truncated(self):
        text = updater.summarize_notes("啊" * 300, limit=10)
        self.assertTrue(text.endswith("…"))
        self.assertEqual(len(text), 11)

    def test_empty_notes(self):
        self.assertEqual(updater.summarize_notes(None), "")


class RateLimitFallbackTests(unittest.TestCase):
    """GitHub API 未登录每小时只有 60 次额度，撞上了也得能查到版本。"""

    class _Redirect:
        def __init__(self, url):
            self._url = url

        def geturl(self):
            return self._url

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    def _forbidden(self):
        return updater.urllib.error.HTTPError(
            updater.LATEST_API, 403, "rate limit exceeded", {}, None)

    def test_falls_back_to_redirect_tag(self):
        with mock.patch("core.updater.urllib.request.urlopen",
                        side_effect=self._forbidden()), \
                mock.patch.object(updater, "_tag_from_redirect", return_value="v9.9.9"):
            release = updater.check_latest()
        self.assertIsNotNone(release)
        self.assertEqual(release.version, "9.9.9")
        self.assertEqual(
            release.zip_url,
            "https://github.com/L71615/Unlink-Xuexitong/releases/download/v9.9.9/"
            "CourseHelper-9.9.9-win64.zip")
        self.assertEqual(release.file_name, "CourseHelper-9.9.9-win64.zip")

    def test_redirect_tag_not_newer_returns_none(self):
        with mock.patch("core.updater.urllib.request.urlopen",
                        side_effect=self._forbidden()), \
                mock.patch.object(updater, "_tag_from_redirect", return_value="v1.0.0"), \
                mock.patch.object(updater, "APP_VERSION", "1.4.0"):
            self.assertIsNone(updater.check_latest())

    def test_both_channels_failing_returns_none(self):
        with mock.patch("core.updater.urllib.request.urlopen",
                        side_effect=self._forbidden()):
            self.assertIsNone(updater.check_latest())

    def test_parses_tag_from_final_url(self):
        url = "https://github.com/L71615/Unlink-Xuexitong/releases/tag/v1.5.0"
        with mock.patch("core.updater.urllib.request.urlopen",
                        return_value=self._Redirect(url)):
            self.assertEqual(updater._tag_from_redirect(), "v1.5.0")

    def test_non_tag_redirect_returns_empty(self):
        url = "https://github.com/L71615/Unlink-Xuexitong/releases"
        with mock.patch("core.updater.urllib.request.urlopen",
                        return_value=self._Redirect(url)):
            self.assertEqual(updater._tag_from_redirect(), "")


class StripRuntimeTests(unittest.TestCase):
    """更新包不能覆盖用户本机的刷课进度、账号和日志。"""

    def make_payload(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        tool = os.path.join(tmp, "task", "tool")
        os.makedirs(tool, exist_ok=True)
        return tmp, tool

    def test_removes_known_runtime_files(self):
        payload, tool = self.make_payload()
        names = ("course_process.json", "account_info.json", "accounts.json",
                 "输出记录.log", "error.log")
        for name in names:
            with open(os.path.join(tool, name), "w", encoding="utf-8") as f:
                f.write("{}")
        updater._strip_runtime(payload)
        left = set(os.listdir(tool))
        for name in names:
            self.assertNotIn(name, left)

    def test_keeps_shipped_assets(self):
        payload, tool = self.make_payload()
        keep = ("Help.txt", "font_dict.txt", "version_info",
                "account_info.example.json")
        for name in keep:
            with open(os.path.join(tool, name), "w", encoding="utf-8") as f:
                f.write("x")
        updater._strip_runtime(payload)
        left = set(os.listdir(tool))
        for name in keep:
            self.assertIn(name, left)

    def test_payload_without_tool_dir_is_noop(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        updater._strip_runtime(tmp)  # 不抛异常即可

    def test_prepare_update_strips_after_extract(self):
        """prepare_update 解压完必须走一遍清理，否则进度会被清零。"""
        root = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, root, True)

        def fake_extract(_archive, dest):
            tool = os.path.join(dest, "task", "tool")
            os.makedirs(tool, exist_ok=True)
            for name, body in (("course_process.json", "{}"), ("Help.txt", "x")):
                with open(os.path.join(tool, name), "w", encoding="utf-8") as f:
                    f.write(body)

        release = updater.Release("1.4.0", "https://example.invalid/x.zip")
        with mock.patch.object(updater, "work_dir", return_value=root), \
                mock.patch.object(updater, "download"), \
                mock.patch.object(updater, "extract", side_effect=fake_extract):
            out = updater.prepare_update(release)
        tool = os.path.join(out, "task", "tool")
        self.assertFalse(os.path.exists(os.path.join(tool, "course_process.json")))
        self.assertTrue(os.path.exists(os.path.join(tool, "Help.txt")))


if __name__ == "__main__":
    unittest.main()
