"""演示数据初始化：账号、课程、知识库、论文、作业、提交与画像。"""

import hashlib
from datetime import timedelta

from sqlalchemy.orm import Session

from app.database import utcnow
from app.mock.curriculum import EXTRA_KNOWLEDGE_POINTS, FULL_CHAPTERS
from app.mock.knowledge import KNOWLEDGE_DOCUMENTS, KNOWLEDGE_POINTS
from app.mock.papers import PAPERS
from app.mock.users import DEMO_USERS
from app.models import (
    Activity,
    Assignment,
    ChatMessage,
    CodeSubmission,
    Course,
    CourseChapter,
    CourseKnowledgeSpace,
    Enrollment,
    KnowledgeDocument,
    KnowledgePoint,
    LessonPlan,
    Paper,
    PaperReading,
    Question,
    ResearchTopic,
    Submission,
    SubjectiveSubmission,
    User,
)
from app.services.agent.factory import get_agent_service
from app.services.grading_service import GradingService
from app.services.learning_path_service import LearningPathService
from app.services.llm.mock import MockLLMService
from app.services.prompt import PromptService
from app.services.rag.factory import get_rag_service
from app.services.rag.sqlite import SQLiteRAGService


def _hash(username: str, password: str) -> str:
    return hashlib.sha256(f"{username}:{password}".encode()).hexdigest()


def seed_if_empty(db: Session) -> None:
    if db.query(User).first():
        return
    seed_all(db)


