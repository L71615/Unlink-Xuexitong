# Copyright (c) 2025 Mortal004
# All rights reserved.
# This software is provided for non-commercial use only.
# For more information, see the LICENSE file in the root directory of this project.
import json
import random
from selenium.common import  NoAlertPresentException
import time

from selenium.webdriver.common.action_chains import ActionChains

from task.tool.DeepSeekAsk import DeepSeekAsk
from task.tool.answer_match import match_indices
from task.tool import color
import pyautogui
from selenium.webdriver.common.by import By
import itertools

from task.tool.common import save_record
from task.tool.face import delete_face_popup
from task.tool.speed_control import apply_speed

drag_progress_condition = True


def click_video_progress_end(driver,pass_vido):
    global drag_progress_condition
    if pass_vido and drag_progress_condition:
        print(color.green('尝试拖动视频进度条'), flush=True)
        driver.execute_script("""
                    var video = document.querySelector('video');
                    if (video) {
                        video.currentTime = video.duration;
                    }
                """)
        drag_progress_condition=False
def check_internet(driver):
    try:
        internet_choice=driver.find_element(By.CSS_SELECTOR,"[class='ans-vjserrdisplay-opts']")
        # print(color.red('网络异常'), flush=True)
        choice_list=internet_choice.find_elements(By.CSS_SELECTOR,"[name='ans-vjserrdisplay-opt']")
        for choice in choice_list:
            choice.click()
    except:
        pass

def get_answer(API,question,typ):
    answer = []
    try:
        answer = DeepSeekAsk(API, question, typ)
    except Exception as e:
        print(f'答题时出错了{e}',flush=True)
    return answer

# ---------------------------------------------------------------------------
# 视频题目
#
# 学习通的视频题一旦答错，弹窗会一直挡在播放器上：视频时间不再前进，外层会
# 判定「视频播放异常」并反复刷新同一个视频，表现出来就是卡死。
# 现在的策略是：
#   1. 先用 AI 给出的答案提交；
#   2. 提交后读弹窗状态，答错就换下一个选项（选 A 错了就试 B）继续提交；
#   3. 所有候选都试过还是关不掉弹窗，就强制点「继续学习 / 返回视频」离开，
#      宁可这题算错，也不让视频卡在这里。
# ---------------------------------------------------------------------------

QUIZ_WAIT = 1.2         # 每次提交后等待页面反馈的秒数
QUIZ_MAX_ATTEMPTS = 12  # 同一道题最多提交几次，防止无限循环（4 选项多选共 11 种组合）


def _answer_indices(answer, option_texts, question_type=''):
    """把「B」或者选项原文换算成选项下标，匹配不到时返回空列表"""
    return match_indices(answer, option_texts, question_type)


def _quiz_popup(driver):
    """当前可见的题目弹窗，没有就返回 None"""
    try:
        for element in driver.find_elements(By.CLASS_NAME, 'tkTopic'):
            try:
                if element.is_displayed():
                    return element
            except Exception:
                continue
    except Exception:
        pass
    return None


def _quiz_options(popup):
    try:
        options = popup.find_elements(By.CSS_SELECTOR, '.tkItem_ul li')
        if options:
            return options
    except Exception:
        pass
    try:
        return popup.find_elements(By.TAG_NAME, 'li')
    except Exception:
        return []


def _option_selected(option):
    try:
        if (option.get_attribute('aria-checked') or '').lower() == 'true':
            return True
        classes = (option.get_attribute('class') or '').lower()
        return any(key in classes for key in ('selected', 'checked', 'active'))
    except Exception:
        return False


def _click_element(driver, element):
    """普通点击失败时退回 JS 点击"""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    except Exception:
        pass
    try:
        element.click()
        return True
    except Exception:
        try:
            driver.execute_script('arguments[0].click();', element)
            return True
        except Exception:
            return False


