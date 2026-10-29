# Copyright (c) 2025 Mortal004
# All rights reserved.
# This software is provided for non-commercial use only.
# For more information, see the LICENSE file in the root directory of this project.
import random
import time
import re
import ast
import asyncio
import traceback

from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By

from task.tool.common import turn_page, Common
from task.tool.no_secret import DecodeSecret
from task.tool import color
import sys
import io
from task.tool.ai_wen_da import main,AnswerAPI,Question
from task.tool.answer_match import (answer_text, match_indices, split_batch,
                                    split_blanks, to_items)
from task.tool.DeepSeekAsk import DeepSeekAsk
from task.tool.send_wx import send_error

# 设置默认编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')



class Answer:
    def __init__(self, driver, test_frame, course_name, api,work_choice,after_finish_question,times=0):
        self.driver=driver
        self.frame = test_frame
        self.decodeSecret = None
        self.questionList0 = []
        self.no_answer_dit = {}# 存储无答案的题目
        self.answer_list = []
        self.course_name = course_name
        self.driver=driver
        self.API_KEY=api
        self.work_choice=work_choice
        self.turn_page=turn_page
        # 使用正则表达式提取百分比数字
        match = re.search(r'(\d+)%', after_finish_question)
        if match:
            self.after_finish_question = int(match.group(1)) / 100
        else:
            self.after_finish_question=after_finish_question

        self.ans_rate =None
        self.all_title_dit={}
        self.num_option_dit = {}
        self.questionType_list = []
        self.all_title = ''
        self.num_answer_dit = {}
        self.only_title_text = []
        self.reword_time = 0
        self.all_optionWebElementList = []
        self.times = times
        if self.work_choice is not None:
            self.main()

    def main(self):
        # 滚动到测试
        self.driver.execute_script("arguments[0].scrollIntoView();", self.frame)
        # 判断是否完成任务
        try:
            element = self.frame.find_element(By.XPATH, 'preceding-sibling::div[1]')
            txt = element.get_attribute('aria-label')
        except:
            self.driver.switch_to.frame(self.frame)
            self.driver.switch_to.frame('frame_content')
            element = self.driver.find_element(By.CLASS_NAME, 'testTit_status')
            txt = element.text
            time.sleep(3)
            self.driver.switch_to.default_content()
            self.driver.switch_to.frame('iframe')
        if '已完成' in txt:
            print(color.green('测试已完成'), flush=True)
            return
        else:
            self.get_title_option()
            print(color.red('正在搜索中，请耐心等待...'))
            if not self.questionList0:
                print(color.red('没有识别到题目，跳过本次测验'), flush=True)
                return
            if self.API_KEY=='sk-open_deepseek':
                self.no_answer_dit = dict(self.all_title_dit)
            else:
                try:
                    self.use_ai_wen_da()
                except Exception as error:
                    print(color.red(f'题库查询出错：{error}'), flush=True)
                self.no_answer_dit = {
                    index: text for index, text in self.all_title_dit.items()
                    if not self.num_answer_dit.get(index)
                }
                try:
                    self.use_deepseek()
                except Exception as error:
                    print(color.red(f'AI 搜题出错：{error}'), flush=True)
            if not turn_page(self.driver,'学生学习页面')=='True':
                self.driver.switch_to.frame('iframe')
                self.driver.switch_to.frame(self.frame)
                self.driver.switch_to.frame('frame_content')
            print(color.green('开始答题'), flush=True)
            for title_num in self.num_answer_dit.keys():
                if self.finish_title(title_num):
                    self.reword_time += 1
                time.sleep(1)
            self.ans_rate = (self.reword_time / len(self.questionList0)
                             if self.questionList0 else 0)
            print(self.reword_time, '/', len(self.questionList0))
            message = self.submit()
            if not message and self.times<3:
                print(color.green('开始第{}次重新做题'.format(self.times+1)))
                self.driver.switch_to.frame('iframe')
                print(color.green('重新做题'), flush=True)
                Answer(self.driver, self.frame, self.course_name, self.API_KEY, self.work_choice, self.after_finish_question, self.times + 1)
            elif self.times>=3:
                print(color.red('测试答题失败，已重试3次'), flush=True)
    def get_title_option(self):
        self.driver.switch_to.frame(self.frame)
        self.driver.switch_to.frame('frame_content')
        # 实例化 DecodeSecret 类
        self.decodeSecret = DecodeSecret(1)
        print(color.yellow("启用字体解密"), flush=True)
        self.decodeSecret.getFontFace(self.driver)
        # 获取页面中的所有题目
        self.questionList0 = self.driver.find_elements(By.CSS_SELECTOR, '[class="singleQuesId"]')
        print(color.yellow("当前测试共有{}题".format(len(self.questionList0))), flush=True)

        for i in range(len(self.questionList0)):
            self.title_num = i + 1
            self.option_text_list = []
            self.title_and_option_element = self.questionList0[i]
            self.title_and_option_text = re.sub(r'\s+', '',
                                               self.decodeSecret.decode(self.title_and_option_element.text).strip())
            self.title_element = self.title_and_option_element.find_element(By.CSS_SELECTOR,
                                                                            '[class="clearfix font-cxsecret fontLabel"]')
            self.title = re.sub(r'\s+', '', self.decodeSecret.decode(self.title_element.text).strip())
            # 题目类型
            self.questionType = self.title[self.title.find("【") + 1: self.title.find("】")]
            # 题目文本
            self.title_text = self.title[self.title.find("】") + 1:]
            self.only_title_text.append(self.title_text)
            self.questionType_list.append(self.questionType)
            if self.questionType in ['单选题', '多选题','判断题']:
                self.all_optionWebElementList.append(
                    self.title_and_option_element.find_elements(By.TAG_NAME, 'li'))
                for option in self.title_and_option_element.find_elements(By.TAG_NAME, 'li'):
                    self.option_text_list.append(re.sub(r'\s+', '', self.decodeSecret.decode(option.text).strip()))
            elif self.questionType in ['简答题', '论述题', '填空题','名词解释']:
                self.all_optionWebElementList.append(None)
                self.option_text_list  =['']
            else:
                print(color.red(f'第{i+1}题题型为{self.questionType},无法作答'))
                continue
            self.all_title_dit[i] = self.title_and_option_text
            self.num_option_dit[i] = self.option_text_list

    def use_ai_wen_da(self):
        for i in self.all_title_dit.keys():
            self.answer_list = []
            if self.times == 0 and self.work_choice != '随机答题':
                print(color.green('\n<===================  分隔线  ===================>\n'), flush=True)
                for attempt in range(2):
                    try:
                        result = asyncio.run(
                            main(self.questionType_list[i], self.only_title_text[i],
                                 self.num_option_dit[i], self.API_KEY))
                    except Exception as error:
                        print(color.red(f'第{i+1}题搜索失败：{error}'), flush=True)
                        result = []
                    if isinstance(result, str):
                        try:
                            result = ast.literal_eval(result)
                        except Exception:
                            result = [result]
                    self.answer_list = list(result or [])
                    if self.answer_list:
                        break
                    if attempt == 0:
                        print(color.yellow(f'第{i+1}题没有搜到答案，重试一次'), flush=True)
            elif self.work_choice == '随机答题':
                question_type = self.questionType_list[i]
                options = self.num_option_dit[i]
                if question_type in ('单选题', '多选题', '判断题') and options:
                    self.answer_list = [random.choice(options)]
                    print(color.red(f'本次采用随机答题,随机答案为：{self.answer_list}'), flush=True)
            if not self.answer_list:
                self.num_answer_dit[i] = []
                continue
            self.num_answer_dit[i] = self.answer_list

    def use_deepseek(self):
        keys = list(self.no_answer_dit.keys())
        if not keys:
            return
        print(color.red('正在使用deepseek搜题，请耐心等待...'), flush=True)

        parts = []
        try:
            title = '\n'.join(
                f'{number}. {self.no_answer_dit[key]}'
                for number, key in enumerate(keys, 1))
            parts = split_batch(DeepSeekAsk(self.API_KEY, title, 'all'))
        except Exception as error:
            print(color.red(f'DeepSeek 批量搜题失败：{error}'), flush=True)
            parts = []

        if len(parts) != len(keys):
            if parts:
                print(color.yellow(
                    f'AI 返回 {len(parts)} 条答案，与题目数 {len(keys)} 不一致，改为逐题询问'),
                    flush=True)
            parts = []

        for index, key in enumerate(keys):
            if parts:
                items = to_items(parts[index])
            else:
                try:
                    question_type = self.questionType_list[key]
                    if question_type == '名词解释':
                        question_type = '简答题'
                    items = to_items(
                        DeepSeekAsk(self.API_KEY, self.no_answer_dit[key],
                                    question_type))
                except Exception as error:
                    print(color.red(f'第{key+1}题 AI 搜题失败：{error}'), flush=True)
                    items = []
            self.num_answer_dit[key] = items
            if not items:
                print(color.yellow(f'第{key+1}题没有拿到 AI 答案，留空'), flush=True)
                continue
            try:
                AnswerAPI().cache_answer(Question(
                    type=str(self.questionType_list[key]),
                    question=self.only_title_text[key],
                    options=self.num_option_dit[key],
                    API=self.API_KEY), items)
            except Exception as error:
                print(color.yellow(f'缓存答案失败：{error}'), flush=True)


    def finish_title(self, title_num):
        try:
            # 滚动到题目
            self.driver.execute_script("arguments[0].scrollIntoView();", self.questionList0[title_num])
        except Exception:
            pass
        print(color.green(f'正在回答第{title_num + 1}题...'), flush=True)
        answer = self.num_answer_dit.get(title_num) or []
        question_type = self.questionType_list[title_num]
        options = self.num_option_dit[title_num]
        print(color.green(f'该题为{question_type}，答案：{answer}'), flush=True)
        try:
            if question_type in ('单选题', '判断题'):
                indices = match_indices(answer, options, question_type)
                if not indices:
                    print(color.red('答案没能匹配到选项，跳过这题'), flush=True)
                    return False
                elements = self.all_optionWebElementList[title_num]
                index = indices[0]
                if index >= len(elements):
                    print(color.red('选项下标越界，跳过这题'), flush=True)
                    return False
                element = elements[index]
                if (element.get_attribute('aria-checked') or '').lower() == 'true':
                    print(color.red('已回答，无需重复回答'), flush=True)
                else:
                    self._click_option(element)
                return True

            if question_type == '多选题':
                indices = match_indices(answer, options, question_type)
                if not indices:
                    print(color.red('答案没能匹配到选项，跳过这题'), flush=True)
                    return False
                elements = self.all_optionWebElementList[title_num]
                for index in indices:
                    if index >= len(elements):
                        continue
                    element = elements[index]
                    try:
                        checked = (element.get_attribute('aria-checked') or '').lower() == 'true'
                    except Exception:
                        checked = False
                    if checked:
                        print(color.red('已回答，无需重复回答'), flush=True)
                        continue
                    self._click_option(element)
                    time.sleep(1)
                return True

            if question_type in ('简答题', '论述题', '名词解释'):
                text = answer_text(answer).strip()
                if not text:
                    print(color.red('没有可提交的文本答案'), flush=True)
                    return False
                text_frame = self.questionList0[title_num].find_element(By.TAG_NAME, 'iframe')
                self.driver.switch_to.frame(text_frame)
                p_element = self.driver.find_element(By.TAG_NAME, 'p')
                if p_element.text:
                    print(color.red('已回答，无需重复回答'), flush=True)
                    self.driver.switch_to.parent_frame()
                    return True
                try:
                    p_element.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", p_element)
                p_element.send_keys(text)
                self.driver.switch_to.parent_frame()
                return True

            if question_type == '填空题':
                if self.work_choice is not None:
                    elements = self.questionList0[title_num].find_elements(By.CLASS_NAME, 'InpDIV')
                else:
                    elements = self.questionList0[title_num].find_elements(
                        By.CSS_SELECTOR, '[class="edui-editor-iframeholder edui-default"]')
                text_frames = self.questionList0[title_num].find_elements(By.TAG_NAME, 'iframe')
                if not elements:
                    print(color.red('没有找到填空输入框，跳过这题'), flush=True)
                    return False
                parts = split_blanks(answer, len(elements))
                if not any(parts):
                    print(color.red('没有可提交的填空答案'), flush=True)
                    return False
                answered = False
                for number, element in enumerate(elements):
                    if number >= len(text_frames):
                        break
                    value = parts[number] if number < len(parts) else ''
                    self.driver.execute_script("arguments[0].click();", element)
                    self.driver.switch_to.frame(text_frames[number])
                    p_element = self.driver.find_element(By.TAG_NAME, 'p')
                    if p_element.text:
                        print(color.red('已回答，无需重复回答'), flush=True)
                        self.driver.switch_to.parent_frame()
                        continue
                    try:
                        p_element.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", p_element)
                    if value:
                        try:
                            p_element.send_keys(value)
                            answered = True
                        except Exception:
                            pass
                    self.driver.switch_to.parent_frame()
                    time.sleep(1)
                return answered

            print(color.red(f'该题为{question_type}，暂时无法作答'), flush=True)
            return False
        except Exception as e:
            print(color.red(f'答题时出错了{e}'), flush=True)
            return False

    def _click_option(self, element):
        try:
            element.click()
        except Exception:
            try:
                self.driver.execute_script("arguments[0].click();", element)
            except Exception:
                pass

    def submit(self):
        formatted_result = "{:.2%}".format(self.ans_rate)
        print(color.red(f'本次答题率为{formatted_result}'), flush=True)
        if self.after_finish_question=='仅自动保存':
            print(color.yellow('3秒后保存'), flush=True)
            time.sleep(3)
            button=self.driver.find_element(By.CSS_SELECTOR, '[class="btnSave workBtnIndex"]')
            #滚动到按钮可见
            self.driver.execute_script("arguments[0].scrollIntoView();", button)
            #点击按钮
            self.driver.execute_script("arguments[0].click();", button)
        elif self.after_finish_question=='强制自动提交'  or self.work_choice =='随机答题' or self.ans_rate >= self.after_finish_question:
            # 点击提交
            print(color.yellow('3秒后提交'), flush=True)
            time.sleep(3)
            try:
                button=self.driver.find_element(By.CSS_SELECTOR, '[class="btnSubmit workBtnIndex"]')
                #滚动到按钮可见
                self.driver.execute_script("arguments[0].scrollIntoView();", button)
                #点击按钮
                self.driver.execute_script("arguments[0].click();", button)
                time.sleep(1)
            except NoSuchElementException:
                print(color.red('当前测验无法提交'), flush=True)
                return True
            # 点击确认
            self.driver.switch_to.default_content()
            self.driver.find_element(By.XPATH, '//*[@id="popok"]').click()
            time.sleep(2)
            message =self.driver.find_element(By.ID, 'popcontent').text
            if message:
                print(color.red(f'提交失败，原因：{message}'), flush=True)
                self.driver.find_element(By.ID, 'popok').click()
                return False
            self.save_score()
        else:
            print(color.yellow(f'答题率未达到提交要求{self.after_finish_question}'), flush=True)
            print(color.yellow('3秒后保存'), flush=True)
            time.sleep(3)
            self.driver.find_element(By.CSS_SELECTOR, '[class="btnSave workBtnIndex"]').click()

        return True

    def save_score(self):
        # save_process(self.course_name)
        element = self.driver.find_element(By.CLASS_NAME, 'prev_title')
        title = element.get_attribute('title')
        self.driver.switch_to.frame('iframe')
        self.driver.switch_to.frame(self.frame)
        self.driver.switch_to.frame('frame_content')
        try:
            f = open(fr'task\record\《{self.course_name}》的成绩记录.txt', 'a', encoding='utf-8')
            element = self.driver.find_element(By.CSS_SELECTOR, '.achievement i')
            score = element.text
        except:
            score = '未查询到'
            print(color.yellow('未查询到本次测试成绩'), flush=True)
        try:
            f.write(
                f'已完成:《{title}》章节中的测试题，完成时间：{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))}\n测试得分：{score}分(本次使用{self.work_choice})\n\n')
            print(color.green(f'已保存进度'), flush=True)
            f.close()
        except:
            pass
