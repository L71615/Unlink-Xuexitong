# -*- coding: utf-8 -*-
"""人脸弹窗守卫的回归测试：不再无限刷新，超时停止本课程。"""
import unittest
from unittest import mock

from task.tool import face


class FakeElement:
    def __init__(self, text="人脸信息采集", qr=True):
        self.text = text
        self.qr = qr

    def is_displayed(self):
        return True

    def find_elements(self, by, selector):
        return [object()] if self.qr else []


class FakeDriver:
    """只模拟 .maskDiv 选择器；present 为 True 时返回一个可见弹窗。"""

    def __init__(self, present=True, flip_after=None):
        self.present = present
        self.flip_after = flip_after
        self.polls = 0

    def find_elements(self, by, selector):
        if selector != ".maskDiv":
            return []
        self.polls += 1
        if self.flip_after is not None and self.polls > self.flip_after:
            self.present = False
        return [FakeElement()] if self.present else []


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def time(self):
        self.now += 0.1
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class ScriptableDriver(FakeDriver):
    """带 execute_script 的驱动：模拟“藏遮罩后是否回弹 / 播放是否继续”。"""

    def __init__(self, present=True, hide_works=True, times=("00:00", "00:05")):
        super().__init__(present=present)
        self.hide_works = hide_works
        self.times = list(times)
        self.calls = 0

    def execute_script(self, script, *args):
        self.calls += 1
        if "vjs-current-time-display" in script:
            return self.times[0] if self.calls == 1 else self.times[-1]
        if self.hide_works:
            self.present = False
        return 1


class SoftDismissTests(unittest.TestCase):
    def test_true_when_mask_stays_hidden_and_playback_continues(self):
        driver = ScriptableDriver()
        self.assertTrue(face.soft_dismiss_face_popup(driver, hold=2))

    def test_false_when_server_pushes_mask_back(self):
        driver = ScriptableDriver(hide_works=False)
        self.assertFalse(face.soft_dismiss_face_popup(driver, hold=2))

    def test_false_when_playback_is_frozen(self):
        driver = ScriptableDriver(times=("00:05", "00:05"))
        self.assertFalse(face.soft_dismiss_face_popup(driver, hold=2))

    def test_driver_without_execute_script_is_not_soft_dismissed(self):
        self.assertFalse(face.soft_dismiss_face_popup(FakeDriver(present=True)))


class FaceGuardTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.patches = [
            mock.patch.object(face.time, "time", self.clock.time),
            mock.patch.object(face.time, "sleep", self.clock.sleep),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def _call(self, driver, ok=False, manual_wait=0.2, auto_verify=0.2):
        with mock.patch.object(face.ChaoxingFaceBypass, "run", return_value=ok), \
                mock.patch("builtins.print"):
            return face.delete_face_popup(
                driver, True, manual_wait=manual_wait, auto_verify=auto_verify)

    def test_disabled_without_popup_does_nothing(self):
        self.assertTrue(face.delete_face_popup(None, False))
        self.assertTrue(self._call(FakeDriver(present=False), ok=False))

    def test_disabled_still_waits_for_manual_scan(self):
        driver = FakeDriver(present=True, flip_after=2)
        with mock.patch.object(face.ChaoxingFaceBypass, "run") as run, \
                mock.patch("builtins.print"):
            self.assertTrue(face.delete_face_popup(
                driver, False, manual_wait=1.0))
        run.assert_not_called()

    def test_disabled_raises_when_manual_scan_times_out(self):
        with mock.patch.object(face.ChaoxingFaceBypass, "run") as run, \
                mock.patch("builtins.print"):
            with self.assertRaises(face.FaceRequired):
                face.delete_face_popup(FakeDriver(present=True), False,
                                       manual_wait=0.2)
        run.assert_not_called()

    def test_no_popup_returns_true(self):
        self.assertTrue(self._call(FakeDriver(present=False)))

    def test_auto_success_and_popup_closed(self):
        driver = FakeDriver(present=True, flip_after=1)
        self.assertTrue(self._call(driver, ok=True))

    def test_auto_fail_raises_after_manual_timeout(self):
        driver = FakeDriver(present=True)
        with self.assertRaises(face.FaceRequired):
            self._call(driver, ok=False, manual_wait=0.2)

    def test_auto_fail_but_soft_dismiss_succeeds(self):
        self.assertTrue(self._call(ScriptableDriver(), ok=False, manual_wait=5))

    def test_soft_dismiss_fails_then_manual_timeout(self):
        with self.assertRaises(face.FaceRequired):
            self._call(ScriptableDriver(hide_works=False), ok=False, manual_wait=0.2)

    def test_auto_success_but_popup_stays_then_manual_scan(self):
        driver = FakeDriver(present=True, flip_after=3)
        self.assertTrue(self._call(driver, ok=True, manual_wait=1.0))

    def test_manual_scan_completes(self):
        driver = FakeDriver(present=True, flip_after=2)
        self.assertTrue(self._call(driver, ok=False, manual_wait=1.0))

    def test_non_face_mask_div_is_ignored(self):
        class OtherMask(FakeElement):
            def __init__(self):
                super().__init__(text="公告", qr=False)

        class Driver:
            def find_elements(self, by, selector):
                if selector == ".maskDiv":
                    return [OtherMask()]
                return []

        self.assertTrue(self._call(Driver()))


if __name__ == "__main__":
    unittest.main()
