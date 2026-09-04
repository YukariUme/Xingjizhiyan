"""MockCodeJudgeService 单元测试。"""

from app.services.judge.mock import MockCodeJudgeService


def _cases() -> list[dict]:
    return [
        {"id": 1, "name": "函数定义", "check": "contains", "value": "def reverse_list"},
        {"id": 2, "name": "指针反转", "check": "contains", "value": ".next"},
    ]


def test_accept_verdict():
    judge = MockCodeJudgeService()
    code = "def reverse_list(head):\n    prev = None\n    while head:\n        nxt = head.next\n        head.next = prev\n        prev = head\n        head = nxt\n    return prev\n"
    result = judge.judge(code, "python", _cases())
    assert result.verdict == "accepted"
    assert result.passed_tests == 2
    assert result.total_tests == 2
    assert not result.error_message


def test_wrong_answer_verdict():
    judge = MockCodeJudgeService()
    result = judge.judge("def reverse_list(head):\n    pass\n", "python", _cases())
    assert result.verdict == "wrong_answer"
    assert result.passed_tests < result.total_tests
    assert result.error_message
    assert any(not r.passed for r in result.report)


def test_compile_error_on_empty():
    judge = MockCodeJudgeService()
    result = judge.judge("", "python", _cases())
    assert result.verdict == "compile_error"


def test_unsupported_language():
    judge = MockCodeJudgeService()
    result = judge.judge("print(1)", "brainfuck", _cases())
    assert result.verdict == "compile_error"
    assert "暂不支持" in result.error_message


def test_cross_language_function_name_check():
    """“def reverse_list”这类测试点在 C/C++/Java 中按函数名判定，兼容驼峰命名。"""
    judge = MockCodeJudgeService()
    cases = [
        {"id": 1, "name": "函数定义", "check": "contains", "value": "def reverse_list", "hint": "需要定义 reverse_list"},
        {"id": 2, "name": "主体实现", "check": "contains", "value": "while", "hint": "需要循环遍历"},
        {"id": 3, "name": "空值处理", "check": "contains", "value": "None", "hint": "需要处理空链表"},
    ]
    python_ok = judge.judge(
        "def reverse_list(head):\n    prev = None\n    while head:\n        nxt = head.next\n        head.next = prev\n        prev = head\n        head = nxt\n    return prev",
        "python", cases,
    )
    assert python_ok.verdict == "accepted"
    java_ok = judge.judge(
        "class Solution {\n    public ListNode reverseList(ListNode head) {\n        ListNode prev = null;\n        while (head != null) {\n            ListNode nxt = head.next;\n            head.next = prev;\n            prev = head;\n            head = nxt;\n        }\n        return prev;\n    }\n}",
        "java", cases,
    )
    assert java_ok.verdict == "accepted"
    c_ok = judge.judge(
        "struct Node* reverse_list(struct Node* head) {\n    struct Node* prev = NULL;\n    while (head) {\n        struct Node* nxt = head->next;\n        head->next = prev;\n        prev = head;\n        head = nxt;\n    }\n    return prev;\n}",
        "c", cases,
    )
    assert c_ok.verdict == "accepted"
    cpp_ok = judge.judge(
        "Node* reverseList(Node* head) {\n    Node* prev = nullptr;\n    while (head) {\n        Node* nxt = head->next;\n        head->next = prev;\n        prev = head;\n        head = nxt;\n    }\n    return prev;\n}",
        "cpp", cases,
    )
    assert cpp_ok.verdict == "accepted"
    # None → null 跨语言等价
    java_null = judge.judge(
        "class Solution {\n    public ListNode reverseList(ListNode head) {\n        ListNode prev = null;\n        while (head != null) {\n            ListNode nxt = head.next;\n            head.next = prev;\n            prev = head;\n            head = nxt;\n        }\n        return prev;\n    }\n}",
        "java", cases,
    )
    assert java_null.verdict == "accepted"
    wrong = judge.judge("void foo() {}\n", "c", cases)
    assert wrong.verdict == "wrong_answer"
