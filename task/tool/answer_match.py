# -*- coding: utf-8 -*-
"""把 AI / 题库返回的答案换算成选项下标。

这个模块只做纯文本处理，不依赖 Selenium，方便直接单测。

答案的常见形式：
    "B" / "B、错" / "B. 错"      -> 字母
    "AB" / "A,B" / "A、C"       -> 多选字母
    "实体经济" / "B、实体经济"    -> 选项原文
    "对" / "正确" / "T" / "√"    -> 判断题
"""
from __future__ import annotations

import ast
import re
from difflib import SequenceMatcher

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# 规范化时去掉的标点/空白
_PUNCT_RE = re.compile(r'[\s\.、,，;；:：()（）\[\]【】"\'“”‘’_\-]+')

# 全角转半角（字母 / 数字 / 常用标点）
_FULLWIDTH = str.maketrans(
    "ＡＢＣＤＥＦＧＨａｂｃｄｅｆｇｈ０１２３４５６７８９，。；：（）",
    "ABCDEFGHabcdefgh0123456789,.;:()")

_TRUE_WORDS = ("正确", "对", "是", "√", "TRUE", "YES", "T")
_FALSE_WORDS = ("错误", "错", "否", "×", "FALSE", "NO", "F")

# "B、错" / "B. 错" / "B) 错" 这种带选项字母的写法
_LEADING_LETTER_RE = re.compile(r"^\s*([A-Ha-hＡ-Ｈ])\s*[、.．,，:：)）]\s*\S")
_LETTERS_ONLY_RE = re.compile(r"^[A-H]{1,8}$")
_LETTER_BLOCK_RE = re.compile(r"^[A-Ha-h,，、;；\s]+$")


def normalize(text) -> str:
    """去空白、去标点、全角转半角、转大写，只用于比较。"""
    value = str(text or "").translate(_FULLWIDTH)
    return _PUNCT_RE.sub("", value).upper()


def leading_letter(text):
    """从 "B、错" 里取出 B 的下标；没有带字母前缀时返回 None。"""
    match = _LEADING_LETTER_RE.match(str(text or ""))
    if not match:
        return None
    letter = match.group(1).translate(_FULLWIDTH).upper()
    return LETTERS.index(letter)


def judgment_value(text):
    """判断题文字 -> True/False/None。"""
    key = normalize(text)
    if not key:
        return None
    for word in _TRUE_WORDS:
        if word in key:
            return True
    for word in _FALSE_WORDS:
        if word in key:
            return False
    return None


def to_items(answer):
    """把答案统一成字符串列表，兼容列表、列表字符串、A/B、A、B 等写法。"""
    if isinstance(answer, (list, tuple, set)):
        raw_items = [str(item) for item in answer]
    else:
        text = str(answer or "").strip()
        raw_items = [text]
        if text.startswith("[") and text.endswith("]"):
            try:
                value = ast.literal_eval(text)
            except Exception:
                value = None
            if isinstance(value, (list, tuple)):
                raw_items = [str(item) for item in value]

    items = []
    for raw in raw_items:
        for chunk in re.split(r"[/|]", raw):
            chunk = chunk.strip().strip('[]"\'')
            if not chunk:
                continue
            if _LETTER_BLOCK_RE.match(chunk) and re.search(r"[A-Ha-h]", chunk):
                items.extend(letter.upper() for letter in re.findall(r"[A-Ha-h]", chunk))
            else:
                items.append(chunk)
    return items


def answer_text(answer) -> str:
    """把简答/论述类答案拼成可输入的一段文字。"""
    if isinstance(answer, (list, tuple, set)):
        return "".join(str(item) for item in answer)
    text = str(answer or "").strip()
    if text.startswith("[") and text.endswith("]"):
        try:
            value = ast.literal_eval(text)
        except Exception:
            value = None
        if isinstance(value, (list, tuple)):
            return "".join(str(item) for item in value)
    return text


def split_batch(raw):
    """把批量搜题返回的 "A/B/ABCD" 或 ["A","B"] 切成每题一条。"""
    text = str(raw or "").strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            value = ast.literal_eval(text)
        except Exception:
            value = None
        if isinstance(value, (list, tuple)):
            return [str(item).strip() for item in value if str(item).strip()]
    parts = [part.strip().strip('[]"\'') for part in re.split(r"[/\n]", text)]
    return [part for part in parts if part]


def split_blanks(answer, count: int):
    """填空题答案按空拆分；数量不足时补空串。"""
    items = to_items(answer)
    if len(items) == 1 and count > 1:
        parts = [part.strip() for part in re.split(r"[\s,，;；]+", items[0]) if part.strip()]
    else:
        parts = [str(item).strip() for item in items if str(item).strip()]
    if len(parts) < count:
        parts += [""] * (count - len(parts))
    return parts[:count]


def _add(indices, index):
    if index is not None and index >= 0 and index not in indices:
        indices.append(index)


def match_indices(answer, options, question_type: str = ""):
    """把答案换算成选项下标，匹配不到返回空列表。"""
    opts = [str(option) for option in (options or [])]
    if not opts:
        return []
    norm_opts = [normalize(option) for option in opts]
    indices = []

    for item in to_items(answer):
        raw = str(item).strip()
        if not raw:
            continue

        # 1) "B、错" / "B. 错"：字母 + 分隔符，优先信字母
        letter = leading_letter(raw)
        if letter is not None and letter < len(opts):
            _add(indices, letter)
            continue

        key = normalize(raw)
        if not key:
            continue

        # 2) "B" / "AB" / "ACD"：纯字母
        if _LETTERS_ONLY_RE.match(key):
            mapped = [LETTERS.index(letter) for letter in key]
            mapped = [index for index in mapped if index < len(opts)]
            if mapped:
                indices.extend(index for index in mapped if index not in indices)
                continue

        # 3) 判断题：对/错/正确/错误/√/× 映射到选项
        if question_type == "判断题":
            value = judgment_value(raw)
            if value is not None:
                matched = next((index for index, option in enumerate(opts)
                                if judgment_value(option) is value), None)
                if matched is not None:
                    _add(indices, matched)
                    continue

        # 4) 选项原文（题库通常直接返回选项文本）
        exact = [index for index, option in enumerate(norm_opts) if option == key]
        if exact:
            _add(indices, exact[0])
            continue

        contains = [(len(option), index) for index, option in enumerate(norm_opts)
                    if option and (key in option or option in key)]
        if contains:
            contains.sort()
            _add(indices, contains[0][1])
            continue

        # 5) 兜底：相似度足够高才算命中，避免乱点
        if len(key) >= 3:
            best_ratio, best_index = 0.0, None
            for index, option in enumerate(norm_opts):
                if not option:
                    continue
                ratio = SequenceMatcher(None, key, option).ratio()
                if ratio > best_ratio:
                    best_ratio, best_index = ratio, index
            if best_index is not None and best_ratio >= 0.65:
                _add(indices, best_index)

    return sorted(indices)
