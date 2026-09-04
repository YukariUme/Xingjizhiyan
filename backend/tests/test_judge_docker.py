"""Docker 沙箱判题测试：结果解析/判定纯逻辑 + Docker 可用时的端到端。"""

import pathlib
import shutil
import subprocess

import pytest

from app.services.judge.docker import DockerCodeJudgeService


def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def test_read_results_parsing():
    """results.txt 解析：PASS/WA/TLE/RE/CE 各行。"""
    service = DockerCodeJudgeService()
    tmp = pathlib.Path(".").resolve() / "tmp_results"
    tmp.mkdir(exist_ok=True)
    try:
        (tmp / "results.txt").write_text(
            "PASS|12\nFAIL|WA|输出与期望不符\nFAIL|TLE|运行超时\n", encoding="utf-8"
        )
        rows = service._read_results(tmp)
        assert rows[0] == (1, "PASS", "accepted", "12")
        assert rows[1] == (2, "FAIL", "wrong_answer", "输出与期望不符")
        assert rows[2] == (3, "FAIL", "time_limit_exceeded", "运行超时")
    finally:
        import shutil as _sh

        _sh.rmtree(tmp, ignore_errors=True)


def test_compile_error_stops_parsing():
    service = DockerCodeJudgeService()
    tmp = pathlib.Path(".").resolve() / "tmp_results"
    tmp.mkdir(exist_ok=True)
    try:
        (tmp / "results.txt").write_text("CE|语法错误\nPASS|1\n", encoding="utf-8")
        rows = service._read_results(tmp)
        assert rows == [(1, "FAIL", "compile_error", "语法错误")]
    finally:
        import shutil as _sh

        _sh.rmtree(tmp, ignore_errors=True)


def test_docker_unavailable_message():
    result = DockerCodeJudgeService._docker_unavailable("测试错误", [{"id": 1}])
    assert result.verdict == "internal_error"
    assert result.metadata["available"] is False


@pytest.mark.skipif(not _docker_available(), reason="本机未安装/未启动 Docker")
def test_docker_python_accepted():
    """Docker 端到端：两数之和 → accepted。"""
    service = DockerCodeJudgeService()
    result = service.judge(
        "a, b = map(int, input().split())\nprint(a + b)\n",
        "python",
        [
            {"id": 1, "name": "样例1", "input": "1 2\n", "output": "3\n"},
            {"id": 2, "name": "样例2", "input": "10 -4\n", "output": "6\n"},
        ],
    )
    assert result.verdict == "accepted", result.error_message
    assert result.passed_tests == 2


@pytest.mark.skipif(not _docker_available(), reason="本机未安装/未启动 Docker")
def test_docker_python_wrong_answer():
    service = DockerCodeJudgeService()
    result = service.judge(
        "print('hello')\n",
        "python",
        [{"id": 1, "name": "样例", "input": "", "output": "world\n"}],
    )
    assert result.verdict == "wrong_answer"
