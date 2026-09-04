"""计算机学科知识库 Mock 数据。"""

KNOWLEDGE_POINTS = [
    # 数据结构
    {"name": "线性表", "subject": "数据结构", "chapter": "第 2 章 线性表", "difficulty": "易",
     "description": "顺序表与链表的存储结构、基本操作与复杂度对比，是数据组织的基础。",
     "prerequisites": ["C/Python 基础语法", "指针与引用"]},
    {"name": "栈和队列", "subject": "数据结构", "chapter": "第 3 章 栈与队列", "difficulty": "易",
     "description": "受限线性结构：栈的 LIFO、队列的 FIFO 特性及典型应用（表达式求值、括号匹配、循环队列）。",
     "prerequisites": ["线性表"]},
    {"name": "树与二叉树", "subject": "数据结构", "chapter": "第 4 章 树", "difficulty": "中",
     "description": "二叉树的性质、遍历（先/中/后序、层次）、线索化与 Huffman 树。",
     "prerequisites": ["栈和队列", "递归"]},
    {"name": "图", "subject": "数据结构", "chapter": "第 5 章 图", "difficulty": "难",
     "description": "图的存储（邻接矩阵/邻接表）、深度优先与广度优先遍历、最小生成树与最短路径。",
     "prerequisites": ["树与二叉树", "队列"]},
    {"name": "排序算法", "subject": "数据结构", "chapter": "第 6 章 排序", "difficulty": "中",
     "description": "插入、选择、冒泡、快排、归并、堆排序的原理、复杂度与稳定性。",
     "prerequisites": ["线性表", "树与二叉树"]},
    {"name": "查找与哈希", "subject": "数据结构", "chapter": "第 7 章 查找", "difficulty": "中",
     "description": "顺序/二分查找、二叉排序树、平衡二叉树与哈希表冲突处理。",
     "prerequisites": ["树与二叉树"]},
    # 算法
    {"name": "算法复杂度分析", "subject": "算法设计与分析", "chapter": "第 1 章 绪论", "difficulty": "易",
     "description": "大 O 记号、最好/最坏/平均复杂度，算法分析的基本方法。",
     "prerequisites": ["排序算法"]},
    {"name": "分治策略", "subject": "算法设计与分析", "chapter": "第 2 章 分治", "difficulty": "中",
     "description": "分解、求解、合并的三步范式，典型应用：归并排序、快速排序、最近点对。",
     "prerequisites": ["算法复杂度分析", "递归"]},
    {"name": "动态规划", "subject": "算法设计与分析", "chapter": "第 3 章 动态规划", "difficulty": "难",
     "description": "最优子结构、重叠子问题与状态转移方程；典型问题：背包、最长公共子序列、编辑距离。",
     "prerequisites": ["分治策略"]},
    {"name": "贪心算法", "subject": "算法设计与分析", "chapter": "第 4 章 贪心", "difficulty": "中",
     "description": "贪心选择性质与最优子结构；典型问题：活动安排、Huffman 编码、最小生成树。",
     "prerequisites": ["算法复杂度分析"]},
    {"name": "回溯与搜索", "subject": "算法设计与分析", "chapter": "第 5 章 回溯", "difficulty": "难",
     "description": "状态空间树、剪枝策略；典型问题：N 皇后、图着色、子集枚举。",
     "prerequisites": ["递归", "树与二叉树"]},
    # 操作系统
    {"name": "进程与线程", "subject": "操作系统", "chapter": "第 2 章 进程管理", "difficulty": "中",
     "description": "进程状态转换、PCB、线程模型，以及进程与线程的异同。",
     "prerequisites": ["计算机组成原理"]},
    {"name": "进程同步与互斥", "subject": "操作系统", "chapter": "第 2 章 进程管理", "difficulty": "难",
     "description": "临界区、信号量、PV 操作与经典同步问题（生产者-消费者、读者-写者）。",
     "prerequisites": ["进程与线程"]},
    {"name": "内存管理", "subject": "操作系统", "chapter": "第 3 章 内存管理", "difficulty": "中",
     "description": "分页、分段、虚拟内存与页面置换算法（FIFO、LRU、Clock）。",
     "prerequisites": ["进程与线程"]},
    {"name": "处理器调度", "subject": "操作系统", "chapter": "第 2 章 进程管理", "difficulty": "中",
     "description": "先来先服务、短作业优先、时间片轮转与多级反馈队列。",
     "prerequisites": ["进程与线程"]},
    {"name": "文件系统", "subject": "操作系统", "chapter": "第 4 章 文件管理", "difficulty": "易",
     "description": "文件逻辑结构与物理结构、目录、磁盘空间管理。",
     "prerequisites": ["内存管理"]},
    # 计算机网络
    {"name": "网络分层模型", "subject": "计算机网络", "chapter": "第 1 章 概述", "difficulty": "易",
     "description": "OSI 七层与 TCP/IP 四层模型，各层职责与封装过程。",
     "prerequisites": []},
    {"name": "TCP/IP 协议", "subject": "计算机网络", "chapter": "第 3 章 传输层", "difficulty": "难",
     "description": "TCP 三次握手与四次挥手、拥塞控制、滑动窗口；UDP 特点。",
     "prerequisites": ["网络分层模型"]},
    {"name": "HTTP 协议", "subject": "计算机网络", "chapter": "第 5 章 应用层", "difficulty": "中",
     "description": "HTTP/1.1 与 HTTP/2、请求响应模型、无状态与会话保持。",
     "prerequisites": ["TCP/IP 协议"]},
    {"name": "DNS 解析", "subject": "计算机网络", "chapter": "第 5 章 应用层", "difficulty": "中",
     "description": "域名层次结构、递归与迭代查询、缓存与 DNS 劫持。",
     "prerequisites": ["网络分层模型"]},
    {"name": "路由与交换", "subject": "计算机网络", "chapter": "第 2 章 网络层", "difficulty": "中",
     "description": "IP 地址与子网划分、路由协议（RIP、OSPF）与交换原理。",
     "prerequisites": ["网络分层模型"]},
    # 数据库
    {"name": "关系模型", "subject": "数据库系统", "chapter": "第 2 章 关系数据库", "difficulty": "易",
     "description": "关系、元组、属性、候选键与范式（1NF-3NF）。",
     "prerequisites": ["集合论基础"]},
    {"name": "SQL 查询", "subject": "数据库系统", "chapter": "第 3 章 SQL", "difficulty": "中",
     "description": "SELECT/INSERT/UPDATE/DELETE、连接查询、子查询与聚合。",
     "prerequisites": ["关系模型"]},
    {"name": "事务与 ACID", "subject": "数据库系统", "chapter": "第 4 章 事务", "difficulty": "中",
     "description": "原子性、一致性、隔离性、持久性；并发控制与隔离级别。",
     "prerequisites": ["SQL 查询"]},
    {"name": "索引与查询优化", "subject": "数据库系统", "chapter": "第 5 章 索引", "difficulty": "难",
     "description": "B+ 树索引、哈希索引、执行计划与查询优化器。",
     "prerequisites": ["SQL 查询", "树与二叉树"]},
    # 人工智能
    {"name": "机器学习基础", "subject": "人工智能", "chapter": "第 2 章 机器学习", "difficulty": "中",
     "description": "监督/无监督/强化学习，模型评估（准确率、精确率、召回率），过拟合与正则化。",
     "prerequisites": ["概率论", "线性代数"]},
    {"name": "深度学习", "subject": "人工智能", "chapter": "第 3 章 深度学习", "difficulty": "难",
     "description": "神经网络前向/反向传播、激活函数、卷积网络与循环网络基础。",
     "prerequisites": ["机器学习基础"]},
    {"name": "大语言模型", "subject": "人工智能", "chapter": "第 4 章 大模型", "difficulty": "难",
     "description": "Transformer 架构、预训练与指令微调、提示工程与上下文学习。",
     "prerequisites": ["深度学习"]},
    {"name": "检索增强生成 RAG", "subject": "人工智能", "chapter": "第 4 章 大模型", "difficulty": "难",
     "description": "文档切分、向量化、检索、重排与生成结合，缓解幻觉、增强可追溯性。",
     "prerequisites": ["大语言模型", "索引与查询优化"]},
    {"name": "强化学习", "subject": "人工智能", "chapter": "第 5 章 强化学习", "difficulty": "难",
     "description": "马尔可夫决策过程、Q-learning、策略梯度与 RLHF。",
     "prerequisites": ["机器学习基础"]},
]


