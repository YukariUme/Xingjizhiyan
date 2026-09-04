"""RAG 检索评测：对真实知识库运行 30+ 道学科问题，输出 Recall@k 等指标。

用法（在 backend 目录下）：
    python -m scripts.rag_eval                    # 默认 auto 模式（真实 Embedding 优先）
    python -m scripts.rag_eval --embedding hash   # 对比纯词法/哈希模式
    python -m scripts.rag_eval --no-report        # 只打印摘要，不写报告

输出：
    控制台汇总 + docs/RAG_EVAL_REPORT.md（Recall@1/3/5、命中位置、平均相似度、
    来源等级分布、grounded 判定、负例误报率）。
"""

import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.services.embedding import FastEmbeddingService, HashEmbeddingService  # noqa: E402
from app.services.rag.sqlite import SQLiteRAGService  # noqa: E402


# 每道题：问题 + 期望命中的文档标题关键词（任一命中即算 hit）
EVAL_QUESTIONS: list[dict] = [
    # 数据结构
    {"q": "线性表的顺序存储和链式存储有什么区别", "expect": ["线性表"]},
    {"q": "单链表如何实现插入和删除操作", "expect": ["线性表", "Algorithm Design"]},
    {"q": "栈和队列的区别是什么", "expect": ["栈与队列", "Algorithm Design"]},
    {"q": "栈的应用场景有哪些，括号匹配怎么用栈实现", "expect": ["栈与队列"]},
    {"q": "二叉树的前序、中序、后序遍历怎么写", "expect": ["二叉树"]},
    {"q": "二叉树的性质：第 i 层最多有多少个结点", "expect": ["二叉树"]},
    {"q": "图的深度优先遍历和广度优先遍历", "expect": ["图"]},
    {"q": "Dijkstra 最短路径算法的基本思想", "expect": ["图", "离散数学"]},
    # 算法设计与分析
    {"q": "什么是算法的时间复杂度和空间复杂度", "expect": ["算法复杂度"]},
    {"q": "大 O 记号如何表示算法增长量级", "expect": ["算法复杂度", "离散数学"]},
    {"q": "归并排序的分治思想是什么", "expect": ["分治"]},
    {"q": "快速排序和归并排序的复杂度对比", "expect": ["分治"]},
    {"q": "动态规划的基本思想与最优子结构", "expect": ["动态规划", "Algorithm Design", "离散数学"]},
    {"q": "0-1 背包问题怎么用动态规划求解", "expect": ["动态规划", "Algorithm Design"]},
    {"q": "编辑距离的动态规划解法", "expect": ["动态规划", "Algorithm Design"]},
    {"q": "婚姻匹配问题是什么，稳定婚姻如何求解", "expect": ["Algorithm Design"]},
    {"q": "Gale-Shapley 算法如何保证稳定匹配", "expect": ["Algorithm Design"]},
    # 操作系统
    {"q": "进程和线程有什么区别", "expect": ["进程、线程与调度"]},
    {"q": "进程有哪些状态，状态之间如何转换", "expect": ["进程、线程与调度"]},
    {"q": "操作系统的进程调度算法有哪些", "expect": ["进程、线程与调度"]},
    {"q": "信号量如何实现进程同步与互斥", "expect": ["进程同步"]},
    {"q": "生产者消费者问题怎么用信号量解决", "expect": ["进程同步"]},
    {"q": "死锁产生的四个必要条件是什么", "expect": ["进程同步"]},
    {"q": "虚拟内存和页面置换算法有哪些", "expect": ["内存管理"]},
    {"q": "LRU 页面置换算法的工作原理", "expect": ["内存管理"]},
    # 计算机网络
    {"q": "TCP/IP 分层模型包含哪些层次", "expect": ["TCP/IP 分层"]},
    {"q": "TCP 三次握手的过程是怎样的", "expect": ["TCP 可靠传输"]},
    {"q": "TCP 拥塞控制有哪些算法", "expect": ["TCP 可靠传输"]},
    {"q": "HTTP 协议与 HTTPS 有什么区别", "expect": ["HTTP"]},
    {"q": "Cookie 和 Session 如何维持会话", "expect": ["HTTP"]},
    # 数据库系统
    {"q": "关系模型中的第一范式、第二范式、第三范式", "expect": ["关系模型与范式"]},
    {"q": "数据库范式分解的目的是什么", "expect": ["关系模型与范式"]},
    {"q": "SQL 中 JOIN 查询怎么写", "expect": ["SQL 查询"]},
    {"q": "数据库索引的原理和优化方法", "expect": ["SQL 查询"]},
    {"q": "事务的 ACID 特性是什么", "expect": ["事务、ACID"]},
    {"q": "数据库并发控制如何实现隔离性", "expect": ["事务、ACID"]},
    # 人工智能
    {"q": "监督学习和无监督学习的区别", "expect": ["机器学习基础"]},
    {"q": "过拟合是什么，如何避免", "expect": ["机器学习基础"]},
    {"q": "Transformer 的注意力机制是什么", "expect": ["Transformer"]},
    {"q": "大语言模型是怎么训练的", "expect": ["Transformer"]},
    {"q": "RAG 检索增强生成的流程是怎样的", "expect": ["RAG"]},
    {"q": "向量数据库在 RAG 中的作用是什么", "expect": ["RAG"]},
    # 离散数学
    {"q": "命题逻辑中的蕴含关系怎么理解", "expect": ["离散数学"]},
    {"q": "集合的运算有哪些", "expect": ["离散数学"]},
]

