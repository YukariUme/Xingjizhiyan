"""按国内主流教材整理的课程章节与主要知识点（7 门课 × 6~9 章）。"""

# 章节结构：official_ref 使用“第 N 章”格式，便于与知识点自动匹配
FULL_CHAPTERS: dict[str, list[dict]] = {
    "数据结构": [
        {"key": "ch1", "title": "绪论", "official_ref": "第 1 章", "summary": "数据结构的基本概念、逻辑/存储结构、抽象数据类型与算法分析。"},
        {"key": "ch2", "title": "线性表", "official_ref": "第 2 章", "summary": "顺序表与链表的存储结构、基本操作与复杂度对比。"},
        {"key": "ch3", "title": "栈和队列", "official_ref": "第 3 章", "summary": "栈与队列的特性、实现与典型应用。"},
        {"key": "ch4", "title": "串、数组和广义表", "official_ref": "第 4 章", "summary": "串的模式匹配（KMP）、数组的存储与广义表。"},
        {"key": "ch5", "title": "树和二叉树", "official_ref": "第 5 章", "summary": "二叉树性质与遍历、线索化、Huffman 树与并查集。"},
        {"key": "ch6", "title": "图", "official_ref": "第 6 章", "summary": "图的存储与遍历、最小生成树、最短路径与拓扑排序。"},
        {"key": "ch7", "title": "查找", "official_ref": "第 7 章", "summary": "顺序/折半查找、二叉排序树、平衡二叉树与哈希表。"},
        {"key": "ch8", "title": "排序", "official_ref": "第 8 章", "summary": "插入/交换/选择/归并/基数排序与外部排序。"},
    ],
    "算法设计与分析": [
        {"key": "ch1", "title": "算法概述与复杂度", "official_ref": "第 1 章", "summary": "大 O 记号、递推与主定理、最好/最坏/平均复杂度。"},
        {"key": "ch2", "title": "递归与分治", "official_ref": "第 2 章", "summary": "分治范式：归并排序、快速排序、二分查找与最近点对。"},
        {"key": "ch3", "title": "动态规划", "official_ref": "第 3 章", "summary": "最优子结构与状态转移：背包、LCS、矩阵链乘与编辑距离。"},
        {"key": "ch4", "title": "贪心算法", "official_ref": "第 4 章", "summary": "贪心选择性质：活动安排、Huffman 编码、最小生成树。"},
        {"key": "ch5", "title": "回溯法", "official_ref": "第 5 章", "summary": "状态空间树与剪枝：N 皇后、图着色、子集与排列。"},
        {"key": "ch6", "title": "分支限界法", "official_ref": "第 6 章", "summary": "广度优先搜索限界：0/1 背包、旅行商问题的分支限界求解。"},
        {"key": "ch7", "title": "概率算法与近似算法", "official_ref": "第 7 章", "summary": "随机化算法与 NP 难问题的近似求解策略。"},
    ],
    "操作系统": [
        {"key": "ch1", "title": "操作系统引论", "official_ref": "第 1 章", "summary": "操作系统的目标、发展、特征与运行环境。"},
        {"key": "ch2", "title": "进程与线程", "official_ref": "第 2 章", "summary": "进程/线程模型、状态转换、同步互斥与经典同步问题。"},
        {"key": "ch3", "title": "处理机调度与死锁", "official_ref": "第 3 章", "summary": "调度算法、死锁的四个必要条件与银行家算法。"},
        {"key": "ch4", "title": "内存管理", "official_ref": "第 4 章", "summary": "连续/分页/分段/段页式、虚拟内存与页面置换。"},
        {"key": "ch5", "title": "文件管理", "official_ref": "第 5 章", "summary": "文件逻辑/物理结构、目录、空闲空间管理与磁盘调度。"},
        {"key": "ch6", "title": "输入输出与设备管理", "official_ref": "第 6 章", "summary": "I/O 控制方式、中断、DMA、缓冲与设备分配。"},
    ],
    "计算机网络": [
        {"key": "ch1", "title": "概述", "official_ref": "第 1 章", "summary": "分层模型、协议、服务与性能指标。"},
        {"key": "ch2", "title": "物理层与数据链路层", "official_ref": "第 2 章", "summary": "编码与传输介质、差错控制、以太网与交换机。"},
        {"key": "ch3", "title": "网络层", "official_ref": "第 3 章", "summary": "IP 编址、子网划分、ARP、路由协议与路由器。"},
        {"key": "ch4", "title": "传输层", "official_ref": "第 4 章", "summary": "UDP/TCP、可靠传输、流量与拥塞控制。"},
        {"key": "ch5", "title": "应用层", "official_ref": "第 5 章", "summary": "DNS、HTTP、FTP、电子邮件与网络应用模型。"},
        {"key": "ch6", "title": "网络安全", "official_ref": "第 6 章", "summary": "对称/公钥密码、数字签名、HTTPS 与防火墙。"},
    ],
    "数据库系统": [
        {"key": "ch1", "title": "绪论", "official_ref": "第 1 章", "summary": "数据库系统组成、数据模型与三级模式结构。"},
        {"key": "ch2", "title": "关系数据库", "official_ref": "第 2 章", "summary": "关系模型、完整性约束与关系代数。"},
        {"key": "ch3", "title": "关系数据库标准语言 SQL", "official_ref": "第 3 章", "summary": "DDL/DML/DQL、连接查询、视图与嵌入式 SQL。"},
        {"key": "ch4", "title": "数据库安全性与完整性", "official_ref": "第 4 章", "summary": "用户授权、完整性约束与触发器。"},
        {"key": "ch5", "title": "关系数据理论", "official_ref": "第 5 章", "summary": "函数依赖、候选键求解与范式分解（1NF~BCNF）。"},
        {"key": "ch6", "title": "数据库设计", "official_ref": "第 6 章", "summary": "需求分析、概念设计（E-R）、逻辑设计与物理设计。"},
        {"key": "ch7", "title": "事务与并发控制", "official_ref": "第 7 章", "summary": "ACID、调度、封锁协议、隔离级别与 MVCC。"},
        {"key": "ch8", "title": "索引与查询优化", "official_ref": "第 8 章", "summary": "B+ 树/哈希索引、执行计划与查询优化策略。"},
    ],
    "人工智能": [
        {"key": "ch1", "title": "绪论与智能体", "official_ref": "第 1 章", "summary": "人工智能定义、发展史、智能体与问题求解。"},
        {"key": "ch2", "title": "机器学习基础", "official_ref": "第 2 章", "summary": "监督/无监督/强化学习、模型评估与正则化。"},
        {"key": "ch3", "title": "深度学习", "official_ref": "第 3 章", "summary": "神经网络、反向传播、CNN/RNN 与训练技巧。"},
        {"key": "ch4", "title": "大语言模型与提示工程", "official_ref": "第 4 章", "summary": "Transformer、预训练、指令微调与思维链提示。"},
        {"key": "ch5", "title": "检索增强生成与知识工程", "official_ref": "第 5 章", "summary": "RAG 全流程、向量检索、知识图谱与可溯源问答。"},
        {"key": "ch6", "title": "强化学习", "official_ref": "第 6 章", "summary": "MDP、动态规划、Q-learning、策略梯度与 RLHF。"},
        {"key": "ch7", "title": "人工智能安全与伦理", "official_ref": "第 7 章", "summary": "公平性、可解释性、幻觉治理与负责任 AI。"},
    ],
    "计算机组成原理": [
        {"key": "ch1", "title": "计算机系统概论", "official_ref": "第 1 章", "summary": "冯·诺依曼结构、层次结构、性能指标（CPI、MIPS）。"},
        {"key": "ch2", "title": "数据的表示与运算", "official_ref": "第 2 章", "summary": "数制转换、原码/补码/移码、定点与浮点运算。"},
        {"key": "ch3", "title": "存储系统", "official_ref": "第 3 章", "summary": "存储层次、半导体存储器、Cache 与主存扩展。"},
        {"key": "ch4", "title": "指令系统", "official_ref": "第 4 章", "summary": "指令格式、寻址方式、CISC 与 RISC。"},
        {"key": "ch5", "title": "中央处理器", "official_ref": "第 5 章", "summary": "数据通路、硬布线/微程序控制、流水线技术。"},
        {"key": "ch6", "title": "总线与输入输出系统", "official_ref": "第 6 章", "summary": "总线仲裁、中断、DMA 与 I/O 接口。"},
    ],
}

