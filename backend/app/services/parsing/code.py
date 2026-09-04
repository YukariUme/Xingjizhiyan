"""代码块识别：从文本/OCR 行流中识别代码区域。"""

import re


_CODE_KEYWORDS = {
    "c": {"#include", "int main", "printf", "scanf", "return 0", "malloc", "struct "},
    "cpp": {"#include", "int main", "using namespace std", "std::", "cout", "cin", "class "},
    "java": {"public static void main", "public class", "System.out", "import java", "private "},
    "python": {"def ", "import ", "from ", "print(", "if __name__", "class ", "return "},
    "sql": {"select", "insert into", "update ", "create table", "where ", "from "},
}


def detect_code_language(text: str) -> str | None:
    """按关键词启发式识别代码语言；不确定返回 None。"""
    lowered = text.lower()
    best, best_score = None, 0
    for lang, keywords in _CODE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lowered)
        if score > best_score:
            best, best_score = lang, score
    return best if best_score >= 2 else None


def looks_like_code(text: str) -> bool:
    """判断一段文本是否为代码块（缩进 + 关键词 + 标点特征）。"""
    if not text or len(text) < 3:
        return False
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    indented = sum(1 for line in lines if re.match(r"^\s{2,}", line))
    ratio = indented / len(lines)
    lang = detect_code_language(text)
    braces = text.count("{") + text.count("}")
    semicolons = text.count(";")
    return bool(
        (ratio >= 0.5 and (braces >= 2 or semicolons >= 2))
        or (lang is not None and len(lines) >= 3)
    )