# 负例：知识库不应命中的问题（测试误报率）
NEGATIVE_QUESTIONS: list[str] = [
    "附近有什么好吃的川菜馆",
    "今天中午吃什么比较健康",
    "怎么办理校园卡",
    "推荐一本言情小说",
    "明天会下雨吗",
]


def _hit(result_title: str, result_topic: str, expect: list[str]) -> bool:
    title = (result_title or "").lower()
    topic = (result_topic or "").lower()
    return any(
        kw.lower() in title or kw.lower() in topic for kw in expect if kw.strip()
    )


def run_eval(embedding: str, top_k: int = 5, write_report: bool = True) -> dict:
    if embedding == "hash":
        service = SQLiteRAGService(embedder=HashEmbeddingService(), search_mode="lexical")
    else:
        service = SQLiteRAGService(embedder=FastEmbeddingService(), search_mode="hybrid")
    db = SessionLocal()
    try:
        rows = []
        t0 = time.time()
        for item in EVAL_QUESTIONS:
            results = service.search(db, item["q"], top_k=top_k)
            hit_rank: int | None = None
            for i, r in enumerate(results):
                if _hit(r.document_title, r.topic, item["expect"]):
                    hit_rank = i + 1
                    break
            ctx = service.retrieve_context(db, item["q"], top_k=top_k)
            top = results[0] if results else None
            rows.append(
                {
                    "question": item["q"],
                    "expect": item["expect"][0],
                    "hit_rank": hit_rank,
                    "hit@1": hit_rank == 1,
                    "hit@3": hit_rank is not None and hit_rank <= 3,
                    "hit@5": hit_rank is not None and hit_rank <= 5,
                    "top_doc": top.document_title if top else "",
                    "top_topic": top.topic if top else "",
                    "top_score": top.score if top else 0.0,
                    "top_source_level": top.metadata.get("source_level", "") if top else "",
                    "grounded": bool(ctx.get("grounded")),
                }
            )
        neg_rows = []
        for q in NEGATIVE_QUESTIONS:
            results = service.search(db, q, top_k=top_k)
            ctx = service.retrieve_context(db, q, top_k=top_k)
            neg_rows.append(
                {
                    "question": q,
                    "hits": len(results),
                    "top_doc": results[0].document_title if results else "",
                    "top_score": results[0].score if results else 0.0,
                    "grounded": bool(ctx.get("grounded")),
                }
            )
    finally:
        db.close()

    n = len(rows)
    agg = {
        "total": n,
        "hit@1": round(sum(r["hit@1"] for r in rows) / n, 3),
        "hit@3": round(sum(r["hit@3"] for r in rows) / n, 3),
        "hit@5": round(sum(r["hit@5"] for r in rows) / n, 3),
        "recall_top5": round(sum(r["hit@5"] for r in rows) / n, 3),
        "avg_score_hits": round(
            sum(r["top_score"] for r in rows if r["hit_rank"] is not None)
            / max(1, sum(1 for r in rows if r["hit_rank"] is not None)),
            3,
        ),
        "grounded_rate": round(sum(r["grounded"] for r in rows) / n, 3),
        "miss_count": sum(1 for r in rows if r["hit_rank"] is None),
        "false_grounding": sum(1 for r in neg_rows if r["grounded"]),
        "false_hits": sum(1 for r in neg_rows if r["hits"] > 0),
        "source_levels": {},
    }
    for r in rows:
        if r["top_source_level"]:
            agg["source_levels"][r["top_source_level"]] = (
                agg["source_levels"].get(r["top_source_level"], 0) + 1
            )
    elapsed = round(time.time() - t0, 1)

    print("=" * 70)
    print(f"RAG 评测 · embedding={embedding} · search_mode={service.search_mode}")
    print(f"耗时 {elapsed}s · 正例 {n} 道 · 负例 {len(neg_rows)} 道")
    print(f"  Recall@1 = {agg['hit@1']:.1%}   Recall@3 = {agg['hit@3']:.1%}   Recall@5 = {agg['hit@5']:.1%}")
    print(f"  平均命中相似度 = {agg['avg_score_hits']}   grounded 率 = {agg['grounded_rate']:.1%}")
    print(f"  未命中 = {agg['miss_count']}  负例误报 = {agg['false_hits']}  负例误 grounded = {agg['false_grounding']}")
    print(f"  来源等级分布 = {agg['source_levels']}")
    for r in rows:
        flag = "✓" if r["hit_rank"] is not None else "✗"
        print(f"  {flag} [{r['hit_rank'] or '-'}] {r['question']} -> {r['top_doc'][:40]} ({r['top_score']})")
    print("=" * 70)

    if write_report:
        _write_report(embedding, service.search_mode, agg, rows, neg_rows, elapsed)
    return {"aggregate": agg, "rows": rows, "negatives": neg_rows}


