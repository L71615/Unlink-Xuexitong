# -*- coding: utf-8 -*-
"""标题元素定位的回归测试。

线上问题：`[class="clearfix font-cxsecret fontLabel"]` 是属性全等匹配，页面
class 顺序变化、多一个 class、或题目没做字体加密时就抛
NoSuchElementException，整份测验中断。这里锁住新的包含匹配 + 兜底行为。
"""
import unittest
from unittest import mock

import task.quiz_ai as quiz_ai
import task.do_work as do_work_module
from selenium.common import NoSuchElementException
from task.tool.no_secret import DecodeSecret


class FakeNode:
    def __init__(self, text='', cls='', tag='div', children=None, displayed=True, attrs=None):
        self.text = text
        self.cls = cls
        self.tag = tag
        self.children = children or []
        self.displayed = displayed
        self.attrs = attrs or {}

    def get_attribute(self, name):
        if name == 'class':
            return self.cls
        return self.attrs.get(name, '')

    def is_displayed(self):
        return self.displayed

    def _walk(self):
        for child in self.children:
            yield child
            for deeper in child._walk():
                yield deeper

    def find_elements(self, by, selector):
        tag, value = by, selector
        return [node for node in self._walk() if _matches(node, tag, value)]


def _matches(node, by, value):
    if by == 'tag name':
        return node.tag == value
    if by == 'css selector':
        if value == 'li':
            return node.tag == 'li'
        if 'font-cxsecret' in value and 'fontLabel' in value:
            return 'font-cxsecret' in node.cls and 'fontLabel' in node.cls
        if 'fontLabel' in value:
            return 'fontLabel' in node.cls
        if 'workTextWrap' in value:
            return 'workTextWrap' in node.cls
        if 'singleQuesId' in value:
            return 'singleQuesId' in node.cls
        if 'answerBg' in value:
            return 'answerBg' in node.cls
        if value == 'div.mark_name':
            return node.tag == 'div' and 'mark_name' in node.cls.split()
        if value == 'div.cy_question':
            return node.tag == 'div' and 'cy_question' in node.cls.split()
        return False
    if by == 'xpath':
        return 'fontLabel' in node.cls
    return False


class FakeSwitch:
    def frame(self, *args, **kwargs):
        pass

    def parent_frame(self):
        pass

    def default_content(self):
        pass


class FakeDriver:
    def __init__(self, questions):
        self.switch_to = FakeSwitch()
        self.questions = questions

    def find_elements(self, by, selector):
        if by == 'css selector' and 'singleQuesId' in selector:
            return list(self.questions)
        return []


class ImmediateWait:
    def __init__(self, driver, timeout, poll=0.5):
        self.driver = driver

    def until(self, method):
        return method(self.driver)


def build_question(title_cls, title_text='【单选题】1+1等于几', options=('A、1', 'B、2')):
    option_nodes = [FakeNode(option, 'clearfix answerBg', tag='li') for option in options]
    title = FakeNode(title_text, title_cls)
    container_text = title_text + ''.join(options)
    return FakeNode(container_text, 'padBom50 questionLi fontLabel singleQuesId',
                    children=[title] + option_nodes)


def build_answer(questions):
    answer = quiz_ai.Answer.__new__(quiz_ai.Answer)
    answer.driver = FakeDriver(questions)
    answer.frame = 'frame1'
    answer.questionList0 = []
    answer.all_title_dit = {}
    answer.num_option_dit = {}
    answer.questionType_list = []
    answer.only_title_text = []
    answer.all_optionWebElementList = []
    answer.title_num = 0
    answer.option_text_list = []
    return answer


def run_get_title_option(questions):
    answer = build_answer(questions)
    with mock.patch.object(quiz_ai, 'WebDriverWait', ImmediateWait), \
            mock.patch.object(quiz_ai, 'DecodeSecret', lambda _code: DecodeSecret(0)):
        answer.get_title_option()
    return answer


