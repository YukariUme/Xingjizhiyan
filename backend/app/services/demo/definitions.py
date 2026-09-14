"""Demo 场景定义与预置 AI 响应。

场景步骤与预置结果集中在这里，页面不硬编码；Demo 模式的关键 AI 端点
由后端路由层拦截并返回预置 JSON，保证现场演示不依赖真实 LLM API。
"""

MAIN_STEPS = [
    {"id": "teacher_diagnose", "label": "① 教学诊断", "path": "/teach/diagnostics"},
    {"id": "teacher_plan", "label": "② AI 教学方案", "path": "/teach/design?course=操作系统&chapter=第4章 进程同步&topic=进程同步与信号量"},
    {"id": "student_course", "label": "③ 学生课程", "path": "/learn/courses"},
    {"id": "course_overview", "label": "④ 课程首页", "path": "/learn/courses/:os?tab=overview"},
    {"id": "student_lecture", "label": "⑤ AI 课程讲堂", "path": "/learn/courses/:os?tab=lecture"},
    {"id": "student_preview", "label": "⑥ 课前预习", "path": "/learn/courses/:os?tab=preview"},
    {"id": "knowledge_graph", "label": "⑦ 知识图谱", "path": "/learn/courses/:os?tab=graph"},
    {"id": "student_tutor", "label": "⑧ 课程答疑", "path": "/learn/tutor"},
    {"id": "student_code", "label": "⑨ 代码实验", "path": "/learn/assignments"},
    {"id": "student_profile", "label": "⑩ 个性化学习", "path": "/learn/center"},
    {"id": "student_review", "label": "⑪ 课后复习", "path": "/learn/courses/:os?tab=review"},
    {"id": "student_exam", "label": "⑫ 考前模拟", "path": "/learn/courses/:os?tab=exam"},
    {"id": "teacher_review", "label": "⑬ 教师复诊", "path": "/teach/diagnostics"},
    {"id": "research_hotspots", "label": "⑭ 科研前沿", "path": "/research/frontier"},
    {"id": "research_paper", "label": "⑮ 论文阅读", "path": "/research/papers"},
    {"id": "workflow_view", "label": "⑯ 工作流可视化", "path": "/workflows"},
]

TEACHING_STEPS = [
    {"id": "teacher_plan", "label": "① AI 备课", "path": "/teach/design"},
    {"id": "teacher_assignment", "label": "② 发布作业", "path": "/teach/assignments"},
    {"id": "teacher_analytics", "label": "③ 学情分析", "path": "/teach/diagnostics"},
    {"id": "teacher_adjust", "label": "④ 教学调整", "path": "/teach/design"},
]

LEARNING_STEPS = [
    {"id": "preview", "label": "① 课前预习", "path": "/learn/courses/:os?tab=preview"},
    {"id": "lecture", "label": "② AI 课程讲堂", "path": "/learn/courses/:os?tab=lecture"},
    {"id": "graph", "label": "③ 知识图谱", "path": "/learn/courses/:os?tab=graph"},
    {"id": "homework", "label": "④ 作业", "path": "/learn/assignments"},
    {"id": "judge", "label": "⑤ 自动评测", "path": "/learn/assignments"},
    {"id": "diagnose", "label": "⑥ 错误诊断", "path": "/learn/assignments"},
    {"id": "review", "label": "⑦ 课后复习", "path": "/learn/courses/:os?tab=review"},
    {"id": "exam", "label": "⑧ 考前模拟", "path": "/learn/courses/:os?tab=exam"},
]

DATA_STRUCTURE_STEPS = [
    {"id": "ds_stack", "label": "① 栈 Stack", "path": "/learn/animation?ds=stack"},
    {"id": "ds_queue", "label": "② 队列 Queue", "path": "/learn/animation?ds=queue"},
    {"id": "ds_list", "label": "③ 链表 Linked List", "path": "/learn/animation?ds=list"},
    {"id": "ds_bst", "label": "④ 二叉搜索树 BST", "path": "/learn/animation?ds=bst"},
]

ROUNDTABLE_STEPS = [
    {"id": "roundtable_discuss", "label": "① AI 圆桌讨论", "path": "/learn/roundtable"},
]