# 课程章节（按官方教材结构，支撑预习/复习/模拟范围）
CHAPTERS: dict[str, list[dict]] = {
    "数据结构": [
        {"key": "ch1", "title": "绪论与算法分析", "official_ref": "第 1 章", "summary": "数据结构的基本概念、逻辑/存储结构、算法复杂度分析。"},
        {"key": "ch2", "title": "线性表", "official_ref": "第 2 章", "summary": "顺序表与链表的结构、操作与复杂度对比。"},
        {"key": "ch3", "title": "栈与队列", "official_ref": "第 3 章", "summary": "栈与队列的特性、实现与应用。"},
        {"key": "ch4", "title": "树与二叉树", "official_ref": "第 4 章", "summary": "二叉树性质、遍历、线索化与 Huffman 树。"},
        {"key": "ch5", "title": "图", "official_ref": "第 5 章", "summary": "图的存储、遍历、最小生成树与最短路径。"},
        {"key": "ch6", "title": "查找与排序", "official_ref": "第 6 章", "summary": "静态/动态查找、哈希表与经典排序算法。"},
    ],
    "算法设计与分析": [
        {"key": "ch1", "title": "算法基础与复杂度", "official_ref": "第 1 章", "summary": "大 O 记号与复杂度分析方法。"},
        {"key": "ch2", "title": "分治策略", "official_ref": "第 2 章", "summary": "分解-求解-合并范式与经典应用。"},
        {"key": "ch3", "title": "动态规划", "official_ref": "第 3 章", "summary": "最优子结构、状态转移与经典问题。"},
        {"key": "ch4", "title": "贪心算法", "official_ref": "第 4 章", "summary": "贪心选择性质与活动安排等问题。"},
        {"key": "ch5", "title": "回溯与搜索", "official_ref": "第 5 章", "summary": "状态空间树、剪枝与典型问题。"},
    ],
    "操作系统": [
        {"key": "ch1", "title": "操作系统概述", "official_ref": "第 1 章", "summary": "操作系统的功能、发展与环境。"},
        {"key": "ch2", "title": "进程管理", "official_ref": "第 2 章", "summary": "进程/线程、调度、同步互斥与死锁。"},
        {"key": "ch3", "title": "内存管理", "official_ref": "第 3 章", "summary": "分页分段、虚拟内存与页面置换。"},
        {"key": "ch4", "title": "文件系统", "official_ref": "第 4 章", "summary": "文件逻辑/物理结构、目录与磁盘管理。"},
    ],
    "计算机网络": [
        {"key": "ch1", "title": "网络体系结构", "official_ref": "第 1 章", "summary": "分层模型、协议与封装。"},
        {"key": "ch2", "title": "网络层与路由", "official_ref": "第 2 章", "summary": "IP 编址、子网划分与路由协议。"},
        {"key": "ch3", "title": "传输层 TCP/UDP", "official_ref": "第 3 章", "summary": "可靠传输、流量与拥塞控制。"},
        {"key": "ch4", "title": "应用层协议", "official_ref": "第 4 章", "summary": "HTTP、DNS 与典型应用协议。"},
    ],
    "数据库系统": [
        {"key": "ch1", "title": "数据库系统概论", "official_ref": "第 1 章", "summary": "数据模型、数据库系统结构。"},
        {"key": "ch2", "title": "关系数据库", "official_ref": "第 2 章", "summary": "关系模型、完整性约束与范式。"},
        {"key": "ch3", "title": "SQL 与查询", "official_ref": "第 3 章", "summary": "SQL 语言、连接查询与聚合。"},
        {"key": "ch4", "title": "事务与并发", "official_ref": "第 4 章", "summary": "ACID、隔离级别与并发控制。"},
        {"key": "ch5", "title": "索引与优化", "official_ref": "第 5 章", "summary": "B+ 树、执行计划与查询优化。"},
    ],
    "人工智能": [
        {"key": "ch1", "title": "人工智能导论", "official_ref": "第 1 章", "summary": "AI 发展、应用与研究范式。"},
        {"key": "ch2", "title": "机器学习基础", "official_ref": "第 2 章", "summary": "监督/无监督/强化，评估与正则化。"},
        {"key": "ch3", "title": "深度学习", "official_ref": "第 3 章", "summary": "神经网络、反向传播与 CNN/RNN。"},
        {"key": "ch4", "title": "大模型与 RAG", "official_ref": "第 4 章", "summary": "Transformer、LLM、提示工程与 RAG。"},
        {"key": "ch5", "title": "强化学习", "official_ref": "第 5 章", "summary": "MDP、Q-learning 与策略梯度。"},
    ],
    "计算机组成原理": [
        {"key": "ch1", "title": "计算机系统概论", "official_ref": "第 1 章", "summary": "冯·诺依曼结构、性能指标。"},
        {"key": "ch2", "title": "数据的表示与运算", "official_ref": "第 2 章", "summary": "数制、定点/浮点表示与运算。"},
        {"key": "ch3", "title": "存储系统", "official_ref": "第 3 章", "summary": "层次结构、Cache 与主存。"},
        {"key": "ch4", "title": "指令系统与 CPU", "official_ref": "第 4 章", "summary": "指令格式、寻址方式与数据通路。"},
        {"key": "ch5", "title": "输入输出系统", "official_ref": "第 5 章", "summary": "总线、中断与 DMA。"},
    ],
}