def _write_report(
    embedding: str,
    search_mode: str,
    agg: dict,
    rows: list[dict],
    neg_rows: list[dict],
    elapsed: float,
) -> None:
    docs_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RAG 检索评测报告",
        "",
        f"> 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 环境：embedding=`{embedding}` · search_mode=`{search_mode}` · 知识库切片来自 SQLite",
        "",
        "## 一、总体指标",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
        f"| 正例问题数 | {agg['total']} |",
        f"| Recall@1 | {agg['hit@1']:.1%} |",
        f"| Recall@3 | {agg['hit@3']:.1%} |",
        f"| Recall@5 | {agg['hit@5']:.1%} |",
        f"| 命中问题平均相似度 | {agg['avg_score_hits']} |",
        f"| 命中判定 grounded 率 | {agg['grounded_rate']:.1%} |",
        f"| 未命中数 | {agg['miss_count']} |",
        f"| 负例误报数 | {agg['false_hits']} |",
        f"| 负例误 grounded 数 | {agg['false_grounding']} |",
        f"| 评测耗时 | {elapsed}s |",
        "",
        "## 二、来源等级分布（Top1 命中的来源等级）",
        "",
        "| 来源等级 | 次数 |",
        "| --- | --- |",
    ]
    for level, cnt in sorted(agg["source_levels"].items()):
        lines.append(f"| {level} | {cnt} |")
    lines += [
        "",
        "## 三、逐题结果",
        "",
        "| # | 问题 | 期望文档 | 命中位置 | Top1 文档 | Top1 相似度 | grounded |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"| {i} | {r['question']} | {r['expect']} | "
            f"{r['hit_rank'] or '未命中'} | {r['top_doc']} | {r['top_score']} | {r['grounded']} |"
        )
    lines += ["", "## 四、负例（不应命中）", "", "| 问题 | 命中数 | Top1 文档 | Top1 相似度 | grounded |", "| --- | --- | --- | --- | --- |"]
    for r in neg_rows:
        lines.append(
            f"| {r['question']} | {r['hits']} | {r['top_doc']} | {r['top_score']} | {r['grounded']} |"
        )
    lines += [
        "",
        "## 五、说明",
        "",
        "- Recall@k：期望文档出现在前 k 条检索结果中的比例（按文档标题/主题关键词判定）。",
        "- grounded：`retrieve_context` 判定命中知识库（Top1 相似度 ≥ 阈值）。",
        "- 混合模式下相似度为 0.55×语义余弦 + 0.45×归一化词法余弦 + 关键词重叠奖励。",
        "",
    ]
    (docs_dir / "RAG_EVAL_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"报告已写入 {docs_dir / 'RAG_EVAL_REPORT.md'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG 检索评测")
    parser.add_argument("--embedding", choices=["auto", "fastembed", "hash"], default="auto")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--no-report", action="store_true")
    args = parser.parse_args()
    run_eval(embedding=args.embedding, top_k=args.top_k, write_report=not args.no_report)


if __name__ == "__main__":
    main()