SCENARIOS = [
    {
        "id": "teaching_learning_research",
        "name": "教学—学习—科研一体化",
        "course": "操作系统",
        "initial_role": "teacher",
        "description": "约 3 分钟展示完整平台能力：教师诊断 → AI 教学方案 → 学生课程学习 → 代码实验 → 个性化学习 → 科研探索",
        "steps": MAIN_STEPS,
    },
    {
        "id": "teaching_loop",
        "name": "教学闭环",
        "course": "操作系统",
        "initial_role": "teacher",
        "description": "教师 AI 备课 → 发布作业 → 学情分析 → 教学调整",
        "steps": TEACHING_STEPS,
    },
    {
        "id": "learning_loop",
        "name": "学习闭环",
        "course": "操作系统",
        "initial_role": "student",
        "description": "预习 → AI 课程讲堂 → 作业 → 代码评测 → 错误诊断 → 复习 → 考前模拟",
        "steps": LEARNING_STEPS,
    },
    {
        "id": "data_structure",
        "name": "数据结构动画演示",
        "course": "数据结构",
        "initial_role": "student",
        "description": "约 1 分钟：栈 → 队列 → 链表 → 二叉搜索树，逐步动画演示经典数据结构",
        "steps": DATA_STRUCTURE_STEPS,
    },
    {
        "id": "roundtable",
        "name": "AI 圆桌讨论",
        "course": "数据结构",
        "initial_role": "student",
        "description": "多个 AI 角色就一个计算机学科问题，从不同角度辩论 + 白板呈现观点",
        "steps": ROUNDTABLE_STEPS,
    },
]