def _select_options(driver, options, targets, question_type):
    """按题型选中指定下标的选项，返回是否至少点中一个"""
    targets = set(targets)
    clicked = False
    if question_type == '多选题':
        for index, option in enumerate(options):
            if (index in targets) == _option_selected(option):
                continue
            clicked = _click_element(driver, option) or clicked
    else:
        for index in sorted(targets):
            if index < len(options):
                clicked = _click_element(driver, options[index]) or clicked
    return clicked


def _submit_quiz(driver):
    try:
        element = driver.find_element(By.ID, 'videoquiz-submit')
    except Exception:
        return False
    return _click_element(driver, element)


def _leave_quiz(driver):
    """点「继续学习」或「返回视频」，把挡在视频上的弹窗收掉"""
    clicked = False
    for by, selector in ((By.ID, 'videoquiz-continue'),
                         (By.CSS_SELECTOR,
                          '[class="bntWhiteBorder ans-videoquiz-back fr"]')):
        try:
            element = driver.find_element(by, selector)
        except Exception:
            continue
        if _click_element(driver, element):
            clicked = True
            time.sleep(0.5)
    if not clicked:
        # 有些版本这两个按钮都没有，只能把弹窗本身隐藏掉
        try:
            driver.execute_script("""
                document.querySelectorAll('.tkTopic').forEach(function (el) {
                    el.style.display = 'none';
                });
            """)
        except Exception:
            pass
    return clicked


def _quiz_feedback(driver):
    """提交后弹窗的状态：done(已通过) / retry(答错了) / unknown(看不出来)"""
    popup = _quiz_popup(driver)
    if popup is None:
        return 'done'
    try:
        text = popup.text or ''
    except Exception:
        text = ''
    if any(key in text for key in ('回答错误', '答错了', '再试一次', '重新作答', '重新答题')):
        return 'retry'
    if any(key in text for key in ('回答正确', '答对了')):
        return 'done'
    try:
        continue_button = driver.find_element(By.ID, 'videoquiz-continue')
        if continue_button.is_displayed():
            return 'done'
    except Exception:
        pass
    return 'unknown'


def _candidate_answers(question_type, option_count, ai_indices):
    """依次尝试的选项组合：AI 答案优先，之后逐个选项兜底"""
    candidates = []
    if ai_indices:
        candidates.append(list(ai_indices))
    if question_type == '多选题':
        candidates.append(list(range(option_count)))
        if option_count <= 4:
            all_indices = list(range(option_count))
            for size in (3, 2):
                candidates.extend([list(combo) for combo in
                                   itertools.combinations(all_indices, size)])
    else:
        candidates.extend([[index] for index in range(option_count)])
    unique = []
    seen = set()
    for combo in candidates:
        key = tuple(sorted(combo))
        if key and key not in seen:
            seen.add(key)
            unique.append(list(combo))
    return unique


def _dump_quiz_html(driver):
    """答不对时把弹窗的现场存下来，方便排查是不是页面结构变了"""
    try:
        popup = _quiz_popup(driver)
        html = popup.get_attribute('outerHTML') if popup is not None else driver.page_source
        path = fr'task\record\video_quiz_debug.html'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html or '')
        print(color.red(f'视频题目未能通过，已将现场保存到 {path}'), flush=True)
    except Exception as error:
        print(color.red(f'保存视频题目现场失败：{error}'), flush=True)