class ParseTitleTest(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(quiz_ai.parse_title('【单选题】1+1=?'), ('单选题', '1+1=?'))

    def test_without_marker(self):
        qtype, text = quiz_ai.parse_title('没有题型标记的标题')
        self.assertEqual(qtype, '')
        self.assertEqual(text, '没有题型标记的标题')

    def test_broken_marker_order(self):
        qtype, _ = quiz_ai.parse_title('】单选题【题')
        self.assertEqual(qtype, '')


class FindTitleElementTest(unittest.TestCase):
    """旧代码在这些 class 形态下都会抛 NoSuchElementException。"""

    def test_exact_original_class(self):
        container = build_question('clearfix font-cxsecret fontLabel')
        element = quiz_ai.find_title_element(container)
        self.assertEqual(element.cls, 'clearfix font-cxsecret fontLabel')

    def test_reordered_class(self):
        container = build_question('fontLabel clearfix font-cxsecret')
        self.assertEqual(quiz_ai.find_title_element(container).cls,
                         'fontLabel clearfix font-cxsecret')

    def test_without_font_cxsecret(self):
        # 未加密题目：只有 fontLabel，没有 font-cxsecret
        container = build_question('clearfix fontLabel')
        self.assertEqual(quiz_ai.find_title_element(container).cls, 'clearfix fontLabel')

    def test_extra_class_from_plugin(self):
        container = build_question('clearfix font-cxsecret fontLabel answerBox injected')
        self.assertIn('fontLabel', quiz_ai.find_title_element(container).cls)

    def test_falls_back_to_container(self):
        container = build_question('some-totally-different-class')
        self.assertIs(quiz_ai.find_title_element(container), container)


class GetTitleOptionTest(unittest.TestCase):
    def test_end_to_end_single_choice(self):
        answer = run_get_title_option([build_question('clearfix fontLabel')])
        self.assertEqual(answer.questionType_list, ['单选题'])
        self.assertEqual(answer.only_title_text, ['1+1等于几'])
        self.assertEqual(answer.num_option_dit[0], ['A、1', 'B、2'])
        self.assertEqual(len(answer.all_optionWebElementList), 1)

    def test_mixed_questions_keep_index_alignment(self):
        questions = [
            build_question('clearfix font-cxsecret fontLabel'),
            build_question('clearfix fontLabel', '【判断题】地球是圆的'),
            build_question('weird-class', '这道题没有题型标记'),
            build_question('fontLabel clearfix', '【简答题】说说你的理解'),
        ]
        answer = run_get_title_option(questions)
        # 四道题都要占位，否则后面按下标取值会串题
        self.assertEqual(len(answer.questionType_list), 4)
        self.assertEqual(len(answer.only_title_text), 4)
        self.assertEqual(len(answer.all_optionWebElementList), 4)
        self.assertEqual(answer.questionType_list[1], '判断题')
        self.assertEqual(answer.questionType_list[2], '')
        self.assertEqual(answer.questionType_list[3], '简答题')


class HomeworkIndexTest(unittest.TestCase):
    """作业页遇到无法识别的题型时，四个列表必须仍然对齐，不能串题。"""

    def _node(self, typename, title_cls, title_text, options=('A、甲', 'B、乙')):
        option_nodes = [
            FakeNode(option, 'clearfix answerBg', tag='li',
                     attrs={'aria-label': option + '00'})
            for option in options
        ]
        title = FakeNode(title_text, title_cls)
        return FakeNode(title_text + ''.join(options),
                        'padBom50 questionLi fontLabel singleQuesId',
                        children=[title] + option_nodes,
                        attrs={'typename': typename})

    def test_unknown_type_keeps_lists_aligned(self):
        questions = [
            self._node('单选题', 'clearfix fontLabel', '【单选题】1+1=?'),
            self._node('连线题', 'clearfix fontLabel', '【连线题】把左右连起来'),
            self._node('判断题', 'fontLabel clearfix', '【判断题】地球是圆的'),
        ]
        work = do_work_module.do_work.__new__(do_work_module.do_work)
        work.driver = _HomeworkDriver(questions)
        work.turn_page = lambda *args, **kwargs: None
        work.API_KEY = 'sk-open_deepseek'
        work.save_elements = []

        with mock.patch.object(do_work_module.time, 'sleep', return_value=None), \
                mock.patch.object(do_work_module.do_work, 'use_deepseek', lambda self: None):
            work.get_answer_list()

        self.assertEqual(work.questionType_list, ['单选题', '连线题', '判断题'])
        self.assertEqual(sorted(work.all_title_dit), [0, 2])
        self.assertEqual(len(work.all_optionWebElementList), 3)
        self.assertEqual(work.num_option_dit[2], ['A、甲', 'B、乙'])


class _HomeworkDriver:
    def __init__(self, questions):
        self.questions = questions
        self.switch_to = FakeSwitch()

    def find_elements(self, by, selector):
        return list(self.questions)

    def find_element(self, by, value):
        raise NoSuchElementException('no such element')


if __name__ == '__main__':
    unittest.main()