def preset_teaching(primary_title: str = "", quick: bool = False, hint: bool = False) -> dict:
    """AI 助教（教学模式）预置回答：围绕主资料讲解；提示/快速/深度三种风格。"""
    title = primary_title or ""
    if hint:
        return {
            "answer": (
                f"好，我们围绕主资料《{title or '所选资料'}》来学习。先不急着给答案，请你先思考四个问题：\n\n"
                "1. 这个知识点解决什么问题？没有它会发生什么？\n"
                "2. 它的核心概念/机制是什么？和之前学的知识有什么关系？\n"
                "3. 能不能举一个生活中的例子对应它？\n"
                "4. 它最容易出错的地方可能在哪？\n\n"
                "想好后告诉我你的理解，或直接说“深度讲解”，我会从零开始完整讲一遍。"
            ),
            "knowledge_points": [],
            "references": [title] if title else [],
            "mode": "hint",
            "grounded": True,
            "confidence": 0.85,
            "provider": "demo",
        }
    if any(k in title for k in ("同步", "信号量", "生产者", "消费者", "死锁")):
        kps = ["信号量", "同步", "互斥", "生产者—消费者"]
        if quick:
            answer = (
                "【快速回答 · 进程同步与信号量】\n"
                "1. 临界区：访问共享资源的代码段，需满足互斥、前进、有限等待；\n"
                "2. 信号量 S 支持 P(S)（wait，减 1，小于 0 阻塞）与 V(S)（signal，加 1，唤醒等待者），且必须原子执行；\n"
                "3. 生产者—消费者用三个信号量：empty（空位）、full（已有数据）、mutex（互斥）；\n"
                "4. 易错：P/V 顺序颠倒会死锁，漏 V 会永久阻塞。\n"
                "（依据主资料《进程同步：信号量与经典问题》）"
            )
        else:
            answer = (
                "从零讲解《进程同步与信号量》\n\n"
                "一、为什么需要同步？\n多个进程/线程并发访问共享变量时，执行顺序不确定会产生竞态条件。"
                "比如两个消费者同时取走同一个数据。同步的目标是让并发访问变得确定。\n\n"
                "二、临界区\n访问共享资源的代码段称为临界区，必须满足三个原则：互斥（同一时刻最多一个进入）、"
                "前进（没人占用时允许申请者进入）、有限等待（等待时间有上限）。\n\n"
                "三、信号量与 P/V 操作\n信号量是一个整型变量 + 等待队列。P(S)：S 减 1，若小于 0 则阻塞；"
                "V(S)：S 加 1，若有等待者则唤醒。P/V 必须原子执行。\n\n"
                "四、生产者—消费者问题\n缓冲区容量 N：empty=N、full=0、mutex=1。"
                "生产者先 P(empty) 再 P(mutex)，消费者先 P(full) 再 P(mutex)，顺序不能颠倒，否则可能死锁。\n\n"
                "五、易错点\n① 顺序颠倒导致死锁；② 忘记 V 导致永久阻塞；③ 用忙等替代信号量浪费 CPU。"
            )
        references = [title or "进程同步：信号量与经典问题"]
    elif any(k in title for k in ("进程", "线程", "调度")):
        kps = ["进程", "线程", "调度", "PCB"]
        if quick:
            answer = (
                "【快速回答 · 进程、线程与调度】\n"
                "1. 进程是资源分配的基本单位，线程是 CPU 调度的基本单位；\n"
                "2. 每个进程有独立地址空间（代码/数据/堆/栈），线程共享进程资源，但各有栈与寄存器；\n"
                "3. 调度策略：先来先服务、短作业优先、时间片轮转、优先级、多级反馈队列；\n"
                "4. 要点：进程切换代价高、线程切换代价低；多核并行优先用多线程。\n"
                "（依据主资料《进程、线程与调度》）"
            )
        else:
            answer = (
                "从零讲解《进程、线程与调度》\n\n"
                "一、为什么需要进程？\n程序是静态的代码，进程是程序的一次运行实例。操作系统用进程来隔离程序之间的资源，"
                "防止一个程序崩溃影响整个系统。\n\n"
                "二、进程是什么？\n进程 = 程序 + 运行状态。内核用进程控制块（PCB）记录它的状态、寄存器、内存、打开的文件等。"
                "进程状态：创建、就绪、运行、阻塞、终止。\n\n"
                "三、线程：更轻量的执行单元\n同一进程的多个线程共享代码段、数据段和堆，但各自有独立的栈和寄存器，"
                "所以创建和切换线程比进程快得多。多线程适合 I/O 密集与多核并行任务。\n\n"
                "四、CPU 调度：让就绪队列里的进程/线程轮流用 CPU\n"
                "常见算法：先来先服务（FCFS，公平但可能长任务阻塞）；短作业优先（SJF，平均等待短但可能饿死长任务）；"
                "时间片轮转（RR，响应快，适合分时系统）；多级反馈队列（MLFQ，综合最优）。\n\n"
                "五、一个例子\n浏览器是进程；它的标签页可以是线程，共享渲染引擎；下载线程阻塞不会卡住整个界面。\n\n"
                "六、易错点\n① 线程同步缺失会导致竞态；② 进程与线程的资源粒度混淆；③ 调度算法的适用场景记混。"
            )
        references = [title or "进程、线程与调度讲义"]
    elif "内存" in title:
        kps = ["内存管理", "分页", "虚拟内存"]
        answer = (
            "从零讲解《内存管理》\n\n一、为什么需要内存管理？\n多个程序同时运行，需要隔离各自的地址空间，"
            "否则一个程序能读改另一个程序的数据。\n\n二、基本方案\n连续分配简单但碎片多；分页把内存切成固定大小的页，"
            "进程按页装载，消除外部碎片；分段按逻辑单位（代码/数据/栈）划分，便于共享与保护。\n\n"
            "三、虚拟内存\n只把用到的页装入物理内存，其余在磁盘，配合页面置换算法（LRU、时钟算法）运行比物理内存更大的程序。\n\n"
            "四、易错点\n① 页表开销与 TLB 命中率；② 内部碎片 vs 外部碎片；③ 页面置换算法适用场景。"
        )
        references = [title]
    else:
        kps = ["知识讲解"]
        answer = (
            f"我将围绕主资料《{title or '所选资料'}》从零讲解。\n\n"
            "一、它解决什么问题；二、核心概念；三、典型例子；四、易错点。\n"
            "（当前为演示预置回答：建议在课程资料中上传对应的教材/PPT 后重试，即可获得该资料的完整讲解。）"
        )
        references = [title] if title else []
    return {
        "answer": answer,
        "knowledge_points": kps,
        "references": references,
        "mode": "teaching",
        "grounded": True,
        "confidence": 0.85,
        "provider": "demo",
    }


def get_scenario_def(scenario_id: str) -> dict | None:
    return next((s for s in SCENARIOS if s["id"] == scenario_id), None)


# ---------- 预置 AI 响应（Demo 路由层使用） ----------

DEMO_REFERENCES = [
    {
        "title": "进程同步：信号量与经典问题",
        "source": "《现代操作系统》第 2 章整理",
        "course": "操作系统",
        "chapter": "第 4 章 进程同步",
        "topic": "同步互斥",
        "source_level": "S",
        "page": "第 35-42 页",
        "snippet": "临界区是访问共享资源的代码段，需满足互斥、前进、有限等待三个原则。信号量 S 支持 P（wait）与 V（signal）操作…",
        "score": 0.79,
    },
    {
        "title": "操作系统课程讲义：第 4 章",
        "source": "教师课程 PPT",
        "course": "操作系统",
        "chapter": "第 4 章 进程同步",
        "topic": "生产者-消费者",
        "source_level": "S",
        "page": "第 42 页",
        "snippet": "生产者-消费者问题：empty 信号量表示缓冲区空位，full 表示已用空间，mutex 保护缓冲区互斥访问…",
        "score": 0.72,
    },
]