def seed_all(db: Session) -> None:
    now = utcnow()
    # ---------- 用户 ----------
    users: dict[str, User] = {}
    for data in DEMO_USERS:
        user = User(
            username=data["username"],
            display_name=data["display_name"],
            password_hash=_hash(data["username"], "123456"),
            role=data["role"],
            identity=(
                "teacher"
                if data["role"] == "teacher"
                else "graduate"
                if data["role"] == "researcher"
                else "student"
            ),
            modes=(
                ["teaching", "research"]
                if data["role"] == "teacher"
                else ["research", "learning"]
                if data["role"] == "researcher"
                else ["learning", "research"]
            ),
            title=data["title"],
            bio=data["bio"],
        )
        db.add(user)
        users[data["username"]] = user
    db.commit()

    teacher = users["teacher1"]
    students = [users[f"student{i}"] for i in range(1, 7)]
    researcher = users["researcher1"]

    # ---------- 课程与选课 ----------
    course_defs = [
        ("数据结构", "CS201", "线性表、栈队列、树与图、排序与查找", "2026 春季"),
        ("算法设计与分析", "CS301", "分治、动态规划、贪心、回溯与复杂度分析", "2026 春季"),
        ("操作系统", "CS210", "进程线程、同步互斥、内存管理与调度", "2026 春季"),
        ("计算机网络", "CS220", "分层模型、TCP/IP、HTTP 与 DNS", "2026 春季"),
        ("数据库系统", "CS230", "关系模型、SQL、事务与索引", "2026 秋季"),
        ("人工智能", "CS240", "机器学习、深度学习、大模型与 RAG", "2026 秋季"),
        ("计算机组成原理", "CS250", "数据表示、存储系统、指令系统与 CPU", "2026 秋季"),
    ]
    courses: dict[str, Course] = {}
    for name, code, desc, semester in course_defs:
        course = Course(
            name=name,
            code=code,
            description=desc,
            semester=semester,
            teacher_id=teacher.id,
        )
        db.add(course)
        courses[name] = course
    db.commit()

    # 课程章节 + 课程知识空间
    chapter_map: dict[str, CourseChapter] = {}
    for course_name, chapters in FULL_CHAPTERS.items():
        course = courses.get(course_name)
        if not course:
            continue
        db.add(CourseKnowledgeSpace(course_id=course.id, enabled=True, default_scope="official"))
        for index, ch in enumerate(chapters, start=1):
            chapter = CourseChapter(
                course_id=course.id,
                order=index,
                key=ch["key"],
                title=ch["title"],
                official_ref=ch["official_ref"],
                summary=ch["summary"],
            )
            db.add(chapter)
            chapter_map[f"{course_name}:{ch['official_ref']}"] = chapter
    db.commit()
    for sid, student in enumerate(students):
        enrollments = [
            courses["数据结构"],
            courses["操作系统"],
            courses["算法设计与分析"],
            courses["计算机网络"] if sid % 2 == 0 else courses["数据库系统"],
        ]
        for course in enrollments:
            if not db.query(Enrollment).filter_by(course_id=course.id, student_id=student.id).first():
                db.add(Enrollment(course_id=course.id, student_id=student.id))
    db.commit()

    # ---------- 知识库：知识点 + 文档 + 切分索引 ----------
    rag = get_rag_service()
    kp_map: dict[str, KnowledgePoint] = {}
    for data in KNOWLEDGE_POINTS + EXTRA_KNOWLEDGE_POINTS:
        kp_data = dict(data)
        chapter = None
        chapter_text = kp_data.get("chapter", "")
        for course_name, chapters in FULL_CHAPTERS.items():
            if course_name in (kp_data.get("subject") or ""):
                for ch in chapters:
                    if ch["official_ref"] in chapter_text:
                        chapter = chapter_map.get(f"{course_name}:{ch['official_ref']}")
                        break
        kp = KnowledgePoint(**kp_data)
        kp.chapter_id = chapter.id if chapter else None
        if kp.name == "树与二叉树":
            kp.related_points = ["递归", "栈和队列"]
        elif kp.name == "动态规划":
            kp.related_points = ["分治策略", "算法复杂度分析"]
        elif kp.name == "进程同步与互斥":
            kp.related_points = ["进程与线程"]
        db.add(kp)
        kp_map[data["name"]] = kp
    db.commit()
    for data in KNOWLEDGE_DOCUMENTS:
        doc = KnowledgeDocument(
            title=data["title"],
            source=data["source"],
            course=data["course"],
            topic=data["topic"],
            chapter=data["chapter"],
            difficulty=data["difficulty"],
            type=data["type"],
            year=data["year"],
            content=data["content"],
            metadata_json={
                "title": data["title"],
                "source": data["source"],
                "course": data["course"],
                "topic": data["topic"],
                "chapter": data["chapter"],
                "difficulty": data["difficulty"],
                "type": data["type"],
                "year": data["year"],
            },
        )
        course = courses.get(data["course"])
        doc.course_id = course.id if course else None
        doc.source_level = "S"
        doc.visibility = "official"
        db.add(doc)
        db.flush()
        rag.ingest_document(db, doc.id)

    # ---------- 论文库 ----------
    paper_objs: dict[int, Paper] = {}
    for data in PAPERS:
        paper = Paper(**data)
        db.add(paper)
        paper_objs[paper.id] = paper
    db.commit()

    # ---------- 作业 ----------
    q1 = Question(
        qtype="programming",
        title="反转单链表",
        description="给定一个单链表头节点，反转该链表并返回新的头节点。要求：定义 reverse_list(head) 函数，处理空链表与单节点链表。",
        language="python",
        code_template="def reverse_list(head):\n    # TODO: 实现反转\n    pass\n",
        max_score=10,
        knowledge_point_ids=[kp_map["线性表"].id],
        test_cases=[
            {"id": 1, "name": "示例：1->2->3 反转", "check": "contains", "value": "def reverse_list", "hint": "需要定义 reverse_list 函数"},
            {"id": 2, "name": "链表指针反转", "check": "contains", "value": ".next", "hint": "需要通过 next 指针逐节点反转"},
            {"id": 3, "name": "空链表处理", "check": "contains", "value": "None", "hint": "需要处理空链表/单节点边界"},
        ],
    )
    q2 = Question(
        qtype="subjective",
        title="二叉树前序遍历",
        description="简述二叉树前序遍历（根左右）的递归思想，并说明前序、中序、后序遍历的区别。",
        language="python",
        code_template="",
        max_score=10,
        knowledge_point_ids=[kp_map["树与二叉树"].id],
        test_cases=[],
    )
    q3 = Question(
        qtype="report",
        title="迷宫求解实验报告",
        description="完成 BFS 迷宫求解实验，提交实验报告：实验目的、方法、结果截图与总结。",
        language="python",
        code_template="",
        max_score=15,
        knowledge_point_ids=[kp_map["图"].id, kp_map["栈和队列"].id],
        test_cases=[],
    )
    assignment1 = Assignment(
        title="数据结构 · 作业一：链表与树",
        description="本作业覆盖线性表与二叉树两大章节，包含编程题、简答题与实验报告。",
        course_id=courses["数据结构"].id,
        teacher_id=teacher.id,
        due_at=now + timedelta(days=5),
        status="published",
    )
    db.add(assignment1)
    db.flush()
    for q in (q1, q2, q3):
        q.assignment_id = assignment1.id
        db.add(q)

    q4 = Question(
        qtype="programming",
        title="快速排序",
        description="实现快速排序函数 quick_sort(arr)，返回排序后的新列表。",
        language="python",
        code_template="def quick_sort(arr):\n    # TODO\n    pass\n",
        max_score=10,
        knowledge_point_ids=[kp_map["排序算法"].id, kp_map["分治策略"].id],
        test_cases=[
            {"id": 1, "name": "函数定义", "check": "contains", "value": "def quick_sort", "hint": "需要定义 quick_sort 函数"},
            {"id": 2, "name": "递归分治", "check": "contains", "value": "quick_sort(", "hint": "需要递归调用自身"},
            {"id": 3, "name": "基准与分区", "check": "contains", "value": "pivot", "hint": "需要选取基准元素 pivot"},
        ],
    )
    q5 = Question(
        qtype="subjective",
        title="栈与队列的区别",
        description="说明栈和队列的存储结构、操作特性与典型应用场景，各举两个例子。",
        max_score=10,
        knowledge_point_ids=[kp_map["栈和队列"].id],
        test_cases=[],
    )
    assignment2 = Assignment(
        title="数据结构 · 作业二：排序与栈队列",
        description="继续巩固排序算法与线性结构的应用。",
        course_id=courses["数据结构"].id,
        teacher_id=teacher.id,
        due_at=now + timedelta(days=9),
        status="published",
    )
    db.add(assignment2)
    db.flush()
    for q in (q4, q5):
        q.assignment_id = assignment2.id
        db.add(q)

    q6 = Question(
        qtype="subjective",
        title="进程与线程的区别",
        description="从资源分配、调度、地址空间与切换开销四个角度说明进程与线程的区别。",
        max_score=10,
        knowledge_point_ids=[kp_map["进程与线程"].id],
        test_cases=[],
    )
    q7 = Question(
        qtype="programming",
        title="生产者-消费者问题",
        description="使用 threading 实现生产者-消费者模型：缓冲区容量为 5，生产者生产 10 个数据，消费者消费全部数据。",
        language="python",
        code_template="import threading\n\n# TODO\n",
        max_score=12,
        knowledge_point_ids=[kp_map["进程同步与互斥"].id, kp_map["进程与线程"].id],
        test_cases=[
            {"id": 1, "name": "线程与锁", "check": "contains", "value": "threading", "hint": "需要使用 threading 模块"},
            {"id": 2, "name": "同步原语", "check": "contains", "value": "Lock", "hint": "需要使用锁/信号量保证互斥"},
            {"id": 3, "name": "队列缓冲区", "check": "contains", "value": "Queue", "hint": "建议使用 Queue 作为有界缓冲区"},
        ],
    )
    assignment3 = Assignment(
        title="操作系统 · 作业一：进程与同步",
        description="理解进程线程模型，完成生产者-消费者同步实验。",
        course_id=courses["操作系统"].id,
        teacher_id=teacher.id,
        due_at=now + timedelta(days=7),
        status="published",
    )
    db.add(assignment3)
    db.flush()
    for q in (q6, q7):
        q.assignment_id = assignment3.id
        db.add(q)

    q8 = Question(
        qtype="programming",
        title="最长递增子序列（动态规划）",
        description="给定整数数组 nums，返回最长严格递增子序列的长度。定义函数 length_of_lis(nums)。",
        language="python",
        code_template="def length_of_lis(nums):\n    # TODO\n    pass\n",
        max_score=12,
        knowledge_point_ids=[kp_map["动态规划"].id],
        test_cases=[
            {"id": 1, "name": "函数定义", "check": "contains", "value": "def length_of_lis", "hint": "需要定义 length_of_lis"},
            {"id": 2, "name": "动态规划数组", "check": "contains", "value": "dp", "hint": "需要使用 dp 数组记录状态"},
            {"id": 3, "name": "双层循环", "check": "contains", "value": "for", "hint": "需要遍历更新 dp 状态"},
        ],
    )
    assignment4 = Assignment(
        title="算法 · 作业一：动态规划入门",
        description="掌握最优子结构与状态转移思想。",
        course_id=courses["算法设计与分析"].id,
        teacher_id=teacher.id,
        due_at=now + timedelta(days=6),
        status="published",
    )
    db.add(assignment4)
    db.flush()
    q8.assignment_id = assignment4.id
    db.add(q8)
    db.commit()

    # ---------- 学生提交 ----------
    code_samples = {
        "ok_list": (
            "class ListNode:\n    def __init__(self, val=0, next=None):\n"
            "        self.val = val\n        self.next = next\n\n"
            "def reverse_list(head):\n    prev = None\n    cur = head\n"
            "    while cur:\n        nxt = cur.next\n        cur.next = prev\n"
            "        prev = cur\n        cur = nxt\n    return prev\n"
        ),
        "bad_list": (
            "def reverse_list(head):\n    # TODO: 实现反转\n    pass\n"
        ),
        "ok_sort": (
            "def quick_sort(arr):\n    if len(arr) <= 1:\n        return arr\n"
            "    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n"
            "    mid = [x for x in arr if x == pivot]\n"
            "    right = [x for x in arr if x > pivot]\n"
            "    return quick_sort(left) + mid + quick_sort(right)\n"
        ),
        "bad_sort": (
            "def quick_sort(arr):\n    # TODO\n    pass\n"
        ),
        "ok_os": (
            "import threading\nimport queue\nfrom queue import Queue\n\n"
            "def producer(q, lock):\n    for i in range(10):\n"
            "        with lock:\n            q.put(i)\n\n"
            "def consumer(q, lock):\n    while not q.empty():\n"
            "        with lock:\n            q.get()\n"
        ),
        "bad_os": (
            "import threading\n\ndef producer():\n    pass\n\ndef consumer():\n    pass\n"
        ),
        "ok_lis": (
            "def length_of_lis(nums):\n    n = len(nums)\n    dp = [1] * n\n"
            "    for i in range(n):\n        for j in range(i):\n"
            "            if nums[j] < nums[i]:\n                dp[i] = max(dp[i], dp[j] + 1)\n"
            "    return max(dp) if nums else 0\n"
        ),
        "bad_lis": (
            "def length_of_lis(nums):\n    return 0\n"
        ),
    }
    subjective_samples = {
        "good_traverse": (
            "二叉树前序遍历按照“根节点、左子树、右子树”的顺序递归访问。递归出口是节点为空。"
            "前序遍历用于复制树结构，中序遍历用于二叉搜索树输出有序序列，后序遍历用于删除树与后序表达式求值。"
            "三者的区别在于访问根节点的时机：前序先访问根，中序在左子树之后访问根，后序最后访问根。"
        ),
        "good_stack_queue": (
            "栈是后进先出（LIFO）的线性结构，只允许在栈顶插入删除；队列是先进先出（FIFO）的线性结构，队尾入队、队头出队。"
            "典型应用：栈用于括号匹配、表达式求值与函数调用；队列用于任务调度、消息缓冲与广度优先搜索。"
        ),
        "good_process": (
            "进程是资源分配的基本单位，包含独立的地址空间；线程是 CPU 调度的基本单位，同一进程内线程共享地址空间。"
            "进程切换涉及页表与上下文切换，开销较大；线程切换更轻量。"
            "多进程稳定性强但通信开销高，多线程共享数据方便但需要同步互斥。"
        ),
        "good_dp": (
            "动态规划适用于具有最优子结构和重叠子问题的场景。核心是定义状态、写出状态转移方程、确定初始条件与边界。"
            "例如最长递增子序列：dp[i] 表示以 nums[i] 结尾的最长递增子序列长度，"
            "转移方程 dp[i] = max(dp[i], dp[j]+1)（j < i 且 nums[j] < nums[i]）。"
            "与分治相比，动态规划通过记忆化或填表避免重复计算子问题。"
        ),
        "short_answer": "栈是 LIFO。",
    }

    from app.services.judge.factory import get_judge_service

    judge_service = get_judge_service()
    # 种子数据始终使用离线 Mock（与 LLM_PROVIDER 配置解耦，
    # 避免“已配 deepseek 但未填 Key”时平台无法启动）
    grading = GradingService(
        llm=MockLLMService(delay_ms=0), rag=SQLiteRAGService(), prompts=PromptService()
    )

    # student1: 全部完成，代码全过
    s1 = students[0]
    rows = [
        (assignment1, q1, "programming", code_samples["ok_list"]),
        (assignment1, q2, "subjective", subjective_samples["good_traverse"]),
        (assignment2, q4, "programming", code_samples["ok_sort"]),
        (assignment2, q5, "subjective", subjective_samples["good_stack_queue"]),
        (assignment3, q6, "subjective", subjective_samples["good_process"]),
        (assignment3, q7, "programming", code_samples["ok_os"]),
        (assignment4, q8, "programming", code_samples["ok_lis"]),
    ]
    for assignment, q, qtype, content in rows:
        _make_submission(db, grading, judge_service, s1, assignment, q, qtype, content)

    # student2: 编程题有对有错，简答题待批改
    s2 = students[1]
    rows2 = [
        (assignment1, q1, "programming", code_samples["bad_list"]),
        (assignment1, q2, "subjective", subjective_samples["good_traverse"]),
        (assignment2, q4, "programming", code_samples["ok_sort"]),
        (assignment2, q5, "subjective", subjective_samples["short_answer"]),
        (assignment3, q6, "subjective", subjective_samples["good_process"]),
        (assignment4, q8, "programming", code_samples["bad_lis"]),
    ]
    for assignment, q, qtype, content in rows2:
        _make_submission(db, grading, judge_service, s2, assignment, q, qtype, content)

    # student3-6: 部分提交（制造高频错误知识点：动态规划、进程同步、链表）
    rows3 = [
        (assignment1, q1, "programming", code_samples["bad_list"]),
        (assignment1, q2, "subjective", subjective_samples["short_answer"]),
        (assignment3, q7, "programming", code_samples["bad_os"]),
        (assignment4, q8, "programming", code_samples["bad_lis"]),
    ]
    for student in students[2:6]:
        for assignment, q, qtype, content in rows3:
            _make_submission(db, grading, judge_service, student, assignment, q, qtype, content)

    # 教师确认部分成绩（学生端可看到正式成绩）
    confirmed = db.query(Submission).filter(Submission.qtype == "subjective").all()
    for i, sub in enumerate(confirmed[:6]):
        max_score = db.get(Question, sub.question_id).max_score
        base = max_score * 0.9 if i % 2 == 0 else max_score * 0.75
        sub.subjective.teacher_score = round(min(max_score, base), 1)
        sub.subjective.teacher_comment = "作答要点完整，建议补充实例说明。" if i % 2 == 0 else "要点基本覆盖，展开略少。"
        sub.subjective.graded_at = now
        sub.status = "graded"
        db.add(sub)
    db.commit()

    # ---------- 学习画像与推荐 ----------
    from app.services.analytics_service import AnalyticsService

    for student in students:
        subs = db.query(Submission).filter(Submission.student_id == student.id).all()
        for sub in subs:
            q = db.get(Question, sub.question_id)
            if not q:
                continue
            correct = False
            score = 0.0
            if sub.qtype == "programming" and sub.code:
                correct = sub.code.verdict == "accepted"
                score = q.max_score if correct else 0
            elif sub.subjective and sub.subjective.teacher_score is not None:
                score = sub.subjective.teacher_score
                correct = score >= q.max_score * 0.6
            AnalyticsService.update_profile_from_result(
                db, student.id, q, correct=correct, score=score
            )
    LearningPathService.generate(db, students[0].id)
    LearningPathService.generate(db, students[1].id)

    # ---------- 科研数据 ----------
    db.add(ResearchTopic(owner_id=researcher.id, name="检索增强生成（RAG）", description="关注切分策略、检索质量与生成忠实度"))
    db.add(ResearchTopic(owner_id=researcher.id, name="代码大模型与编程教育", description="代码补全、错误诊断与智能批改"))
    db.add(PaperReading(user_id=researcher.id, paper_id=1, status="favorite", progress=100))
    db.add(PaperReading(user_id=researcher.id, paper_id=3, status="reading", progress=40))
    db.add(PaperReading(user_id=researcher.id, paper_id=2, status="read", progress=100))

    # ---------- 备课记录 ----------
    db.add(
        LessonPlan(
            teacher_id=teacher.id,
            course="数据结构",
            chapter="第 4 章 树",
            topic="二叉树遍历",
            grade="大二",
            objectives="1. 理解二叉树遍历的递归思想；2. 掌握三种遍历的实现；3. 能解决遍历相关的应用问题。",
            knowledge_points=["树与二叉树", "栈和队列", "递归"],
            key_points=["递归三要素", "前/中/后序访问时机"],
            difficulties=["非递归遍历的栈模拟", "由遍历序列还原二叉树"],
            flow=[
                {"step": "导入", "content": "用文件夹目录展开演示先序遍历"},
                {"step": "讲授", "content": "递归遍历三行代码的语义"},
                {"step": "演示", "content": "现场编码前序遍历并打印访问序列"},
                {"step": "练习", "content": "手写中序与后序，互换验证"},
            ],
            cases=["案例：表达式树的后序求值"],
            exercises=[{"title": "基础题", "desc": "写出给定二叉树的三种遍历序列"}],
            homework=["作业：实现非递归前序遍历（栈）"],
        )
    )

    # ---------- 活动记录 ----------
    db.add(Activity(user_id=teacher.id, role="teacher", kind="lesson_plan", title="生成教案：数据结构 · 二叉树遍历"))
    db.add(Activity(user_id=teacher.id, role="teacher", kind="grade_confirm", title="确认 6 份简答题成绩"))
    db.add(Activity(user_id=s1.id, role="student", kind="code_submit", title="提交《反转单链表》：3/3 通过"))
    db.add(Activity(user_id=s2.id, role="student", kind="code_submit", title="提交《最长递增子序列》：1/3 通过"))
    db.add(Activity(user_id=researcher.id, role="researcher", kind="paper_analyze", title="AI 阅读论文：Retrieval-Augmented Generation"))
    db.add(Activity(user_id=researcher.id, role="researcher", kind="frontier", title="前沿探索：代码大模型"))
    db.add(ChatMessage(user_id=s1.id, agent_type="learning", role="user", content="如何理解二叉树的前序遍历？"))
    db.add(ChatMessage(user_id=s1.id, agent_type="learning", role="assistant", content="前序遍历先访问根节点，再递归遍历左子树与右子树…", knowledge_points=["树与二叉树"], references=["《数据结构》课程讲义 · 第 4 章"]))
    db.commit()


