"""科研前沿热点服务：多元方向 + 代表论文 + arXiv 实时更新。

设计目标（响应 < 5s）：
1. 方向列表与说明为内置静态数据，秒回；
2. 论文 = 精选国际会议/期刊代表论文（curated，链接可点）
   + arXiv API 按分类拉取的最新论文（dynamic）；
3. 缓存 TTL（默认 6 小时）+ 后台线程刷新：请求先返回缓存/精选，
   过期时后台异步抓 arXiv，绝不阻塞请求；arXiv 不可用自动回退精选。
"""

import logging
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

ARXIV_API = "https://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


@dataclass
class HotspotPaper:
    title: str
    url: str
    authors: list[str] = field(default_factory=list)
    year: int = 0
    venue: str = ""
    summary: str = ""
    source: str = "curated"  # curated | arxiv
    tag: str = ""  # 最新 / 经典会议论文

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "summary": self.summary,
            "source": self.source,
            "tag": self.tag,
        }


@dataclass
class HotspotDirection:
    id: str
    name: str
    label: str  # 中文名（按钮）
    description: str
    arxiv_query: str
    venues: list[str] = field(default_factory=list)
    papers: list[HotspotPaper] = field(default_factory=list)

    def to_dict(self, include_papers: bool = True) -> dict:
        base = {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "venues": self.venues,
        }
        if include_papers:
            base["papers"] = [p.to_dict() for p in self.papers]
        return base


# ---------------------------------------------------------------------------
# 方向定义（多元 CS/AI 领域，按钮来自这里）
# ---------------------------------------------------------------------------
def _p(title: str, url: str, year: int, venue: str, summary: str, authors: list[str] | None = None) -> HotspotPaper:
    return HotspotPaper(
        title=title,
        url=url,
        year=year,
        venue=venue,
        summary=summary,
        source="curated",
        tag="经典会议论文",
        authors=authors or [],
    )


