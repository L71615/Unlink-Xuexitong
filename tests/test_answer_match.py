# -*- coding: utf-8 -*-
"""答案匹配的单元测试，样例来自真实运行日志。"""
import unittest

from task.tool.answer_match import (answer_text, match_indices, split_batch,
                                    split_blanks, to_items)
class MatchIndicesTest(unittest.TestCase):
    def test_single_letter(self):
        self.assertEqual(match_indices(["C"], ["A、甲", "B、乙", "C、丙"], "单选题"), [2])

    def test_single_letter_with_text(self):
        self.assertEqual(match_indices(["B、错"], ["A、对", "B、错"], "判断题"), [1])

    def test_judgment_word(self):
        self.assertEqual(match_indices(["错"], ["A、对", "B、错"], "判断题"), [1])
        self.assertEqual(match_indices(["正确"], ["A、正确", "B、错误"], "判断题"), [0])

    def test_judgment_symbols(self):
        self.assertEqual(match_indices(["√"], ["A、对", "B、错"], "判断题"), [0])
        self.assertEqual(match_indices(["×"], ["A、对", "B、错"], "判断题"), [1])

    def test_multi_concatenated(self):
        options = ["A、甲", "B、乙", "C、丙", "D、丁"]
        self.assertEqual(match_indices(["ABCD"], options, "多选题"), [0, 1, 2, 3])
        self.assertEqual(match_indices(["AC"], options, "多选题"), [0, 2])

    def test_multi_items(self):
        self.assertEqual(
            match_indices(["A", "C"], ["A、甲", "B、乙", "C、丙"], "多选题"), [0, 2])

    def test_option_text(self):
        self.assertEqual(
            match_indices(["实体经济"], ["A、虚拟经济", "B、实体经济"], "单选题"), [1])

    def test_option_text_with_letter(self):
        self.assertEqual(
            match_indices(["B、实体经济"], ["A、虚拟经济", "B、实体经济"], "单选题"), [1])

    def test_fullwidth_letter(self):
        self.assertEqual(match_indices(["Ｂ、错"], ["A、对", "B、错"], "判断题"), [1])

    def test_no_match(self):
        self.assertEqual(match_indices(["不知道"], ["A、甲", "B、乙"], "单选题"), [])

    def test_answer_from_list_literal(self):
        self.assertEqual(
            match_indices("['A', 'C']", ["A、甲", "B、乙", "C、丙"], "多选题"), [0, 2])


class TextHelpersTest(unittest.TestCase):
    def test_answer_text_list(self):
        self.assertEqual(answer_text(["第一句。", "第二句。"]), "第一句。第二句。")

    def test_answer_text_literal(self):
        self.assertEqual(answer_text("['答案']"), "答案")

    def test_split_blanks(self):
        self.assertEqual(split_blanks(["甲", "乙"], 2), ["甲", "乙"])
        self.assertEqual(split_blanks(["甲 乙"], 2), ["甲", "乙"])
        self.assertEqual(split_blanks([""], 2), ["", ""])

    def test_split_batch_slash(self):
        self.assertEqual(split_batch("A/B,C,D/ABCD"), ["A", "B,C,D", "ABCD"])

    def test_split_batch_list(self):
        self.assertEqual(split_batch("['A', 'B']"), ["A", "B"])

    def test_to_items(self):
        self.assertEqual(to_items("A、C"), ["A", "C"])
        self.assertEqual(to_items(["A、对"]), ["A、对"])


if __name__ == "__main__":
    unittest.main()