def check_video_question(driver,API,video_title_choice):
    """处理视频中弹出的题目，答错自动换下一个选项"""
    popup = _quiz_popup(driver)
    if popup is None:
        return

    print(color.yellow('已检测到视频中有题目'), flush=True)
    try:
        question_title = popup.find_element(By.CLASS_NAME, 'tkItem_title').text
    except Exception:
        question_title = ''
    try:
        question_type = popup.find_element(By.CLASS_NAME, 'tkTopic_type').text.strip()
    except Exception:
        try:
            question_type = popup.find_element(By.CLASS_NAME, 'tkTopic_title').text.strip()
        except Exception:
            question_type = ''

    option_texts = [option.text for option in _quiz_options(popup)]
    print(color.yellow(f'题型：{question_type or "未知"}，共{len(option_texts)}个选项'), flush=True)
    if not option_texts:
        _leave_quiz(driver)
        return

    ai_indices = []
    if video_title_choice=='DeepSeek AI':
        answer = get_answer(API,question_title+'\n'+str(option_texts),question_type)
        ai_indices = _answer_indices(answer, option_texts, question_type)
        if question_type != '多选题' and len(ai_indices) > 1:
            ai_indices = ai_indices[:1]
        if ai_indices:
            print(color.blue(f'AI 给出的答案：{[option_texts[index] for index in ai_indices]}'),
                  flush=True)
        else:
            print(color.red('AI 答案没有匹配到选项，改为逐个尝试'), flush=True)

    candidates = _candidate_answers(question_type, len(option_texts), ai_indices)
    for attempt, targets in enumerate(candidates[:QUIZ_MAX_ATTEMPTS], 1):
        popup = _quiz_popup(driver)
        if popup is None:
            break
        options = _quiz_options(popup)
        targets = [index for index in targets if index < len(options)]
        if not targets:
            break
        if not _select_options(driver, options, targets, question_type):
            print(color.yellow('选项已无法点击，结束本题'), flush=True)
            break
        labels = '、'.join(option_texts[index] for index in targets if index < len(option_texts))
        print(color.yellow(f'第{attempt}次提交：{labels}'), flush=True)
        if not _submit_quiz(driver):
            print(color.yellow('提交按钮已消失，本题应已结束'), flush=True)
            break
        time.sleep(QUIZ_WAIT)
        state = _quiz_feedback(driver)
        if state == 'done':
            print(color.green('视频题目已通过'), flush=True)
            _leave_quiz(driver)
            return
        if state == 'retry':
            print(color.red('答错了，换下一个选项'), flush=True)
            time.sleep(0.5)

    if _quiz_feedback(driver) == 'done':
        print(color.green('视频题目已作答完毕'), flush=True)
        _leave_quiz(driver)
        return
    print(color.red('所有选项都试过了，强制关闭题目弹窗继续播放'), flush=True)
    _dump_quiz_html(driver)
    _leave_quiz(driver)

def check_vido_play(driver, last_time, current_time,speed,pass_face,vido_iframe):
    global b, pause_start_time
    with open(r'task/tool/account_info.json', 'r', encoding='utf-8') as f:
        account_info = json.load(f)
    if last_time == current_time and current_time != '':
        pause_duration = time.time() - pause_start_time
        b += 1
        if  pause_duration >= 2 and b!=3:
            try:
                print(color.red(f'当前视频播放被暂停,点击继续播放'), flush=True)
                driver.find_element(By.CSS_SELECTOR,
                                    '[class="vjs-play-control vjs-control vjs-button vjs-paused"]').click()
            except :
                print(color.red(f'点击失败'), flush=True)
                driver.switch_to.default_content()
                delete_face_popup(driver,pass_face)
                driver.switch_to.frame('iframe')
                driver.switch_to.frame(vido_iframe)
            pause_start_time = time.time()  # 记录第一次检测到暂停的时间
        elif b == 3 and int(speed) >= 2:
            # 当暂停时间间隔小于2秒时，执行原elif的代码
            try:
                if int(speed)>2:
                    print(color.red(f'当前视频已被设置不能调节高倍数，现在将倍数调至2倍'), flush=True)
                    new_speed=2
                    account_info['speed'] = '2'
                else:
                    new_speed=1
                    print(color.red(f'当前视频已被设置不能调节高倍数，现在将倍数调至1倍'), flush=True)
                    account_info['speed'] = '1'
                for j in range(int(int(speed) - new_speed) * 10):
                    pyautogui.press('a')
                    action = ActionChains(driver)
                    action.send_keys('a').perform()
                    time.sleep(0.1)
                print(color.green('调节成功'), flush=True)
                try:
                    driver.find_element(By.CSS_SELECTOR,
                                        '[class="vjs-play-control vjs-control vjs-button vjs-paused"]').click()
                except:
                    print(color.yellow(f'点击播放失败'), flush=True)
            except:
                pass
            with open(r'task/tool/account_info.json', 'w', encoding='utf-8') as fil:
                json.dump(account_info, fil)
        elif b==3 and int(speed)==1:
            raise Exception('视频播放异常')
    else:
        pause_start_time = 0  # 视频正常播放，重置暂停时间记录
        b=0