class Quiz(Common):
    def __init__(self, driver, course_name,API, choice,after_finish_question):
        super().__init__(
            driver,
            '[src="/ananas/modules/work/index.html?v=2025-1028-1629&castscreen=0"]',
            "测验",
            course_name
        )
        self.API = API
        self.choice = choice
        self.after_finish_question = after_finish_question
        self.driver = driver
        self.course_name = course_name
    def start(self):
        try:
            Answer(self.driver, self.iframe, self.course_name, self.API, self.choice,self.after_finish_question)
        except:
            error_msg = traceback.format_exc()
            send_error(
                "\n出错了，可以把下面这段报错和截图发到 numaforbus@gmail.com 或 QQ 2023114826 反馈\n" + error_msg)
            print(color.yellow('出错了，具体原因请前往错误日志查看，请自行保存或提交,15秒后继续'), flush=True)
            turn_page(self.driver,'学生学习页面')
            time.sleep(15)
def finish_quiz(driver, course_name, API, choice,after_finish_question):
    # driver.switch_to.default_content()
    # driver.switch_to.frame('iframe')
    # test_frames = driver.find_elements(By.XPATH,
    #                                    '//iframe[@src="/ananas/modules/work/index.html?v=2025-1028-1629&castscreen=0"]')
    # print(color.magenta(f'已检测到{len(test_frames)}个测试'), flush=True)
    # i=0
    # for test_frame in test_frames:
    #     if i!=0:
    #         driver.switch_to.default_content()
    #         driver.switch_to.frame('iframe')
    #     print(f'当前处理第{i+1}个测试', flush=True)
    #     i+=1
    #     try:
    #         Answer(driver, test_frame, course_name, API, choice,after_finish_question)
    #     except:
    #         error_msg = traceback.format_exc()
    #         send_error(
    #             "\n出错了，可以把下面这段报错和截图发到 numaforbus@gmail.com 或 QQ 2023114826 反馈\n" + error_msg)
    #         print(color.yellow('出错了，具体原因请前往错误日志查看，请自行保存或提交,15秒后继续'), flush=True)
    #         turn_page(driver,'学生学习页面')
    #         time.sleep(15)
    quiz=Quiz(driver, course_name, API, choice,after_finish_question)
    quiz.main()
