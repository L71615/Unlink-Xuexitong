import time
from selenium.webdriver.common.by import By
from task.tool import color
from task.quiz_ai import Answer, QUESTION_CSS, find_title_element

class do_work(Answer):
    def __init__(self,driver,course_name,homework,API_KEY):
        Answer.__init__(self,driver,test_frame=None,course_name=course_name,api=API_KEY,work_choice=None,after_finish_question='仅自动保存')

        self.homework = homework
        self.driver = driver
        self.course_name = course_name
        if self.homework == '自动选择':
            self.auto_choice_homework_question()
        elif self.homework == '手动选择':
            print(color.green('请手动选择你要刷的作业，点开即可'), flush=True)
            now_window_handles = len(driver.window_handles)
            while len(driver.window_handles) == now_window_handles:
                time.sleep(1)
            time.sleep(2)
            self.get_answer_list()
        print(color.green(f'已完成作业,15秒后自动关闭窗口'), flush=True)
        time.sleep(15)


    def auto_choice_homework_question(self):
        # 点击未完成的作业
        elements = self.driver.find_elements(By.CSS_SELECTOR, '[name="group-radio"]')
        elements[2].click()
        time.sleep(2)
        # 作业列dddd表元素
        try:
            element = self.driver.find_element(By.CLASS_NAME, 'bottomList')
        except:
            print(color.red('未检测到作业'), flush=True)
            return
        # 作业列表
        homework_list = element.find_elements(By.TAG_NAME, 'li')
        print(color.green(f'已检测到{len(homework_list)}个作业'), flush=True)
        for i in range(len(homework_list)):
            if i != 0:
                self.turn_page(self.driver, self.course_name)
                self.driver.switch_to.frame(self.driver.find_element(By.TAG_NAME, 'iframe'))
            homework = homework_list[i]
            # 获取作业名称
            homework_name = homework.get_attribute('aria-label')
            print(color.green(f'开始处理第{i + 1}个作业：{homework_name}'), flush=True)
            # 点击作业
            homework.click()
            time.sleep(1)
            self.get_answer_list()
            print(color.green(f'已完成第{i + 1}个作业'), flush=True)
            time.sleep(1)
            self.driver.close()


    def get_answer_list(self):
        self.no_answer_dit = {}
        self.num_answer_dit = {}
        self.answer_list = []
        self.num_option_dit = {}
        self.all_title_dit = {}
        self.all_optionWebElementList = []
        self.optionWebElementList = []
        self.questionType_list = []
        self.only_title_text = []
        self.answer_num = []
        # 切换到作业窗口
        self.turn_page(self.driver, '作业作答')
        # 查找作业题目数量（包含匹配，兼容 class 顺序/追加变化）
        self.questionList0 = self.driver.find_elements(By.CSS_SELECTOR, QUESTION_CSS)
        print(color.green(f'作业题目数量：{len(self.questionList0)}'), flush=True)
        for i in range(len(self.questionList0)):
            self.title_num = i + 1
            self.option_text_list = []
            self.optionWebElementList = []
            # 获取题目类型和题目内容
            self.title_and_option_element=self.questionList0[i]
            self.title_and_option_text =self.title_and_option_element.text
            self.questionType = self.questionList0[i].get_attribute('typename')
            if self.questionType not in ['填空题','判断题','单选题','多选题','简答题','名词解释','论述题']:
                print(color.red(f'第{i+1}题题型为{self.questionType},无法作答'))
                # 占位，保证四个列表下标一致，否则后面会串题
                self.questionType_list.append(self.questionType or '')
                self.only_title_text.append('')
                self.all_optionWebElementList.append(None)
                continue
            # 标题元素用候选链定位，作业页结构变化时也不会整份崩掉
            title_element = find_title_element(self.questionList0[i])
            self.title = (title_element.text or '').strip()
            if ')' in self.title:
                self.title_text = self.title[self.title.find(")") + 1:]
            elif '】' in self.title:
                self.title_text = self.title[self.title.find("】") + 1:]
            else:
                self.title_text = self.title
            self.only_title_text.append(self.title_text)
            self.questionType_list.append(self.questionType)
            # 与 append 后的列表长度对齐，而不是用原始 i
            index = len(self.questionType_list) - 1

            if self.title_text == '':
                print(color.red('未检测到题目内容'), flush=True)
                self.all_optionWebElementList.append(None)
                continue
            self.optionWebElementList = self.questionList0[i].find_elements(
                By.CSS_SELECTOR, '[class*="answerBg"]')
            self.all_optionWebElementList.append(self.optionWebElementList)
            for option_element in self.optionWebElementList:
                label = option_element.get_attribute('aria-label') or ''
                self.option_text_list.append(label[:-2] if len(label) > 2 else label)
            self.all_title_dit[index] = self.title_and_option_text
            self.num_option_dit[index] = self.option_text_list
        print(color.red('正在搜索中，请耐心等待...'))
        if self.API_KEY == 'sk-open_deepseek':
            self.no_answer_dit = self.all_title_dit
        else:
            self.use_ai_wen_da()
            for i, answer in self.num_answer_dit.items():
                if not answer:
                    self.no_answer_dit[i] = self.all_title_dit[i]
        self.use_deepseek()
        self.turn_page(self.driver, '作业作答')

        print(color.green('开始答题'), flush=True)
        for title_num in self.num_answer_dit.keys():
            self.finish_title(title_num)
            time.sleep(0.5)
        try:
            self.save_elements = self.driver.find_element(By.ID, 'submitFocus').find_elements(By.TAG_NAME, 'a')
            print(color.red('暂时保存，AI答题不一定完全正确，请自行确认后再提交'), flush=True)
        except:
            print(color.red('保存失败，请手动保存，15秒后继续'), flush=True)
            time.sleep(15)
            # 找不到保存按钮时留空，避免下面的 for 直接 AttributeError
            self.save_elements = []
        for save_element in self.save_elements:
            if save_element.text == '暂时保存':
                save_element.click()


