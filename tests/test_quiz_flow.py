# -*- coding: utf-8 -*-
"""测验答题流程的回归测试：题库调用参数、AI 兜底、选项点击。"""
import unittest
from unittest import mock

import task.quiz_ai as quiz_ai


class FakeElement:
    def __init__(self, text="", checked=False):
        self.text = text
        self.checked = checked
        self.clicks = 0

    def get_attribute(self, name):
        if name == "aria-checked" and self.checked:
            return "true"
        return ""

    def click(self):
        self.clicks += 1
        self.checked = True

    def is_displayed(self):
        return True


class FakeSwitch:
    def frame(self, *args, **kwargs):
        pass

    def parent_frame(self):
        pass

    def default_content(self):
        pass


class FakeDriver:
    def __init__(self):
        self.switch_to = FakeSwitch()
        self.p_element = FakeElement()
        self.scripts = []

    def execute_script(self, *args, **kwargs):
        self.scripts.append(args)

    def find_element(self, *args, **kwargs):
        return self.p_element


class FakeFrame:
    pass


class FakeQuestion(FakeElement):
    def __init__(self, frame):
        super().__init__("question")
        self.frame = frame

    def find_element(self, by, selector):
        return self.frame


def make_answer(options, answer, qtype="单选题"):
    answer_obj = quiz_ai.Answer.__new__(quiz_ai.Answer)
    answer_obj.driver = FakeDriver()
    answer_obj.questionList0 = [FakeElement("q")]
    answer_obj.questionType_list = [qtype]
    answer_obj.num_option_dit = {0: options}
    answer_obj.num_answer_dit = {0: answer}
    answer_obj.all_optionWebElementList = [[FakeElement(option) for option in options]]
    return answer_obj


class LibraryCallTest(unittest.TestCase):
    def test_free_library_called_with_four_args(self):
        answer = quiz_ai.Answer.__new__(quiz_ai.Answer)
        answer.times = 0
        answer.work_choice = "DeepSeek AI"
        answer.API_KEY = "sk-test"
        answer.all_title_dit = {0: "【单选题】1+1=?"}
        answer.only_title_text = ["1+1=?"]
        answer.questionType_list = ["单选题"]
        answer.num_option_dit = {0: ["A、1", "B、2", "C、3"]}
        answer.num_answer_dit = {}

        calls = []

        async def fake_main(typ, question, options, api):
            calls.append((typ, question, options, api))
            return [options[1]]

        with mock.patch.object(quiz_ai, "main", fake_main):
            answer.use_ai_wen_da()

        self.assertEqual(len(calls[0]), 4)
        self.assertEqual(calls[0][0], "单选题")
        self.assertEqual(answer.num_answer_dit[0], ["B、2"])

    def test_deepseek_batch(self):
        answer = quiz_ai.Answer.__new__(quiz_ai.Answer)
        answer.API_KEY = "sk-test"
        answer.no_answer_dit = {0: "【单选题】q1", 1: "【多选题】q2"}
        answer.num_answer_dit = {0: [], 1: []}
        answer.only_title_text = ["q1", "q2"]
        answer.questionType_list = ["单选题", "多选题"]
        answer.num_option_dit = {0: ["A、1", "B、2"], 1: ["A、甲", "B、乙", "C、丙"]}

        class DummyAPI:
            def cache_answer(self, *args, **kwargs):
                pass

        with mock.patch.object(quiz_ai, "DeepSeekAsk", return_value="A/BC"), \
                mock.patch.object(quiz_ai, "AnswerAPI", DummyAPI):
            answer.use_deepseek()

        self.assertEqual(answer.num_answer_dit[0], ["A"])
        self.assertEqual(answer.num_answer_dit[1], ["B", "C"])

    def test_deepseek_falls_back_to_single_question(self):
        answer = quiz_ai.Answer.__new__(quiz_ai.Answer)
        answer.API_KEY = "sk-test"
        answer.no_answer_dit = {0: "【单选题】q1", 1: "【判断题】q2"}
        answer.num_answer_dit = {0: [], 1: []}
        answer.only_title_text = ["q1", "q2"]
        answer.questionType_list = ["单选题", "判断题"]
        answer.num_option_dit = {0: ["A、1", "B、2"], 1: ["A、对", "B、错"]}

        class DummyAPI:
            def cache_answer(self, *args, **kwargs):
                pass

        # 第一次批量请求抛错，后续逐题返回
        with mock.patch.object(quiz_ai, "DeepSeekAsk",
                               side_effect=[RuntimeError("402"), "B", "A"]), \
                mock.patch.object(quiz_ai, "AnswerAPI", DummyAPI):
            answer.use_deepseek()

        self.assertEqual(answer.num_answer_dit[0], ["B"])
        self.assertEqual(answer.num_answer_dit[1], ["A"])


class FinishTitleTest(unittest.TestCase):
    def test_single_choice_with_letter(self):
        answer = make_answer(["A、甲", "B、乙", "C、丙"], ["B"])
        self.assertTrue(answer.finish_title(0))
        elements = answer.all_optionWebElementList[0]
        self.assertEqual([element.clicks for element in elements], [0, 1, 0])

    def test_judgment_with_option_text(self):
        answer = make_answer(["A、对", "B、错"], ["B、错"], "判断题")
        self.assertTrue(answer.finish_title(0))
        elements = answer.all_optionWebElementList[0]
        self.assertEqual([element.clicks for element in elements], [0, 1])

    def test_multi_choice_concatenated(self):
        answer = make_answer(["A、甲", "B、乙", "C、丙", "D、丁"], ["AC"], "多选题")
        with mock.patch.object(quiz_ai.time, "sleep", return_value=None):
            self.assertTrue(answer.finish_title(0))
        elements = answer.all_optionWebElementList[0]
        self.assertEqual([element.clicks for element in elements], [1, 0, 1, 0])

    def test_no_match_returns_false(self):
        answer = make_answer(["A、甲", "B、乙"], ["完全不相干"])
        self.assertFalse(answer.finish_title(0))

    def test_text_answer_joined(self):
        frame = FakeFrame()
        p_element = FakeElement()
        p_element.sent = []

        def send_keys(value):
            p_element.sent.append(value)

        p_element.send_keys = send_keys

        answer = quiz_ai.Answer.__new__(quiz_ai.Answer)
        answer.driver = FakeDriver()
        answer.driver.p_element = p_element
        answer.questionList0 = [FakeQuestion(frame)]
        answer.questionType_list = ["简答题"]
        answer.num_option_dit = {0: [""]}
        answer.num_answer_dit = {0: ["第一句。", "第二句。"]}
        answer.all_optionWebElementList = [None]

        self.assertTrue(answer.finish_title(0))
        self.assertEqual(p_element.sent, ["第一句。第二句。"])


if __name__ == "__main__":
    unittest.main()
