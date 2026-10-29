# -*- coding: utf-8 -*-
"""题库侧答案匹配的回归测试。"""
import unittest

from task.tool.ai_wen_da import AnswerMatcher, AnswerResult, Question


class LibraryMatcherTest(unittest.TestCase):
    def setUp(self):
        self.matcher = AnswerMatcher()

    def test_match_answer_letters(self):
        question = Question(type='1', question='q',
                            options=['A、甲', 'B、乙', 'C、丙'])
        self.assertEqual(self.matcher.match_answer(['AC'], question), [0, 2])

    def test_match_answer_text(self):
        question = Question(type='0', question='q',
                            options=['A、虚拟经济', 'B、实体经济'])
        self.assertEqual(self.matcher.match_answer(['B、实体经济'], question), [1])

    def test_choice_tries_later_source(self):
        question = Question(type='0', question='q', options=['A、甲', 'B、乙'])
        results = [
            AnswerResult(form='source-one', answer=['???']),
            AnswerResult(form='source-two', answer=['B']),
        ]
        matched = self.matcher._match_choice_questions(results, question)
        self.assertTrue(matched['haveAnswer'])
        self.assertEqual(matched['matchedIndices'], [1])
        self.assertEqual(matched['form'].form, 'source-two')


if __name__ == '__main__':
    unittest.main()
