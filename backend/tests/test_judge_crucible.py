"""CodeCrucible 判题接入测试：本地执行器（IO/WA/CE/TLE/静态检查）。"""

import os
import shutil

import pytest

from app.services.judge.codecrucible import (
    VERDICT_AC,
    VERDICT_CE,
    VERDICT_TLE,
    VERDICT_WA,
    CodeCrucibleJudgeService,
)


@pytest.fixture
def judge():
    return CodeCrucibleJudgeService()


def test_python_io_accepted(judge):
    """IO 测试点：输入两数，输出和 → accepted。"""
    code = "a, b = map(int, input().split())\nprint(a + b)\n"
    cases = [
        {"id": 1, "name": "样例1", "input": "1 2\n", "output": "3\n"},
        {"id": 2, "name": "样例2", "input": "10 -4\n", "output": "6\n"},
    ]
    result = judge.judge(code, "python", cases)
    assert result.verdict == VERDICT_AC
    assert result.passed_tests == 2
    assert result.total_tests == 2


def test_python_wrong_answer(judge):
    code = "print('hello')\n"
    cases = [{"id": 1, "name": "样例", "input": "", "output": "world\n"}]
    result = judge.judge(code, "python", cases)
    assert result.verdict == VERDICT_WA
    assert result.passed_tests == 0


def test_python_compile_error(judge):
    result = judge.judge("def broken(:\n    pass\n", "python", [{"id": 1, "input": "", "output": ""}])
    assert result.verdict == VERDICT_CE


def test_python_time_limit(judge, monkeypatch):
    """死循环 + 极小限时 → TLE（墙钟兜底，Windows 也生效）。"""
    monkeypatch.setattr("app.services.judge.codecrucible._WALL_SLACK_SECONDS", 0)
    code = "while True:\n    pass\n"
    cases = [{"id": 1, "name": "超时", "input": "", "output": "", "time_limit_ms": 200}]
    result = judge.judge(code, "python", cases)
    assert result.verdict == VERDICT_TLE


def test_legacy_static_check(judge):
    """旧式 contains 静态测试点兼容。"""
    code = "def reverse_list(xs):\n    return list(reversed(xs))\n"
    cases = [
        {"id": 1, "name": "函数定义", "check": "contains", "value": "def reverse_list", "hint": "需要定义函数"},
        {"id": 2, "name": "返回", "check": "contains", "value": "return", "hint": "需要返回结果"},
    ]
    result = judge.judge(code, "python", cases)
    assert result.verdict == VERDICT_AC


@pytest.mark.skipif(not shutil.which("gcc"), reason="本机无 gcc")
def test_c_language_accepted(judge):
    code = '#include <stdio.h>\nint main(){int a,b;scanf("%d%d",&a,&b);printf("%d\\n",a+b);return 0;}\n'
    cases = [{"id": 1, "name": "样例", "input": "1 2\n", "output": "3\n"}]
    result = judge.judge(code, "c", cases)
    assert result.verdict == VERDICT_AC, result.error_message


@pytest.mark.skipif(not shutil.which("g++"), reason="本机无 g++")
def test_cpp_language_accepted(judge):
    code = '#include <iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a+b<<std::endl;}\n'
    cases = [{"id": 1, "name": "样例", "input": "1 2\n", "output": "3\n"}]
    result = judge.judge(code, "cpp", cases)
    assert result.verdict == VERDICT_AC, result.error_message


@pytest.mark.skipif(not shutil.which("javac"), reason="本机无 javac")
def test_java_language_accepted(judge):
    code = (
        "import java.util.Scanner;\n"
        "public class Main {\n"
        "  public static void main(String[] args) {\n"
        "    Scanner sc = new Scanner(System.in);\n"
        "    System.out.println(sc.nextInt() + sc.nextInt());\n"
        "  }\n"
        "}\n"
    )
    cases = [{"id": 1, "name": "样例", "input": "1 2\n", "output": "3\n"}]
    result = judge.judge(code, "java", cases)
    assert result.verdict == VERDICT_AC, result.error_message


def test_unsupported_language(judge):
    result = judge.judge("x", "ruby", [])
    assert result.verdict == VERDICT_CE