def _make_submission(
    db: Session,
    grading: GradingService,
    judge_service,
    student: User,
    assignment: Assignment,
    question: Question,
    qtype: str,
    content: str,
) -> None:
    """创建一次提交（编程题评测 / 简答题 AI 建议批改）。"""
    submission = Submission(
        assignment_id=assignment.id,
        question_id=question.id,
        student_id=student.id,
        qtype=qtype,
        status="submitted",
    )
    db.add(submission)
    db.flush()
    if qtype == "programming":
        result = judge_service.judge(content, "python", question.test_cases)
        submission.code = CodeSubmission(
            submission_id=submission.id,
            source_code=content,
            language="python",
            verdict=result.verdict,
            passed_tests=result.passed_tests,
            total_tests=result.total_tests,
            runtime_ms=result.runtime_ms,
            error_message=result.error_message,
            judge_report=[
                {
                    "test_id": r.test_id,
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "expected": r.expected,
                    "actual": r.actual,
                    "time_ms": r.time_ms,
                }
                for r in result.report
            ],
        )
        submission.status = "graded" if result.verdict == "accepted" else "submitted"
        db.add(submission.code)
    else:
        submission.subjective = SubjectiveSubmission(
            submission_id=submission.id,
            content=content,
        )
        db.add(submission.subjective)
    db.commit()
    if qtype == "subjective":
        grading.ai_review(db, submission)


if __name__ == "__main__":
    from app.database import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        if db.query(User).first():
            print("数据库已有数据，跳过（如需重建请删除 backend/data/jbgs.db）")
        else:
            seed_all(db)
            print("演示数据初始化完成 ✓")
    finally:
        db.close()