# 新增主要知识点（覆盖各课程章节；name/subject/chapter 与 FULL_CHAPTERS 对齐）
EXTRA_KNOWLEDGE_POINTS = [
    # 数据结构
    {"name": "串与模式匹配", "subject": "数据结构", "chapter": "第 4 章", "difficulty": "中",
     "description": "串的基本操作、朴素匹配与 KMP 算法（next 数组构造）。", "prerequisites": ["线性表"]},
    {"name": "数组与广义表", "subject": "数据结构", "chapter": "第 4 章", "difficulty": "中",
     "description": "多维数组的行/列优先存储、特殊矩阵压缩与广义表。", "prerequisites": ["线性表"]},
    # 算法
    {"name": "分支限界法", "subject": "算法设计与分析", "chapter": "第 6 章", "difficulty": "难",
     "description": "广度优先搜索 + 限界剪枝：0/1 背包与旅行商问题的分支限界。", "prerequisites": ["回溯与搜索"]},
    {"name": "近似算法", "subject": "算法设计与分析", "chapter": "第 7 章", "difficulty": "难",
     "description": "NP 难问题的近似比分析与常见近似策略（贪心/松弛）。", "prerequisites": ["贪心算法"]},
    # 操作系统
    {"name": "死锁", "subject": "操作系统", "chapter": "第 3 章", "difficulty": "难",
     "description": "死锁必要条件、银行家算法、死锁检测与解除。", "prerequisites": ["进程同步与互斥"]},
    {"name": "设备管理", "subject": "操作系统", "chapter": "第 6 章", "difficulty": "中",
     "description": "I/O 控制方式、中断与 DMA、缓冲管理与设备分配。", "prerequisites": ["内存管理"]},
    # 计算机网络
    {"name": "数据链路层与以太网", "subject": "计算机网络", "chapter": "第 2 章", "difficulty": "中",
     "description": "帧封装、差错控制（CRC）、CSMA/CD 与交换机自学习。", "prerequisites": ["网络分层模型"]},
    {"name": "网络安全基础", "subject": "计算机网络", "chapter": "第 6 章", "difficulty": "中",
     "description": "对称/公钥密码、数字签名、HTTPS 与防火墙。", "prerequisites": ["HTTP 协议"]},
    # 数据库
    {"name": "数据库安全与完整性", "subject": "数据库系统", "chapter": "第 4 章", "difficulty": "中",
     "description": "用户授权与视图、完整性约束与触发器。", "prerequisites": ["SQL 查询"]},
    {"name": "数据库设计", "subject": "数据库系统", "chapter": "第 6 章", "difficulty": "中",
     "description": "E-R 模型、概念/逻辑/物理设计流程与规范化。", "prerequisites": ["关系模型"]},
    # 人工智能
    {"name": "智能体与搜索", "subject": "人工智能", "chapter": "第 1 章", "difficulty": "易",
     "description": "智能体结构、搜索策略（BFS/DFS/A*）与博弈树。", "prerequisites": []},
    {"name": "AI 安全与伦理", "subject": "人工智能", "chapter": "第 7 章", "difficulty": "中",
     "description": "公平性、可解释性、幻觉治理与负责任 AI 原则。", "prerequisites": ["大语言模型"]},
    # 计算机组成原理
    {"name": "计算机系统概述", "subject": "计算机组成原理", "chapter": "第 1 章", "difficulty": "易",
     "description": "冯·诺依曼结构、硬件组成与性能指标（CPI、主频）。", "prerequisites": []},
    {"name": "数据的表示与运算", "subject": "计算机组成原理", "chapter": "第 2 章", "difficulty": "中",
     "description": "原码/补码/移码、定点与 IEEE 754 浮点运算。", "prerequisites": ["计算机系统概述"]},
    {"name": "存储系统", "subject": "计算机组成原理", "chapter": "第 3 章", "difficulty": "中",
     "description": "存储层次、SRAM/DRAM、Cache 映射与替换策略。", "prerequisites": ["计算机系统概述"]},
    {"name": "指令系统", "subject": "计算机组成原理", "chapter": "第 4 章", "difficulty": "中",
     "description": "指令格式与寻址方式、CISC 与 RISC 设计思想。", "prerequisites": ["数据的表示与运算"]},
    {"name": "中央处理器", "subject": "计算机组成原理", "chapter": "第 5 章", "difficulty": "难",
     "description": "数据通路、控制器设计（硬布线/微程序）与流水线。", "prerequisites": ["指令系统"]},
    {"name": "总线与输入输出系统", "subject": "计算机组成原理", "chapter": "第 6 章", "difficulty": "中",
     "description": "总线分类与仲裁、中断系统、DMA 与接口。", "prerequisites": ["中央处理器"]},
]

