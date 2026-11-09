"""配置读写管理器，统一管理 account_info.json 和 course_name.json 的读写"""
import json

try:  # 版本号以 version.py 为准；被单独引用时也不至于炸
    from version import APP_VERSION as _APP_VERSION
except Exception:  # pragma: no cover - 极少数脱离项目根的调用场景
    _APP_VERSION = ""

class ConfigManager:
    ACCOUNT_PATH = r'task/tool/account_info.json'
    COURSE_PATH = r'task/tool/course_name.json'
    VERSION_PATH = r'task/tool/version_info'
    HELP_PATH = r'task/tool/Help.txt'
    COURSE_PROCESS_PATH = r'task/tool/course_process.json'

    def __init__(self):
        self._account_info = {}

    # ========== 账户信息 ==========
    def load_account(self) -> dict:
        try:
            with open(self.ACCOUNT_PATH, 'r', encoding='utf-8') as f:
                self._account_info = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._account_info = {}
        return self._account_info

    def save_account(self, account_info: dict) -> bool:
        """增量保存：只覆盖传入的键，文件里其它配置原样保留。

        以前是整文件覆盖，只要有人传了不完整的 dict（比如只带 user_notice），
        账号、课程、倍速这些就一起被抹掉，表现就是「保存不下来」。
        """
        merged = {}
        try:
            with open(self.ACCOUNT_PATH, 'r', encoding='utf-8') as f:
                old = json.load(f)
            if isinstance(old, dict):
                merged.update(old)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            merged = {}
        if isinstance(account_info, dict):
            merged.update(account_info)
        try:
            with open(self.ACCOUNT_PATH, 'w', encoding='utf-8') as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)
            self._account_info = merged
            return True
        except (PermissionError, OSError):
            return False

    def get_account(self) -> dict:
        return self._account_info

    # ========== 课程数据 ==========
    def load_courses(self, phone_number: str) -> list:
        try:
            with open(self.COURSE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        return data.get(phone_number, [])

    def save_courses(self, phone_number: str, courses: list):
        try:
            with open(self.COURSE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        existing = data.get(phone_number, []) or []
        merged = []
        for name in list(existing) + list(courses or []):
            name = (name or "").strip()
            if name and name not in merged:
                merged.append(name)
        data[phone_number] = merged
        with open(self.COURSE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def set_courses(self, phone_number: str, courses: list):
        """整体替换某账号的课程列表（登录后刷新用，保持平台原有顺序）。"""
        try:
            with open(self.COURSE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        names = []
        for name in courses or []:
            name = (name or "").strip()
            if name and name not in names:
                names.append(name)
        data[phone_number] = names
        with open(self.COURSE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return names

    # ========== 便捷方法 ==========
    def get_version(self) -> str:
        if _APP_VERSION:
            return _APP_VERSION
        try:
            with open(self.VERSION_PATH, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            return '0.0.0'

    def get_help_text(self) -> str:
        try:
            with open(self.HELP_PATH, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return '帮助文档未找到'
    def get_course_process(self) -> dict:
        try:
            with open(self.COURSE_PROCESS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)

        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def count_video_records(self) -> int:
        import os
        record_dir = 'task/record'
        if not os.path.isdir(record_dir):
            return 0
        total = 0
        for fname in os.listdir(record_dir):
            if '刷课记录' in fname and fname.endswith('.txt'):
                try:
                    with open(os.path.join(record_dir, fname), 'r', encoding='utf-8') as f:
                        total += f.read().count('视频')
                except Exception:
                    pass
        return total

    def get_popup_count(self) -> int:
        account = self.load_account()
        return account.get('popup_count', 0)

    def increment_popup_count(self, video_count: int):
        account = self.load_account()
        account['popup_count'] = video_count
        self.save_account(account)