# -*- coding: utf-8 -*-
"""倍速档位计算的回归测试（不启动浏览器）。"""
import unittest

from task.tool.speed_control import MAX_STEPS, plan_steps


class PlanStepsTests(unittest.TestCase):
    def test_already_at_target(self):
        self.assertEqual(plan_steps(2, 2), ("", 0))

    def test_tiny_float_noise_is_ignored(self):
        self.assertEqual(plan_steps(1.299999, 1.3), ("", 0))

    def test_accelerate(self):
        self.assertEqual(plan_steps(1, 1.5), ("d", 5))

    def test_decelerate(self):
        self.assertEqual(plan_steps(8.5, 2), ("a", 65))

    def test_decelerate_to_normal(self):
        self.assertEqual(plan_steps(2, 1), ("a", 10))

    def test_steps_are_capped(self):
        self.assertEqual(plan_steps(1, 99), ("d", MAX_STEPS))


if __name__ == "__main__":
    unittest.main()