def preset_diagnosis() -> dict:
    return {
        "diagnosis": {
            "findings": [
                {
                    "issue": "多数学生能够记忆互斥和同步的定义，但在 P/V 操作顺序和生产者—消费者问题中的应用存在困难",
                    "evidence": "班级 78% 学生在进程同步相关任务表现较差，进程同步正确率 42%",
                    "reason": "概念记忆与应用脱节，缺少代码层面的同步练习与可视化演示",
                }
            ],
            "suggestions": [
                {"title": "增加互斥与同步的对比讲解", "detail": "下一节课用 10 分钟对比互斥/同步/死锁三个概念。"},
                {"title": "使用生产者—消费者案例", "detail": "用一个完整代码案例串讲 empty/full/mutex 三个信号量的作用。"},
                {"title": "增加一次代码实验", "detail": "布置“用信号量实现生产者—消费者”编程作业并接入自动评测。"},
                {"title": "对重点学生安排专项练习", "detail": "为进程同步掌握度低于 50% 的学生推荐针对性复习内容。"},
            ],
            "next_lesson": ["互斥与同步的区别", "信号量 P/V 操作", "生产者-消费者问题"],
            "materials": ["《操作系统》教师 PPT 第 4 章", "《操作系统概念》第 7 章", "生产者-消费者代码实验"],
            "ai_generated": True,
            "ai_label": "AI 生成",
            "provider": "demo",
            "references": DEMO_REFERENCES,
        },
        "ai_generated": True,
        "provider": "demo",
    }


def preset_lecture() -> dict:
    return {
        "learning_goals": [
            "理解临界区、互斥与同步的基本概念",
            "掌握信号量 P/V 操作及其在生产者—消费者问题中的应用",
            "能够分析并修复常见的同步错误",
        ],
        "sections": [
            {
                "title": "为什么需要进程同步",
                "content": "多个进程/线程并发访问共享资源时，若不加控制会出现竞态条件（如两个消费者同时取走同一个数据）。进程同步的目标是保证共享资源访问的互斥与执行顺序的确定性。",
                "example": "银行取款与余额更新的并发场景",
            },
            {
                "title": "临界区",
                "content": "访问共享资源的代码段称为临界区。临界区必须满足三个原则：互斥（同一时刻最多一个进程进入）、前进（无进程在临界区时允许申请者进入）、有限等待（进程等待进入的时间有上限）。",
            },
            {
                "title": "互斥与同步",
                "content": "互斥保证共享资源同一时刻只被一个进程使用；同步保证并发进程按约定顺序执行（如生产者先生产、消费者后消费）。两者常结合使用。",
            },
            {
                "title": "信号量与 P/V 操作",
                "content": "信号量 S 是一个整型变量，支持两个原子操作：P(S)（wait，S 减 1，小于 0 则阻塞）与 V(S)（signal，S 加 1，唤醒等待者）。P/V 操作必须原子执行。",
                "code": "mutex = Semaphore(1)\n\ndef critical_section():\n    P(mutex)      # 进入临界区\n    ...           # 访问共享资源\n    V(mutex)      # 离开临界区",
            },
            {
                "title": "生产者—消费者问题",
                "content": "用三个信号量解决：empty（缓冲区空位数，初值为 N）、full（已用空间，初值为 0）、mutex（保护缓冲区，初值为 1）。生产者先 P(empty) 再 P(mutex)，消费者先 P(full) 再 P(mutex)，顺序不能颠倒，否则可能死锁。",
                "code": "empty, full, mutex = Semaphore(N), Semaphore(0), Semaphore(1)\n\ndef producer():\n    while True:\n        item = produce()\n        P(empty); P(mutex)\n        buffer.append(item)\n        V(mutex); V(full)\n\ndef consumer():\n    while True:\n        P(full); P(mutex)\n        item = buffer.pop(0)\n        V(mutex); V(empty)\n        consume(item)",
            },
            {
                "title": "常见错误",
                "content": "① P/V 操作顺序颠倒导致死锁；② 忘记 V 操作导致进程永久阻塞；③ 用 busy-wait 替代信号量造成忙等浪费 CPU。",
            },
        ],
        "common_errors": ["P/V 操作顺序颠倒", "生产者先 P(mutex) 再 P(empty) 造成死锁", "临界区缺少 V 操作释放"],
        "exercises": [
            {"question": "为什么生产者和消费者都需要使用信号量？", "answer_hint": "生产者需要 empty 防止缓冲区满，消费者需要 full 防止缓冲区空。",
             "knowledge_points": ["信号量", "同步"]},
            {"question": "如果把消费者中的 P(full) 和 P(mutex) 交换顺序会发生什么？", "answer_hint": "缓冲区空时消费者持锁等待 full，生产者无法进入临界区，形成死锁。"},
        ],
        "check": ["能否用自己的话解释互斥与同步的区别？", "能否画出生产者—消费者三信号量的执行流程？"],
        "ai_generated": True,
        "ai_label": "AI 生成",
        "provider": "demo",
        "references": DEMO_REFERENCES,
    }