DIRECTIONS: list[HotspotDirection] = [
    HotspotDirection(
        id="llm_agents",
        name="LLM Agents",
        label="大模型智能体",
        description="研究大语言模型驱动的自主智能体：工具调用、多步规划、多智能体协作与长程任务执行，是当前 AI 最活跃的方向之一。",
        arxiv_query="cat:cs.AI+AND+cat:cs.CL",
        venues=["NeurIPS", "ICML", "ICLR", "ACL", "AAAI"],
        papers=[
            _p("ReAct: Synergizing Reasoning and Acting in Language Models", "https://arxiv.org/abs/2210.03629", 2022, "ICLR 2023", "让 LLM 交替进行推理轨迹与行动，显著提升可控性与可解释性。"),
            _p("Toolformer: Language Models Can Teach Themselves to Use Tools", "https://arxiv.org/abs/2302.04761", 2023, "NeurIPS 2023", "自监督教会模型在合适位置调用外部工具（搜索/计算器/翻译）。"),
            _p("HuggingGPT: Solving AI Tasks with ChatGPT and its Friends in Hugging Face", "https://arxiv.org/abs/2303.17580", 2023, "arXiv", "以 ChatGPT 为控制器编排多个专业模型协作完成任务。"),
        ],
    ),
    HotspotDirection(
        id="reinforcement_learning",
        name="Reinforcement Learning",
        label="强化学习",
        description="从序列决策到离线强化学习、RLHF 与大模型对齐，强化学习正在与 LLM、机器人深度融合。",
        arxiv_query="cat:cs.LG+AND+cat:cs.AI",
        venues=["NeurIPS", "ICML", "ICLR", "AAMAS"],
        papers=[
            _p("Human-level control through deep reinforcement learning", "https://www.nature.com/articles/nature14236", 2015, "Nature", "DQN 首次在 Atari 上达到人类水平，开启深度强化学习时代。"),
            _p("Proximal Policy Optimization Algorithms", "https://arxiv.org/abs/1707.06347", 2017, "arXiv", "PPO：稳定高效的策略优化算法，OpenAI 等广泛使用。"),
            _p("Mastering the game of Go with deep neural networks and tree search", "https://www.nature.com/articles/nature16961", 2016, "Nature", "AlphaGo 结合深度网络与蒙特卡洛树搜索战胜人类棋手。"),
        ],
    ),
    HotspotDirection(
        id="ai_infra",
        name="AI Infrastructure",
        label="AI 基础设施",
        description="面向大模型的训练与推理基础设施：分布式训练框架、推理加速、调度与容错，是支撑大模型落地的关键工程方向。",
        arxiv_query="cat:cs.DC+AND+cat:cs.LG",
        venues=["OSDI", "NSDI", "MLSys", "SOSP", "EuroSys"],
        papers=[
            _p("vLLM: Easy, Fast, and Cheap LLM Serving with PagedAttention", "https://arxiv.org/abs/2309.06180", 2023, "SOSP 2023", "PagedAttention 显存分页管理，吞吐提升 2-4 倍。"),
            _p("Ray: A Distributed Framework for Emerging AI Applications", "https://arxiv.org/abs/1712.05889", 2017, "OSDI 2018", "统一分布式执行引擎，支撑强化学习与超参数搜索。"),
            _p("Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism", "https://arxiv.org/abs/1909.08053", 2019, "arXiv", "张量并行训练数十亿参数语言模型。"),
        ],
    ),
    HotspotDirection(
        id="distributed_systems",
        name="Distributed Systems",
        label="分布式系统",
        description="一致性、共识、容错与大规模存储：从数据中心到跨地域部署的系统设计。",
        arxiv_query="cat:cs.DC",
        venues=["OSDI", "SOSP", "NSDI", "SIGMOD", "USENIX ATC"],
        papers=[
            _p("MapReduce: Simplified Data Processing on Large Clusters", "https://research.google/pubs/pub62/", 2004, "OSDI 2004", "开创大规模数据并行处理范式的经典论文。"),
            _p("Spanner: Google's Globally-Distributed Database", "https://research.google/pubs/pub39966/", 2012, "OSDI 2012", "全球分布式数据库，TrueTime 实现外部一致性。"),
            _p("ZooKeeper: Wait-free Coordination for Internet-scale Systems", "https://www.usenix.org/conference/atc10/zookeeper-wait-free-coordination-internet-scale-systems", 2010, "USENIX ATC 2010", "分布式协调服务，广泛用于服务发现与配置管理。"),
        ],
    ),
    HotspotDirection(
        id="llm",
        name="Large Language Models",
        label="大语言模型",
        description="Transformer 架构、预训练、对齐（RLHF/DPO）与评测：大语言模型的技术全栈与前沿问题。",
        arxiv_query="cat:cs.CL+AND+cat:cs.LG",
        venues=["NeurIPS", "ICML", "ICLR", "ACL", "EMNLP"],
        papers=[
            _p("Attention Is All You Need", "https://arxiv.org/abs/1706.03762", 2017, "NeurIPS 2017", "Transformer 架构：自注意力取代循环，成为大模型基石。"),
            _p("BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding", "https://arxiv.org/abs/1810.04805", 2018, "NAACL 2019", "双向预训练语言模型，刷新多项 NLP 基准。"),
            _p("Training language models to follow instructions with human feedback", "https://arxiv.org/abs/2203.02155", 2022, "NeurIPS 2022", "InstructGPT：RLHF 让模型对齐人类指令。"),
        ],
    ),
    HotspotDirection(
        id="multimodal",
        name="Multimodal Learning",
        label="多模态学习",
        description="视觉-语言-音频统一建模：对比学习、指令微调与多模态大模型。",
        arxiv_query="cat:cs.CV+AND+cat:cs.CL",
        venues=["CVPR", "ICCV", "NeurIPS", "ICML"],
        papers=[
            _p("Learning Transferable Visual Models From Natural Language Supervision", "https://arxiv.org/abs/2103.00020", 2021, "ICML 2021", "CLIP：图文对比学习，零样本迁移。"),
            _p("Visual Instruction Tuning", "https://arxiv.org/abs/2304.08485", 2023, "NeurIPS 2023", "LLaVA：视觉指令微调，多模态对话。"),
            _p("Flamingo: a Visual Language Model for Few-Shot Learning", "https://arxiv.org/abs/2204.14198", 2022, "NeurIPS 2022", "冻结大模型 + 视觉适配器实现少样本多模态理解。"),
        ],
    ),
    HotspotDirection(
        id="computer_vision",
        name="Computer Vision",
        label="计算机视觉",
        description="图像分类、目标检测、分割与生成：CNN 到 ViT 再到视觉基础模型。",
        arxiv_query="cat:cs.CV",
        venues=["CVPR", "ICCV", "ECCV", "NeurIPS"],
        papers=[
            _p("Deep Residual Learning for Image Recognition", "https://arxiv.org/abs/1512.03385", 2015, "CVPR 2016", "ResNet：残差连接解决深层网络退化。"),
            _p("An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale", "https://arxiv.org/abs/2010.11929", 2020, "ICLR 2021", "ViT：纯 Transformer 视觉分类。"),
            _p("Segment Anything", "https://arxiv.org/abs/2304.02643", 2023, "ICCV 2023", "SAM：可提示分割基础模型。"),
        ],
    ),
    HotspotDirection(
        id="graph_learning",
        name="Graph Representation Learning",
        label="图表示学习",
        description="图神经网络、图预训练与知识图谱推理，面向关系数据建模。",
        arxiv_query="cat:cs.LG+AND+cat:cs.SI",
        venues=["NeurIPS", "ICML", "ICLR", "KDD", "WWW"],
        papers=[
            _p("Semi-Supervised Classification with Graph Convolutional Networks", "https://arxiv.org/abs/1609.02907", 2016, "ICLR 2017", "GCN：一阶邻居聚合的半监督图分类。"),
            _p("Inductive Representation Learning on Large Graphs", "https://arxiv.org/abs/1706.02216", 2017, "NeurIPS 2017", "GraphSAGE：归纳式节点表示学习。"),
            _p("Graph Attention Networks", "https://arxiv.org/abs/1710.10903", 2017, "ICLR 2018", "GAT：注意力机制加权邻居聚合。"),
        ],
    ),
    HotspotDirection(
        id="database",
        name="Database Systems",
        label="数据库系统",
        description="云原生数据库、查询优化、向量检索与数据湖仓：从单机到分布式与智能化。",
        arxiv_query="cat:cs.DB",
        venues=["SIGMOD", "VLDB", "ICDE", "CIDR"],
        papers=[
            _p("Amazon Aurora: Design Considerations for High Throughput Cloud-Native Relational Databases", "https://dl.acm.org/doi/10.1145/3035918.3056101", 2017, "SIGMOD 2017", "云原生关系数据库的存储与计算分离设计。"),
            _p("CockroachDB: The Resilient Geo-Distributed SQL Database", "https://dl.acm.org/doi/10.1145/3318464.3386134", 2020, "SIGMOD 2020", "基于 Raft 的地理分布式 SQL 数据库。"),
            _p("Presto: SQL on Everything", "https://research.varada.com/wp-content/uploads/2019/01/Presto_SQL_on_Everything.pdf", 2019, "CIDR 2019", "开源分布式 SQL 查询引擎。"),
        ],
    ),
    HotspotDirection(
        id="security",
        name="System & Network Security",
        label="系统与网络安全",
        description="侧信道攻击、AI 安全、隐私保护与可信计算：安全与机器学习的交叉前沿。",
        arxiv_query="cat:cs.CR",
        venues=["S&P", "USENIX Security", "CCS", "NDSS"],
        papers=[
            _p("Spectre Attacks: Exploiting Speculative Execution", "https://arxiv.org/abs/1801.01203", 2018, "S&P 2019", "利用推测执行泄露内核内存的侧信道攻击。"),
            _p("Meltdown: Reading Kernel Memory from User Space", "https://arxiv.org/abs/1801.01207", 2018, "USENIX Security 2018", "利用乱序执行读取内核内存。"),
            _p("Adversarial Examples in the Physical World", "https://arxiv.org/abs/1607.02533", 2016, "ICLR 2017", "物理世界的对抗样本：AI 安全基础工作。"),
        ],
    ),
    HotspotDirection(
        id="hpc",
        name="High Performance Computing",
        label="高性能计算",
        description="大规模并行训练与科学计算：集合通信、混合并行与异构加速。",
        arxiv_query="cat:cs.DC+AND+cat:cs.PF",
        venues=["SC", "ICS", "PPoPP", "HPDC"],
        papers=[
            _p("Horovod: fast and easy distributed deep learning in TensorFlow", "https://arxiv.org/abs/1802.05799", 2018, "arXiv", "基于 AllReduce 的分布式训练框架。"),
            _p("TensorFlow: A system for large-scale machine learning", "https://arxiv.org/abs/1605.08695", 2016, "OSDI 2016", "大规模机器学习系统设计。"),
        ],
    ),
    HotspotDirection(
        id="edge_cloud",
        name="Edge & Cloud Computing",
        label="边缘与云计算",
        description="无服务器计算、边缘推理与资源调度：云边端协同的新范式。",
        arxiv_query="cat:cs.DC+AND+cat:cs.NI",
        venues=["NSDI", "SoCC", "ICDCS", "IEEE IoT-J"],
        papers=[
            _p("Edge Computing: Vision and Challenges", "https://ieeexplore.ieee.org/document/7488250", 2016, "IEEE IoT-J", "边缘计算愿景与挑战的开创性文章。"),
            _p("Serverless in the Wild: Characterizing and Optimizing the Serverless Workload at a Large Cloud Provider", "https://dl.acm.org/doi/10.1145/3377811.3380370", 2020, "ICSE 2020", "大规模无服务器工作负载特征分析。"),
            _p("Firecracker: Lightweight Virtualization for Serverless Applications", "https://www.usenix.org/conference/nsdi20/presentation/agache", 2020, "NSDI 2020", "无服务器场景的轻量虚拟化。"),
        ],
    ),
    HotspotDirection(
        id="quantum",
        name="Quantum Computing",
        label="量子计算",
        description="量子算法、量子机器学习和量子纠错：经典-量子混合计算探索。",
        arxiv_query="cat:quant-ph+AND+cat:cs.ET",
        venues=["Nature", "PRL", "Quantum", "TQC"],
        papers=[
            _p("Quantum supremacy using a programmable superconducting processor", "https://www.nature.com/articles/s41586-019-1666-5", 2019, "Nature", "谷歌 53 量子比特实现量子霸权实验。"),
            _p("A variational eigenvalue solver on a photonic quantum processor", "https://arxiv.org/abs/1304.3061", 2013, "Nature Communications", "变分量子本征求解器 VQE 原型。"),
        ],
    ),
    HotspotDirection(
        id="federated_learning",
        name="Federated Learning & Privacy",
        label="联邦学习与隐私计算",
        description="数据不出域的训练范式：联邦优化、差分隐私与可信执行环境。",
        arxiv_query="cat:cs.LG+AND+cat:cs.CR",
        venues=["NeurIPS", "ICML", "CCS", "USENIX Security"],
        papers=[
            _p("Communication-Efficient Learning of Deep Networks from Decentralized Data", "https://arxiv.org/abs/1602.05629", 2016, "AISTATS 2017", "FedAvg：联邦平均算法开创性工作。"),
            _p("Federated Learning: Strategies for Improving Communication Efficiency", "https://arxiv.org/abs/1610.05492", 2016, "arXiv", "联邦学习的压缩与量化通信策略。"),
        ],
    ),
    HotspotDirection(
        id="code_intelligence",
        name="Code Intelligence",
        label="代码智能",
        description="代码生成、代码补全、程序修复与测试生成：大模型在软件工程中的应用。",
        arxiv_query="cat:cs.SE+AND+cat:cs.PL",
        venues=["ICSE", "FSE", "ASE", "PLDI", "ACL"],
        papers=[
            _p("CodeBERT: A Pre-Trained Model for Programming and Natural Languages", "https://arxiv.org/abs/2002.08155", 2020, "EMNLP 2020", "编程-自然语言双模态预训练。"),
            _p("Evaluating Large Language Models Trained on Code", "https://arxiv.org/abs/2107.03374", 2021, "arXiv", "Codex：代码大模型与 HumanEval 基准。"),
            _p("Competition-Level Code Generation with AlphaCode", "https://arxiv.org/abs/2203.07814", 2022, "Science", "AlphaCode：竞赛级代码生成。"),
        ],
    ),
    HotspotDirection(
        id="robotics",
        name="Robot Learning",
        label="机器人学习",
        description="具身智能：视觉-语言-动作模型、模仿学习与强化学习在机器人上的结合。",
        arxiv_query="cat:cs.RO+AND+cat:cs.LG",
        venues=["CoRL", "ICRA", "IROS", "RSS"],
        papers=[
            _p("RT-1: Robotics Transformer for Real-World Control at Scale", "https://arxiv.org/abs/2212.06817", 2022, "arXiv", "RT-1：机器人 Transformer 大规模真实控制。"),
            _p("Learning to Walk in Minutes Using Massively Parallel Deep Reinforcement Learning", "https://arxiv.org/abs/2109.03579", 2021, "CoRL 2021", "Isaac Gym 大规模并行训练机器人行走。"),
        ],
    ),
]

