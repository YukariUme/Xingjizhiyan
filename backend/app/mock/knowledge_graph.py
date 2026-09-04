"""操作系统课程两级知识点（一级知识点 → 子知识点），用于知识图谱与思维导图。"""

# 每个子知识点：{name, description, difficulty}
DEFAULT_SUB_POINTS: dict[str, list[dict]] = {
    "进程与线程": [
        {"name": "进程控制块 PCB", "description": "PCB 记录进程状态、寄存器、内存、打开文件等，是进程存在的唯一标志。", "difficulty": "易"},
        {"name": "进程状态转换", "description": "创建、就绪、运行、阻塞、终止五态，以及各状态间的转换条件。", "difficulty": "中"},
        {"name": "进程地址空间", "description": "代码段、数据段、堆、栈的划分，虚拟地址到物理地址的映射。", "difficulty": "中"},
        {"name": "线程模型", "description": "用户级线程与内核级线程，多对一/一对一/多对多三种映射模型。", "difficulty": "中"},
        {"name": "系统调用与中断", "description": "用户态与内核态切换，系统调用的执行流程。", "difficulty": "中"},
    ],
    "进程同步与互斥": [
        {"name": "临界区与临界资源", "description": "访问共享资源的代码段需满足互斥、前进、有限等待三原则。", "difficulty": "易"},
        {"name": "互斥与同步的区别", "description": "互斥保证资源独占，同步约束并发进程的执行顺序。", "difficulty": "中"},
        {"name": "信号量与 P/V 操作", "description": "整型/记录型信号量，P 阻塞、V 唤醒，操作必须原子。", "difficulty": "难"},
        {"name": "生产者—消费者问题", "description": "用 empty/full/mutex 三个信号量解决缓冲区同步互斥。", "difficulty": "难"},
        {"name": "读者—写者问题", "description": "读者优先/写者优先策略，读写锁与信号量实现。", "difficulty": "难"},
        {"name": "管程与条件变量", "description": "封装共享资源与操作，条件变量 wait/signal 实现同步。", "difficulty": "难"},
    ],
    "处理器调度": [
        {"name": "调度准则", "description": "CPU 利用率、吞吐量、周转时间、等待时间、响应时间等指标。", "difficulty": "易"},
        {"name": "先来先服务 FCFS", "description": "按到达顺序服务，实现简单但平均等待时间长。", "difficulty": "易"},
        {"name": "短作业优先 SJF", "description": "平均等待时间最短，但长作业可能饿死。", "difficulty": "中"},
        {"name": "时间片轮转 RR", "description": "按时间片轮流执行，响应快，时间片大小影响系统开销。", "difficulty": "中"},
        {"name": "优先级调度", "description": "抢占/非抢占，注意优先级反转问题。", "difficulty": "中"},
        {"name": "多级反馈队列 MLFQ", "description": "综合响应与周转，动态调整优先级，现代系统常用。", "difficulty": "难"},
    ],
    "死锁": [
        {"name": "死锁产生的必要条件", "description": "互斥、占有并等待、不可剥夺、循环等待四个条件同时满足。", "difficulty": "中"},
        {"name": "死锁预防", "description": "破坏四个必要条件之一，代价较高。", "difficulty": "中"},
        {"name": "死锁避免", "description": "银行家算法、安全状态判断，避免进入不安全状态。", "difficulty": "难"},
        {"name": "死锁检测与解除", "description": "资源分配图化简，撤销或回退进程解除死锁。", "difficulty": "难"},
        {"name": "哲学家进餐问题", "description": "经典死锁案例，通过同时拿筷/信号量限制解决。", "difficulty": "中"},
    ],
    "内存管理": [
        {"name": "连续分配", "description": "固定分区/动态分区，存在内部与外部碎片。", "difficulty": "易"},
        {"name": "分页存储管理", "description": "页表、页号与偏移、地址变换，TLB 加速。", "difficulty": "中"},
        {"name": "分段存储管理", "description": "按逻辑段划分，段表实现共享与保护。", "difficulty": "中"},
        {"name": "段页式管理", "description": "先分段再分页，两级查表，兼顾灵活与效率。", "difficulty": "难"},
        {"name": "虚拟内存与请求调页", "description": "只装入用到的页，缺页中断触发调页。", "difficulty": "中"},
        {"name": "页面置换算法", "description": "OPT/FIFO/LRU/时钟算法，Belady 异常。", "difficulty": "难"},
    ],
    "文件系统": [
        {"name": "文件逻辑结构", "description": "顺序文件、索引文件、链接文件。", "difficulty": "易"},
        {"name": "目录结构", "description": "单级、两级、树形与无环图目录。", "difficulty": "中"},
        {"name": "文件存储分配", "description": "连续分配、链接分配、索引分配。", "difficulty": "中"},
        {"name": "空闲空间管理", "description": "空闲表、空闲链表、位示图、成组链接。", "difficulty": "中"},
        {"name": "磁盘调度", "description": "FCFS、SSTF、SCAN、C-SCAN、LOOK 算法。", "difficulty": "中"},
    ],
    "设备管理": [
        {"name": "I/O 控制方式", "description": "程序查询、中断、DMA、通道四种控制方式。", "difficulty": "中"},
        {"name": "缓冲技术", "description": "单缓冲、双缓冲、循环缓冲、缓冲池。", "difficulty": "中"},
        {"name": "SPOOLing 技术", "description": "假脱机输入输出，把独占设备改造为共享设备。", "difficulty": "中"},
        {"name": "设备分配与回收", "description": "设备控制表、通道控制表，分配算法。", "difficulty": "中"},
        {"name": "设备独立性", "description": "逻辑设备到物理设备的映射，屏蔽硬件差异。", "difficulty": "中"},
    ],
}


def default_sub_points(point_name: str) -> list[dict]:
    """按知识点名称返回内置子知识点；未收录时返回两个通用子点。"""
    exact = DEFAULT_SUB_POINTS.get(point_name)
    if exact:
        return exact
    for key, subs in DEFAULT_SUB_POINTS.items():
        if key in point_name or point_name in key:
            return subs
    return [
        {"name": f"{point_name}·核心概念", "description": f"{point_name} 的核心定义与原理。", "difficulty": "中"},
        {"name": f"{point_name}·典型应用", "description": f"{point_name} 的典型场景与实现。", "difficulty": "中"},
    ]