KNOWLEDGE_DOCUMENTS = [
    # ---------- 数据结构 ----------
    {
        "title": "线性表：顺序表与链表",
        "source": "《数据结构（C 语言版）》（严蔚敏）讲义",
        "course": "数据结构", "topic": "线性表", "chapter": "第 2 章", "difficulty": "易",
        "type": "讲义", "year": 2024,
        "content": """线性表是 n 个数据元素的有限序列，是最基本的数据组织方式。顺序表用一组地址连续的存储单元依次存放元素，支持随机访问，但插入删除需要移动大量元素，平均时间复杂度为 O(n)。链表通过指针把逻辑上相邻的元素链接起来，插入删除只需修改指针，但无法随机访问。
顺序表适用于查找频繁、增删较少的场景；链表适用于增删频繁的场景。双向链表增加了前驱指针，便于双向遍历；循环链表使表尾指向表头，适合环形队列等应用。
典型应用包括：一元多项式表示、稀疏多项式运算、学生信息管理系统中的动态表。理解两种存储结构的时间复杂度差异，是分析后续栈、队列、树结构的基础。""",
    },
    {
        "title": "栈与队列的应用",
        "source": "《数据结构》（清华大学出版社）第 3 章",
        "course": "数据结构", "topic": "栈和队列", "chapter": "第 3 章", "difficulty": "中",
        "type": "教材", "year": 2023,
        "content": """栈是后进先出（LIFO）的受限线性表，只允许在栈顶进行插入和删除。括号匹配、表达式求值、函数递归调用、浏览器的后退功能都是栈的典型应用。
队列是先进先出（FIFO）的受限线性表，只允许在队尾插入、队头删除。操作系统中的作业调度、消息队列、BFS 广度优先遍历都依赖队列。
循环队列通过取模运算复用数组空间，避免假溢出。入队时队尾指针 front=(front+1)%maxSize，判满条件 (rear+1)%maxSize==front。
栈与队列在编译原理、操作系统、图论算法中无处不在，掌握其顺序与链式实现是算法设计的基本功。""",
    },
    {
        "title": "二叉树遍历与性质",
        "source": "《数据结构》课程讲义 · 第 4 章",
        "course": "数据结构", "topic": "树与二叉树", "chapter": "第 4 章", "difficulty": "中",
        "type": "讲义", "year": 2025,
        "content": """二叉树是每个结点至多有两棵子树的树结构。重要性质：第 i 层最多有 2^(i-1) 个结点；深度为 k 的二叉树最多有 2^k-1 个结点；n 个结点的完全二叉树深度为 floor(log2 n)+1。
遍历方式包括先序遍历（根左右）、中序遍历（左根右）、后序遍历（左右根）与层次遍历。已知先序+中序或后序+中序可以唯一确定一棵二叉树。
Huffman 树是带权路径长度最小的二叉树，常用于构造最优前缀编码。二叉排序树（BST）利用有序性实现 O(log n) 的平均查找。
递归是二叉树算法的核心工具：二叉树深度、结点统计、路径求和等问题都能用递归简洁求解，但要注意递归深度与空间复杂度。""",
    },
    {
        "title": "图：存储、遍历与最短路径",
        "source": "《数据结构》实验指导书 · 实验五",
        "course": "数据结构", "topic": "图", "chapter": "第 5 章", "difficulty": "难",
        "type": "实验", "year": 2025,
        "content": """图的存储主要有邻接矩阵与邻接表。邻接矩阵适合稠密图，判断两点是否相邻为 O(1)；邻接表适合稀疏图，空间复杂度 O(V+E)。
深度优先搜索（DFS）借助递归或栈，广度优先搜索（BFS）借助队列，两者都能判定连通性并求解无权图最短路径。
Prim 与 Kruskal 算法分别从点集与边集角度构造最小生成树。Dijkstra 算法求解单源最短路径，要求边权非负；Floyd 算法用动态规划求解任意两点间最短路径。
图论是算法竞赛与工程问题（社交网络、地图导航、任务调度）的通用建模语言，实验建议实现 BFS 迷宫寻路与 Dijkstra 最短路。""",
    },
    # ---------- 算法 ----------
    {
        "title": "算法复杂度分析",
        "source": "《算法导论》第 2-3 章 整理讲义",
        "course": "算法设计与分析", "topic": "复杂度", "chapter": "第 1 章", "difficulty": "易",
        "type": "讲义", "year": 2024,
        "content": """算法复杂度用大 O 记号描述输入规模 n 增长时的资源消耗趋势。常见量级：O(1) < O(log n) < O(n) < O(n log n) < O(n^2) < O(2^n)。
时间复杂度分析关注最内层循环的执行次数；递归算法可建立递推式并用主定理求解，如归并排序 T(n)=2T(n/2)+O(n) 解得 O(n log n)。
空间复杂度包括输入占用之外的辅助空间。分析时区分最好、最坏与平均情况，例如快速排序平均 O(n log n)、最坏 O(n^2)。
复杂度分析是算法设计的第一道门槛：先估复杂度，再选算法，最后优化常数与实现细节。""",
    },
    {
        "title": "分治策略与归并排序",
        "source": "《算法设计与分析基础》第 4 章",
        "course": "算法设计与分析", "topic": "分治", "chapter": "第 2 章", "difficulty": "中",
        "type": "教材", "year": 2023,
        "content": """分治策略把原问题分解为规模更小且结构相同的子问题，递归求解后合并结果，典型范式是“分解-求解-合并”。
归并排序把数组一分为二，递归排序后线性合并，复杂度稳定 O(n log n)，是外部排序的基础。快速排序以枢轴元素划分数组，平均 O(n log n)，常数小但最坏退化为 O(n^2)。
二分查找是分治的最简形式，每次减半搜索区间，复杂度 O(log n)。最近点对、最大子数组和等问题也常用分治求解。
分治的关键是正确分析子问题规模与合并代价，避免重复计算，否则可能退化为指数复杂度。""",
    },
    {
        "title": "Algorithm Design: Stable Matching",
        "source": "Algorithm Design (Kleinberg & Tardos), Chapter 1",
        "course": "算法设计与分析", "topic": "稳定匹配 Stable Matching", "chapter": "第 1 章", "difficulty": "中",
        "type": "教材", "year": 2026,
        "content": """The Stable Matching Problem, introduced by Gale and Shapley (1962), asks for a perfect matching between n men and n women in which no unstable pair exists. A pair (m, w) is unstable if m prefers w to his current partner and w prefers m to her current partner.
The Gale-Shapley algorithm (deferred acceptance) works as follows: while some man is free and has not proposed to every woman, that man proposes to the woman he ranks highest whom he has not yet proposed to. The woman tentatively accepts the best proposal she has received and rejects the others. The process repeats until every man is engaged.
Properties: the algorithm always terminates in at most n^2 proposals and always produces a stable matching. It is optimal for the proposing side: every man receives the best partner he could get in any stable matching, while every woman receives the worst partner she could get in any stable matching. The running time is O(n^2).
Applications include college admissions, resident-hospital assignment, and public-school assignment. The problem is closely related to bipartite graph matching and is a classic example of greedy and deferred-acceptance reasoning.""",
    },
    {
        "title": "动态规划：从背包到编辑距离",
        "source": "《算法竞赛入门经典》第 9 章",
        "course": "算法设计与分析", "topic": "动态规划", "chapter": "第 3 章", "difficulty": "难",
        "type": "教材", "year": 2024,
        "content": """动态规划适用于具有最优子结构与重叠子问题的问题。核心是定义状态与状态转移方程，并用记忆化或自底向上填表避免重复计算。
0/1 背包：dp[i][w]=max(dp[i-1][w], dp[i-1][w-wi]+vi)，可滚动数组优化到一维。最长公共子序列（LCS）与编辑距离（Levenshtein）都是经典的二维 DP。
动态规划从“暴力递归 → 记忆化 → 迭代填表 → 空间优化”四步演进，是面试与竞赛的高频考点。常见错误是状态定义不清或初始化遗漏边界。
建议通过“数字三角形”“最长递增子序列”“钢条切割”三个入门题建立 DP 直觉，再进阶区间 DP 与树形 DP。""",
    },
    # ---------- 操作系统 ----------
    {
        "title": "进程、线程与调度",
        "source": "《计算机操作系统》（汤小丹）第 2 章",
        "course": "操作系统", "topic": "进程管理", "chapter": "第 2 章", "difficulty": "中",
        "type": "教材", "year": 2023,
        "content": """进程是资源分配的基本单位，包含代码段、数据段、堆栈与进程控制块 PCB；线程是 CPU 调度的基本单位，同一进程的线程共享地址空间与资源。
进程有就绪、运行、阻塞三种基本状态，通过调度与等待事件相互转换。进程间通信包括管道、消息队列、共享内存与信号量。
常用调度算法：先来先服务（FCFS）、短作业优先（SJF）、时间片轮转（RR）与多级反馈队列（MLFQ）。现代操作系统普遍采用优先级抢占式调度。
进程与线程的区别是高频考点：进程隔离性好但切换开销大，线程切换轻量但需同步保护共享数据。""",
    },
    {
        "title": "进程同步：信号量与经典问题",
        "source": "《现代操作系统》第 2 章 整理",
        "course": "操作系统", "topic": "同步互斥", "chapter": "第 2 章", "difficulty": "难",
        "type": "讲义", "year": 2024,
        "content": """临界区是访问共享资源的代码段，需满足互斥、前进、有限等待三个原则。信号量 S 支持 P（wait，S--，小于 0 则阻塞）与 V（signal，S++，唤醒等待者）操作，是解决同步互斥的通用工具。
经典问题：生产者-消费者用三个信号量（互斥、空位、满位）实现有界缓冲区；读者-写者问题用读写锁思想；哲学家进餐问题通过限制并发数或顺序取筷避免死锁。
死锁的四个必要条件：互斥、占有并等待、不可剥夺、循环等待。避免死锁可用银行家算法，检测后可用资源剥夺或进程回退恢复。
同步问题要求先画清并发流程，再选择信号量组合，最后验证各条路径都不违反互斥与顺序约束。""",
    },
    {
        "title": "内存管理与页面置换",
        "source": "《计算机操作系统》第 3 章 实验指导",
        "course": "操作系统", "topic": "内存管理", "chapter": "第 3 章", "difficulty": "中",
        "type": "实验", "year": 2025,
        "content": """分页将逻辑地址划分为固定大小的页，页表完成逻辑页到物理页框的映射；分段按程序逻辑结构划分，便于共享与保护；段页式结合两者优点。
虚拟内存允许进程访问比物理内存更大的地址空间，缺页时按需装入。页面置换算法：FIFO 实现简单但可能产生 Belady 异常；LRU 基于最近使用历史，性能好；Clock（时钟）算法用访问位近似 LRU，是实际系统常用方案。
实验建议：实现 OPT/FIFO/LRU/Clock 四种置换算法并统计缺页率，比较不同访问序列下的表现差异。
局部性原理（时间局部性、空间局部性）是虚拟内存有效的理论基础。""",
    },
    # ---------- 计算机网络 ----------
    {
        "title": "TCP/IP 分层模型与封装",
        "source": "《计算机网络》（谢希仁）第 1 章",
        "course": "计算机网络", "topic": "网络分层", "chapter": "第 1 章", "difficulty": "易",
        "type": "教材", "year": 2023,
        "content": """网络协议采用分层设计：OSI 七层模型（物理、数据链路、网络、传输、会话、表示、应用）与 TCP/IP 四层模型（网络接口、网际、传输、应用）。
发送方逐层封装，依次添加各层首部；接收方逐层解封装。路由器工作在网络层，交换机工作在数据链路层，集线器工作在物理层。
分层的好处是各层独立演化、接口清晰，例如应用层可自由选择 TCP 或 UDP 作为传输服务。
理解“每一层的 PDU 名称”（帧、报文段、数据报）与各层地址（MAC 地址、IP 地址、端口号）是网络排障的基础。""",
    },
    {
        "title": "TCP 可靠传输与拥塞控制",
        "source": "《计算机网络》第 3 章 讲义",
        "course": "计算机网络", "topic": "TCP/IP", "chapter": "第 3 章", "difficulty": "难",
        "type": "讲义", "year": 2024,
        "content": """TCP 是面向连接、可靠、字节流传输协议。三次握手建立连接（SYN、SYN+ACK、ACK），四次挥手释放连接（FIN、ACK 交错）。
可靠传输依赖序号、确认、重传与滑动窗口。发送窗口由接收窗口 rwnd 与拥塞窗口 cwnd 共同决定。
拥塞控制包括慢启动（指数增长）、拥塞避免（线性增长）、快重传与快恢复。经典算法 Tahoe 与 Reno 的区别在于拥塞发生时如何调整 cwnd。
面试高频题：为什么握手三次而非两次？因为需要确认双方收发能力；为什么挥手四次？因为全双工关闭需要两个方向分别 FIN。""",
    },
    {
        "title": "HTTP 协议与会话保持",
        "source": "《图解 HTTP》整理讲义",
        "course": "计算机网络", "topic": "HTTP", "chapter": "第 5 章", "difficulty": "中",
        "type": "讲义", "year": 2025,
        "content": """HTTP 是无状态的应用层协议，请求-响应模型由方法、URL、头部与实体构成。常见方法：GET 取资源、POST 提交、PUT 更新、DELETE 删除。
HTTP/1.1 引入持久连接与管线化，减少连接建立开销；HTTP/2 使用二进制分帧、多路复用与头部压缩，提升并发性能。
由于 HTTP 无状态，Web 应用用 Cookie/Session/Token 维护会话：服务器签发会话标识，客户端携带标识完成身份认证。
HTTPS 在 HTTP 与 TCP 之间加入 TLS 层，通过证书链验证身份并加密传输，是当前 Web 安全的基础。""",
    },
    # ---------- 数据库 ----------
    {
        "title": "关系模型与范式",
        "source": "《数据库系统概论》（王珊）第 2 章",
        "course": "数据库系统", "topic": "关系模型", "chapter": "第 2 章", "difficulty": "易",
        "type": "教材", "year": 2023,
        "content": """关系模型用二维表组织数据：行（元组）代表记录，列（属性）代表字段，候选键可唯一标识元组。完整性约束包括实体完整性、参照完整性与用户定义完整性。
范式用于消除冗余与异常：1NF 要求属性原子；2NF 消除非主属性对候选键的部分依赖；3NF 消除传递依赖；BCNF 要求所有决定因素都是候选键。
反范式化在查询密集场景故意引入冗余以换取读性能，是工程权衡。
设计练习：把“学生-课程-选课”拆成三张表，通过外键关联，既避免重复存储又保证更新一致性。""",
    },
    {
        "title": "SQL 查询与索引优化",
        "source": "《高性能 MySQL》精选",
        "course": "数据库系统", "topic": "SQL/索引", "chapter": "第 3-5 章", "difficulty": "中",
        "type": "讲义", "year": 2024,
        "content": """SQL 分为 DDL（建表）、DML（增删改）、DQL（查询）与 DCL（权限）。多表连接包括 INNER JOIN、LEFT JOIN、RIGHT JOIN；子查询可改写为 JOIN 提升可读性。
索引是加速查询的数据结构：B+ 树索引支持范围查询与排序，哈希索引适合等值查询。最左前缀原则决定了联合索引的列顺序。
查询优化器通过统计信息选择执行计划，EXPLAIN 可查看访问类型（type）、扫描行数（rows）与是否使用索引（key）。
常见优化：避免 SELECT *、为 WHERE/JOIN/ORDER BY 列建索引、用小结果集驱动大表、分页用覆盖索引。""",
    },
    {
        "title": "事务、ACID 与并发控制",
        "source": "《数据库系统概论》第 4 章",
        "course": "数据库系统", "topic": "事务", "chapter": "第 4 章", "difficulty": "中",
        "type": "教材", "year": 2023,
        "content": """事务是数据库操作的原子执行单位。ACID：原子性（全做或全不做）、一致性（约束不被破坏）、隔离性（并发互不干扰）、持久性（提交后不丢失）。
并发问题包括脏读、不可重复读与幻读。隔离级别从低到高：读未提交、读已提交、可重复读、串行化。MySQL InnoDB 默认可重复读，用 MVCC 加间隙锁解决幻读。
实现原子性与持久性依赖 undo log 与 redo log；日志先行（WAL）保证崩溃恢复能力。
理解隔离级别与锁的关系，是排查线上“数据对不上”问题的关键。""",
    },
    # ---------- 人工智能 ----------
    {
        "title": "机器学习基础与模型评估",
        "source": "《机器学习》（周志华）第 2 章",
        "course": "人工智能", "topic": "机器学习", "chapter": "第 2 章", "difficulty": "中",
        "type": "教材", "year": 2023,
        "content": """机器学习分监督学习（分类/回归）、无监督学习（聚类/降维）与强化学习。特征工程与数据质量直接影响模型上限。
模型评估指标：准确率、精确率、召回率、F1；二分类用混淆矩阵分析。ROC 曲线与 AUC 衡量排序能力，对类别不平衡更稳健。
过拟合指模型记住训练集噪声而泛化差，缓解手段：更多数据、正则化（L1/L2）、Dropout、交叉验证、早停。
偏差-方差权衡：高偏差欠拟合，高方差过拟合；集成方法（Bagging 降方差、Boosting 降偏差）是经典兜底方案。""",
    },
    {
        "title": "Transformer 与大语言模型",
        "source": "《Attention Is All You Need》精读讲义",
        "course": "人工智能", "topic": "大语言模型", "chapter": "第 4 章", "difficulty": "难",
        "type": "论文精读", "year": 2025,
        "content": """Transformer 的核心是自注意力机制：Query、Key、Value 三个向量通过缩放点积计算注意力权重，多头注意力让模型从不同子空间捕捉关系。
大语言模型遵循“预训练 → 指令微调 → 人类反馈对齐（RLHF）”范式。GPT 系列用自回归目标，BERT 用掩码语言模型目标。
提示工程（Prompt Engineering）通过指令、示例（few-shot）与思维链（CoT）激发模型能力；上下文学习（In-Context Learning）无需更新参数即可适配新任务。
局限与挑战：幻觉、知识时效性、推理成本与安全对齐，直接推动了 RAG 与 Agent 方向的快速发展。""",
    },
    {
        "title": "RAG：检索增强生成全流程",
        "source": "《Retrieval-Augmented Generation》综述讲义",
        "course": "人工智能", "topic": "RAG", "chapter": "第 4 章", "difficulty": "难",
        "type": "论文精读", "year": 2025,
        "content": """RAG 在生成前先从外部知识库检索相关内容，把检索结果作为上下文注入提示词，显著降低幻觉并支持来源引用。
标准流程：文档切分（chunking，按段落/语义切分并保留重叠）→ 向量化（Embedding 模型编码）→ 向量库存储 → 相似度检索（Top-K）→ 重排（Rerank）→ LLM 生成。
切分粒度影响召回：过长丢失定位精度，过短缺乏上下文；常见做法是 300-500 token 加 10-20% 重叠，并保留章节元数据。
检索质量评估用召回率与命中位置；生成质量关注忠实度（是否忠于引用）与答案完整性。混合检索（关键词+向量）在专业术语场景往往优于纯向量检索。""",
    },
]
