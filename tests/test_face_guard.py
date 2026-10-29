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