def handle_video_error_alert(driver):
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        if "视频播放异常" in alert_text:
            print(color.red("检测到视频播放异常弹窗，尝试刷新页面..."))
            alert.accept()
            time.sleep(2)
            driver.refresh()
            # 刷新后需要重新进入 iframe，具体逻辑根据实际情况补充
            raise Exception('视频播放异常')
        else:
            alert.accept()
            raise Exception('视频播放异常')
    except NoAlertPresentException:
        return

def check_vido_finish(driver,i,time_start,total_time,vido_iframe,lock_screen,API,video_title_choice,speed,pass_face):
    last_time = 0
    h = 0
    quiz_stall = 0  # 题目弹窗连续卡住的次数
    # 判断是否完成任务
    while True:
        time.sleep(1)
        # 每次切换前先处理可能存在的弹窗
        # handle_video_error_alert(driver)
        driver.switch_to.default_content()
        driver.switch_to.frame('iframe')
        elements2 = driver.find_elements(By.CLASS_NAME, 'ans-job-icon-clear ')
        element2 = elements2[i]
        # 定位到该元素的上一级（父元素）
        parent_element2 = element2.find_element(By.XPATH, "..")
        # 获取 parent_element2 的class值
        parent_element2_class = parent_element2.get_attribute("class")
        txt = element2.get_attribute('aria-label')
        # print(parent_element2_class, flush=True)
        if txt == '任务点已完成' or 'ans-attach-ct ans-job-finished' in parent_element2_class:
            # pyautogui.scroll(-250)
            print(color.green(f'已完成第{i + 1}个视频'), flush=True)
            time_end = time.time()
            print(color.green('总共耗费了%.2f秒.' % (time_end - time_start)), flush=True)
            break
        else:
            driver.switch_to.default_content()
            driver.switch_to.frame('iframe')
            driver.switch_to.frame(vido_iframe)
            check_internet(driver)
            check_video_question(driver,API,video_title_choice)
            # 兜底：题目弹窗还在就说明这题没过去，弹窗会把视频卡住，超时强制关掉
            if _quiz_popup(driver) is not None:
                quiz_stall += 1
                if quiz_stall == 15:
                    print(color.red('题目弹窗一直没关掉，强制关闭后继续播放'), flush=True)
                    _dump_quiz_html(driver)
                    _leave_quiz(driver)
                elif quiz_stall >= 30:
                    quiz_stall = 0
                    raise Exception('视频题目弹窗无法关闭')
            else:
                quiz_stall = 0
            element = driver.find_element(By.CLASS_NAME, 'vjs-current-time-display')
            current_time = element.text
            check_vido_play(driver, last_time, current_time,speed,pass_face,vido_iframe)
            last_time = current_time
            if current_time == total_time:
                if h == 0:
                    h += 1
                    try:
                        print(color.yellow('视频已播放完毕，但任务点仍未完成，开始重播'), flush=True)
                        driver.find_element(By.CSS_SELECTOR,
                                            '[class="vjs-play-control vjs-control vjs-button vjs-paused vjs-ended"]').click()
                    except:
                        print(color.red(f'点击失败'), flush=True)
                else:
                    print(color.green(f'已完成第{i + 1}个视频'), flush=True)
                    time_end = time.time()
                    print(color.green('总共耗费了%.2f秒.' % (time_end - time_start)), flush=True)
                    break
            if lock_screen:
                pyautogui.move(20, 0, )
                pyautogui.move(-20, 0)
    return True