def preset_tutor() -> dict:
    return {
        "answer": "生产者和消费者都需要使用信号量，是因为它们共享一个容量有限的缓冲区：\n\n"
        "1. 生产者需要用 empty 信号量（初值为缓冲区大小）判断缓冲区是否有空位，空位不足时阻塞等待；\n"
        "2. 消费者需要用 full 信号量（初值为 0）判断缓冲区是否有数据，没有数据时阻塞等待；\n"
        "3. 双方都需要用 mutex 保护对缓冲区的互斥访问，避免并发读写导致数据错乱。\n\n"
        "所以三个信号量各司其职：empty 管“能不能放”，full 管“能不能取”，mutex 管“同一时刻只能一个人动缓冲区”。\n"
        "回答主要依据课程官方资料。",
        "knowledge_points": ["信号量", "同步", "生产者—消费者"],
        "references": [
            f"[{DEMO_REFERENCES[0]['source_level']}] {DEMO_REFERENCES[0]['title']} · {DEMO_REFERENCES[0]['source']} · 第 {DEMO_REFERENCES[0]['page']} 页",
            f"[{DEMO_REFERENCES[1]['source_level']}] {DEMO_REFERENCES[1]['title']} · {DEMO_REFERENCES[1]['source']} · 第 {DEMO_REFERENCES[1]['page']} 页",
        ],
        "mode": "hint",
        "grounded": True,
        "confidence": 0.79,
        "provider": "demo",
    }


def preset_code_diagnosis() -> dict:
    return {
        "error_reason": "问题可能出现在消费者获取 empty 信号量之前的执行顺序——部分测试中消费者可能在缓冲区为空时继续执行。",
        "knowledge_points": ["信号量", "同步", "生产者—消费者"],
        "thinking": [
            "检查消费者是否在 P(full) 之前访问了缓冲区",
            "检查 P/V 操作是否成对出现、顺序是否与资源语义一致",
            "确认 empty/full/mutex 三个信号量的初值与使用位置",
        ],
        "advice": [
            "建议先回顾 P/V 操作及 empty/full/mutex 三个信号量的作用",
            "先画执行流程图再对照代码，重点检查阻塞分支",
        ],
        "suggestion": "先复习信号量与生产者—消费者问题，再重写消费者中 P/V 的顺序。",
        "line_anchors": [
            {"line": 8, "note": "消费者先 P(mutex) 再 P(full)，缓冲区为空时会持锁等待，导致死锁。"},
            {"line": 10, "note": "访问 buffer 前应先确认已通过 full 信号量取得数据。"},
        ],
        "mode": "hint",
        "provider": "demo",
    }


def preset_paper_analysis(title: str = "", authors: str = "") -> dict:
    return {
        "paper_id": 0,
        "title": title or "Operating Systems: Three Easy Pieces（进程同步章节）",
        "summary": "论文系统阐述了进程同步的基本机制：从竞态条件的产生，到锁/信号量的设计与正确性论证，"
        "并以生产者—消费者、读者-写者等经典问题展示同步原语的使用，最后讨论了死锁的预防与避免。",
        "research_question": "如何设计正确且高效的进程同步原语，并避免死锁？",
        "method": "形式化定义 + 经典问题建模：用信号量与管程描述同步约束，通过不变式论证正确性。",
        "experiments": [
            {"组别": "信号量实现", "人数": 30, "干预方式": "P/V 操作", "测量指标": "正确率/吞吐", "主要结果": "正确率 88%"},
            {"组别": "管程实现", "人数": 30, "干预方式": "条件变量", "测量指标": "正确率/吞吐", "主要结果": "正确率 93%"},
        ],
        "conclusion": "同步原语的选择影响正确性与可维护性；管程比裸信号量更不易出错，但信号量更灵活。",
        "limitations": "并发场景规模有限，未覆盖分布式系统下的同步问题。",
        "future": "可进一步研究无锁数据结构与跨进程同步机制。",
        "knowledge_points": ["信号量", "互斥", "并发控制"],
        "references": DEMO_REFERENCES,
        "provider": "demo",
        "ai_generated": True,
    }
