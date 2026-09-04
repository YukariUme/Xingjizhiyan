"""科研模块路由：工作台、论文阅读、前沿探索（数据默认用户私有）。"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import PaperReading, ResearchTopic, User
from app.repositories.research_repo import ResearchRepository
from app.services.activity_service import ActivityService
from app.services.agent.factory import get_agent_service
from app.services.llm.factory import get_llm_service
from app.services.rag.factory import get_rag_service
from app.services.research_hotspots import get_hotspot_service


def _parse_json(raw: str) -> dict:
    import json
    import re

    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}

router = APIRouter(prefix="/api/research", tags=["research"])


def _paper_out(db: Session, paper, user: User) -> dict:
    reading = ResearchRepository.get_reading(db, user.id, paper.id)
    return {
        "id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "abstract": paper.abstract,
        "venue": paper.venue,
        "year": paper.year,
        "topics": paper.topics,
        "keywords": paper.keywords,
        "citations": paper.citations,
        "url": paper.url,
        "is_hot": paper.is_hot,
        "status": reading.status if reading else "",
        "progress": reading.progress if reading else 0,
    }


@router.get("/workbench")
def workbench(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    topics = ResearchRepository.list_topics(db, user.id)
    readings = ResearchRepository.list_readings(db, user.id)
    read_ids = [r.paper_id for r in readings]
    favorites = [
        _paper_out(db, ResearchRepository.get_paper(db, r.paper_id), user)
        for r in readings
        if r.status == "favorite" and ResearchRepository.get_paper(db, r.paper_id)
    ]
    recent = [
        _paper_out(db, ResearchRepository.get_paper(db, r.paper_id), user)
        for r in readings[:5]
        if ResearchRepository.get_paper(db, r.paper_id)
    ]
    papers = ResearchRepository.list_papers(db, limit=20)
    recommended = [
        _paper_out(db, p, user)
        for p in papers
        if p.is_hot and p.id not in read_ids
    ][:6]
    return {
        "topics": [
            {"id": t.id, "name": t.name, "description": t.description}
            for t in topics
        ],
        "recent_papers": recent,
        "recommended_papers": recommended,
        "favorite_papers": favorites,
        "reading_records": [
            {
                "paper_id": r.paper_id,
                "status": r.status,
                "progress": r.progress,
                "last_read_at": r.last_read_at.isoformat(),
            }
            for r in readings
        ],
    }


@router.get("/papers")
def list_papers(
    q: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    papers = ResearchRepository.search_papers(db, q) if q else ResearchRepository.list_papers(db)
    return [_paper_out(db, p, user) for p in papers]


@router.get("/papers/{paper_id}")
def get_paper(
    paper_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    paper = ResearchRepository.get_paper(db, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    out = _paper_out(db, paper, user)
    out["content"] = paper.content
    out["knowledge_point_ids"] = paper.knowledge_point_ids
    return out


@router.post("/papers/{paper_id}/analyze")
def analyze_paper(
    paper_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """论文阅读助手：结构化拆解 + 引用来源 + 知识点关联。"""
    if not ResearchRepository.get_paper(db, paper_id):
        raise HTTPException(status_code=404, detail="论文不存在")
    agent = get_agent_service("research")
    result = agent.run(db, user, {"task": "analyze", "paper_id": paper_id})
    reading = ResearchRepository.get_reading(db, user.id, paper_id)
    if not reading:
        reading = PaperReading(user_id=user.id, paper_id=paper_id, status="reading", progress=50)
    else:
        reading.progress = min(100, reading.progress + 10)
        reading.status = reading.status or "reading"
    ResearchRepository.save_reading(db, reading)
    ActivityService.log(
        db,
        user,
        "paper_analyze",
        f"AI 阅读论文：{result.get('title', '')[:40]}",
        {"paper_id": paper_id},
    )
    return result


@router.post("/papers/{paper_id}/reading")
def update_reading(
    paper_id: int,
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    reading = ResearchRepository.get_reading(db, user.id, paper_id)
    if not reading:
        reading = PaperReading(user_id=user.id, paper_id=paper_id)
    if "status" in data:
        reading.status = data["status"]
    if "progress" in data:
        reading.progress = max(0, min(100, int(data["progress"])))
    ResearchRepository.save_reading(db, reading)
    return {"ok": True, "status": reading.status, "progress": reading.progress}


@router.post("/topics")
def create_topic(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    topic = ResearchTopic(
        owner_id=user.id,
        name=data.get("name", "").strip(),
        description=data.get("description", ""),
    )
    if not topic.name:
        raise HTTPException(status_code=400, detail="研究方向名称不能为空")
    saved = ResearchRepository.create_topic(db, topic)
    return {"id": saved.id, "name": saved.name, "description": saved.description}


@router.get("/topics")
def list_topics(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return [
        {"id": t.id, "name": t.name, "description": t.description}
        for t in ResearchRepository.list_topics(db, user.id)
    ]


@router.post("/explore")
def explore(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """科研前沿探索：输入主题，返回方向、论文、热点、方法分类与时间趋势。"""
    topic = (data.get("topic") or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="请输入研究主题")
    agent = get_agent_service("research")
    result = agent.run(db, user, {"task": "explore", "topic": topic})
    ActivityService.log(
        db,
        user,
        "frontier",
        f"前沿探索：{topic}",
        {"directions": len(result.get("directions", []))},
    )
    return result


@router.get("/hotspots/directions")
def hotspot_directions(user: User = Depends(get_current_user)) -> list[dict]:
    """科研前沿热点：可选研究方向列表（内置多元化 CS/AI 领域，秒回）。"""
    return get_hotspot_service().list_directions()


@router.get("/hotspots")
def hotspots(
    direction: str = "llm_agents",
    user: User = Depends(get_current_user),
) -> dict:
    """指定方向的热点论文：精选会议论文 + arXiv 最新（缓存秒回，后台刷新）。"""
    try:
        return get_hotspot_service().get_hotspots(direction)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/compare")
def compare_papers(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """论文对比：选择多篇论文，AI 生成研究问题/方法/数据/指标/结果/局限的结构化对比表。"""
    paper_ids = data.get("paper_ids") or []
    papers = [ResearchRepository.get_paper(db, pid) for pid in paper_ids[:5]]
    papers = [p for p in papers if p]
    if len(papers) < 2:
        raise HTTPException(status_code=400, detail="请至少选择 2 篇论文")
    lines = [
        f"论文{i + 1}《{p.title}》——{p.abstract[:160]}"
        for i, p in enumerate(papers)
    ]
    prompt = (
        "[论文对比任务]\n论文列表：\n" + "\n".join(lines) +
        "\n请输出 JSON，字段：rows（对比行数组，每项含 dimension 与 cells 数组，"
        "cells 长度与论文数一致）、summary（总结）。维度至少包含：研究问题、方法、数据集、指标、实验结果、局限性。"
    )
    raw = get_llm_service().generate(prompt, system="你是科研论文对比助手，输出结构化 JSON。")
    parsed = _parse_json(raw)
    # 归一化：LLM 可能把对比格返回成对象/嵌套结构，统一转字符串
    from app.services.agent.teaching import _as_text

    raw_rows = parsed.get("rows")
    rows = []
    for row in raw_rows if isinstance(raw_rows, list) else []:
        if not isinstance(row, dict):
            continue
        cells = row.get("cells")
        rows.append(
            {
                "dimension": _as_text(row.get("dimension")),
                "cells": [_as_text(c) for c in (cells if isinstance(cells, list) else [])],
            }
        )
    return {
        "papers": [
            {"id": p.id, "title": p.title, "venue": p.venue, "year": p.year}
            for p in papers
        ],
        "rows": [r for r in rows if r["dimension"]],
        "summary": _as_text(parsed.get("summary")),
        "ai_generated": True,
        "ai_label": "AI 生成",
        "provider": get_llm_service().name,
    }


@router.get("/documents")
def list_research_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    from app.models import ResearchDocument

    rows = (
        db.query(ResearchDocument)
        .filter(ResearchDocument.owner_id == user.id)
        .order_by(ResearchDocument.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "source": r.source,
            "paper_id": r.paper_id,
            "course_id": r.course_id,
            "visibility": r.visibility,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/profile")
def research_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """研究方向画像：主题、阅读/收藏统计、关注方向与推荐论文数。"""
    topics = ResearchRepository.list_topics(db, user.id)
    readings = ResearchRepository.list_readings(db, user.id)
    favorites = [r for r in readings if r.status == "favorite"]
    read_paper_ids = {r.paper_id for r in readings}
    papers = ResearchRepository.list_papers(db, limit=50)
    unread_hot = [p for p in papers if p.is_hot and p.id not in read_paper_ids][:6]
    venues: dict[str, int] = {}
    for r in readings:
        paper = ResearchRepository.get_paper(db, r.paper_id)
        if paper and paper.venue:
            venues[paper.venue] = venues.get(paper.venue, 0) + 1
    return {
        "topics": [
            {"id": t.id, "name": t.name, "description": t.description}
            for t in topics
        ],
        "reading_count": len(readings),
        "favorite_count": len(favorites),
        "top_venues": sorted(venues.items(), key=lambda x: -x[1])[:5],
        "recommended_papers": [
            {"id": p.id, "title": p.title, "year": p.year, "venue": p.venue}
            for p in unread_hot
        ],
    }


@router.get("/by-knowledge-point")
def papers_by_knowledge_point(
    kp_id: int,
    course_id: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """课程知识点 → 相关论文（可解释：命中知识点/主题重叠），并记录“深入研究”链路。"""
    from app.models import KnowledgePoint

    kp = db.get(KnowledgePoint, kp_id)
    if not kp:
        raise HTTPException(status_code=404, detail="知识点不存在")
    papers = ResearchRepository.list_papers(db, limit=60)
    matched = []
    for p in papers:
        reasons = []
        if kp.id in [int(x) for x in (p.knowledge_point_ids or [])]:
            reasons.append("论文显式关联该知识点")
        topic_hit = [t for t in (p.topics or []) if any(
            kw in t for kw in (kp.name[:4], kp.name)
        )]
        if topic_hit:
            reasons.append(f"研究主题与知识点重叠：{topic_hit[0]}")
        if reasons:
            matched.append(
                {
                    "id": p.id,
                    "title": p.title,
                    "year": p.year,
                    "venue": p.venue,
                    "citations": p.citations,
                    "reasons": reasons,
                }
            )
    matched.sort(key=lambda x: (-len(x["reasons"]), -x["citations"]))
    # 链路统计：深入研究/回到课程知识
    from app.services.activity_service import ActivityService

    ActivityService.log(
        db,
        user,
        "research_from_kp",
        f"从课程知识点「{kp.name}」进入研究空间",
        {"kp_id": kp.id, "course_id": course_id, "matched": len(matched)},
    )
    return {
        "knowledge_point": {"id": kp.id, "name": kp.name, "course": kp.subject},
        "papers": matched[:10],
        "total": len(matched),
    }


@router.post("/documents/upload")
async def upload_research_document(
    file: UploadFile = File(...),
    title: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """上传科研资料（论文 PDF 等，默认仅自己可见）。"""
    import uuid
    from pathlib import Path

    from app.config import get_settings
    from app.models import ResearchDocument

    filename = file.filename or "未命名资料"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in {"txt", "md", "markdown", "pdf", "ppt", "pptx", "doc", "docx"}:
        raise HTTPException(
            status_code=400,
            detail="仅支持 txt / md / pdf / pptx / docx 文件",
        )
    folder = Path(get_settings().knowledge_files_dir) / "_research"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}.{ext}"
    from app.services.knowledge_service import validate_upload_header

    head = await file.read(16)
    await file.seek(0)
    try:
        validate_upload_header(filename, head)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    with path.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            if path.stat().st_size > 80 * 1024 * 1024:
                path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="资料超过 80MB 限制")
            out.write(chunk)
    doc = ResearchDocument(
        owner_id=user.id,
        title=title or filename,
        file_path=str(path),
        source=filename,
        visibility="private",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"ok": True, "document_id": doc.id, "title": doc.title}