def study_page(driver,course_name,lock_screen,API,video_title_choice,pass_vido,speed,pass_face):
    global drag_progress_condition
    driver.switch_to.default_content()
    driver.switch_to.frame('iframe')
    try:
        # 判断是否完成任务
        elements1 = driver.find_elements(By.CLASS_NAME, 'ans-job-icon-clear ')
        print(color.magenta(f'已检测到{len(elements1)}个视频包含有任务点'),flush=True)
    except:
        pyautogui.scroll(-250)
        print(color.green('视频已完成,点击下一节'),flush=True)
        return

    for i in range(len(elements1)):
        drag_progress_condition = True
        element1=elements1[i]
        # 定位到该元素的上一级（父元素）
        parent_element = element1.find_element(By.XPATH, "..")
        try:
            # 获取 parent_element 的class值
            parent_element_class=parent_element.get_attribute("class")
            txt = element1.get_attribute('aria-label')
        except:
            txt = ''
            parent_element_class=''
        if txt == '任务点未完成' and 'ans-attach-ct' in parent_element_class:
            vido_iframe=element1.find_element(By.XPATH, "following-sibling::iframe[1]")
            driver.execute_script("arguments[0].scrollIntoView();", vido_iframe)
            driver.switch_to.frame(vido_iframe)
            print(color.green(f'开始播放第{i + 1}个视频'),flush=True)
            time_start=time.time()
            try:
                driver.find_element(By.CLASS_NAME,'vjs-big-play-button').click()
            except:
                pass
            #点击我知道了
            driver.switch_to.default_content()
            delete_face_popup(driver,pass_face)
            driver.switch_to.frame('iframe')
            driver.switch_to.frame(vido_iframe)

            # 每个视频都按实际 playbackRate 重新校准，平台限速时不会白按
            try:
                apply_speed(driver, speed)
            except Exception as error:
                print(color.yellow(f'倍速校准跳过：{error}'), flush=True)

            try:
                element=driver.find_element(By.CLASS_NAME,'writeNote_vid_blue')
                element.click()
            except:
                pass
            try:
                print(color.blue('调节音量'), flush=True)
                element = driver.find_element(By.XPATH, '//*[@id="video"]/div[6]/div[6]')
                element.click()
                print(color.green('调节成功'), flush=True)
            except:
                print(color.yellow('未找到音量，或已经调节'), flush=True)

            time.sleep(1)
            element=driver.find_element(By.CLASS_NAME,'vjs-duration-display')
            total_time=element.text
            if  total_time=='' or total_time=='0:00':
                print(color.red('获取视频总时长失败'),flush=True)
                total_time='1'
            else:
                print(color.green(f'该视频总时长为：{total_time}'),flush=True)
            click_video_progress_end(driver,pass_vido)
            print(color.yellow('请不要将窗口最小化，这有可能导致脚本异常\n视频播放完毕会自动跳转\n正在观看视频中……'),flush=True)
            driver.switch_to.default_content()
            driver.switch_to.frame('iframe')
            b = 0
            pause_start_time = 0  # 添加变量记录暂停开始时间
            check_vido_finish(driver,i,time_start,total_time,vido_iframe,lock_screen,API,video_title_choice,speed,pass_face)
            save_record(driver, course_name, time, vido_iframe, '视频')
        driver.switch_to.default_content()
        # check_face(driver,driver.current_url,'popDiv1 wid640  faceCollectQrPopVideo  popClass faceRecognition_0')
        driver.switch_to.frame('iframe')
    print(color.green('所有视频均已完成'),flush=True)
    return