_DIRECTION_MAP = {d.id: d for d in DIRECTIONS}


# ---------------------------------------------------------------------------
# 服务
# ---------------------------------------------------------------------------
class HotspotService:
    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}
        self._lock = threading.Lock()

    def list_directions(self) -> list[dict]:
        return [d.to_dict(include_papers=False) for d in DIRECTIONS]

    def get_hotspots(self, direction_id: str) -> dict:
        direction = _DIRECTION_MAP.get(direction_id)
        if not direction:
            raise KeyError(f"未知方向：{direction_id}")
        settings = get_settings()
        ttl = settings.hotspot_ttl_hours * 3600
        with self._lock:
            data = self._cache.get(direction_id)
            stale = data is None or time.time() - data["fetched_at"] > ttl
        if data is None:
            data = self._seed_payload(direction)
            with self._lock:
                self._cache[direction_id] = data
        if stale:
            # 后台异步刷新：当前请求立即返回缓存/精选，绝不阻塞
            threading.Thread(
                target=self._refresh,
                args=(direction_id,),
                daemon=True,
                name=f"hotspot-{direction_id}",
            ).start()
        return {k: v for k, v in data.items() if k != "fetched_at"}

    # ---------- 数据组装 ----------
    def _seed_payload(self, direction: HotspotDirection) -> dict:
        return {
            "direction": direction.to_dict(include_papers=False),
            "papers": [p.to_dict() for p in direction.papers],
            "updated_at": _now_iso(),
            "source": "curated",
            "refresh_hours": get_settings().hotspot_ttl_hours,
            "note": "精选国际会议/期刊代表论文；arXiv 实时数据加载中。",
            "fetched_at": time.time(),
        }

    def _refresh(self, direction_id: str) -> None:
        direction = _DIRECTION_MAP.get(direction_id)
        if not direction:
            return
        try:
            latest = self._fetch_arxiv(direction)
            if not latest:
                return
            papers = latest + [p.to_dict() for p in direction.papers]
            payload = {
                "direction": direction.to_dict(include_papers=False),
                "papers": papers[: get_settings().hotspot_max_papers + 3],
                "updated_at": _now_iso(),
                "source": "arxiv",
                "refresh_hours": get_settings().hotspot_ttl_hours,
                "note": "实时热点来自 arXiv 最新提交（按方向分类，6 小时自动刷新）。",
                "fetched_at": time.time(),
            }
            with self._lock:
                self._cache[direction_id] = payload
            logger.info("热点已刷新：%s（%d 篇）", direction_id, len(papers))
        except Exception as exc:  # noqa: BLE001 - 后台刷新失败不影响服务
            logger.warning("热点刷新失败 %s：%s", direction_id, exc)

    # ---------- arXiv API ----------
    def _fetch_arxiv(self, direction: HotspotDirection, limit: int | None = None) -> list[dict]:
        settings = get_settings()
        params = {
            "search_query": direction.arxiv_query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "start": 0,
            "max_results": limit or settings.hotspot_max_papers,
        }
        url = f"{ARXIV_API}?{urlencode(params)}"
        resp = httpx.get(url, timeout=3.0, headers={"User-Agent": "jbgs-hotspot/1.0"})
        resp.raise_for_status()
        return self._parse_atom(resp.text)

    @staticmethod
    def _parse_atom(xml_text: str) -> list[dict]:
        root = ET.fromstring(xml_text)
        papers: list[dict] = []
        for entry in root.findall(f"{ATOM_NS}entry"):
            title = (entry.findtext(f"{ATOM_NS}title") or "").strip().replace("\n", " ").strip()
            link = entry.findtext(f"{ATOM_NS}id") or ""
            published = entry.findtext(f"{ATOM_NS}published") or ""
            year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else 0
            authors = [
                a.findtext(f"{ATOM_NS}name") or ""
                for a in entry.findall(f"{ATOM_NS}author")
            ]
            authors = [a for a in authors if a]
            summary = (entry.findtext(f"{ATOM_NS}summary") or "").strip()
            primary_el = entry.find(f"{ARXIV_NS}primary_category")
            primary = primary_el.get("term") if primary_el is not None else ""
            papers.append(
                HotspotPaper(
                    title=title,
                    url=link,
                    authors=authors[:4],
                    year=year,
                    venue=f"arXiv {primary}" if primary else "arXiv",
                    summary=summary[:220],
                    source="arxiv",
                    tag="arXiv 最新",
                ).to_dict()
            )
        return papers


_SERVICE: HotspotService | None = None


def get_hotspot_service() -> HotspotService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = HotspotService()
    return _SERVICE


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
