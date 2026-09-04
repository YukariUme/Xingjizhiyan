"""科研前沿热点测试：方向列表、精选回退、arXiv Atom 解析、API 秒回。"""

import pytest

from app.services.research_hotspots import (
    HotspotService,
    get_hotspot_service,
)

SAMPLE_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <title>Sample LLM Agent Paper</title>
    <published>2024-01-01T00:00:00Z</published>
    <author><name>Alice Zhang</name></author>
    <author><name>Bob Li</name></author>
    <summary>This is a short sample abstract about agents.</summary>
    <arxiv:primary_category term="cs.CL"/>
  </entry>
</feed>
"""


def test_directions_are_diverse():
    """方向列表多元化：至少 12 个 CS/AI 领域，字段完整。"""
    service = get_hotspot_service()
    directions = service.list_directions()
    assert len(directions) >= 12
    ids = {d["id"] for d in directions}
    assert {"llm_agents", "reinforcement_learning", "ai_infra", "distributed_systems"} <= ids
    for d in directions:
        assert d["id"] and d["name"] and d["label"] and d["description"]
        assert d["venues"]


def test_get_hotspots_instant_curated():
    """arXiv 不可用时：请求立即返回精选论文（不阻塞、不报错）。"""
    service = HotspotService()
    data = service.get_hotspots("llm_agents")
    assert data["source"] == "curated"
    assert data["direction"]["id"] == "llm_agents"
    assert data["papers"]
    assert all(p["url"].startswith("http") for p in data["papers"])


def test_refresh_merges_arxiv_papers(monkeypatch):
    """后台刷新成功后：arXiv 最新论文排在精选论文之前。"""
    service = HotspotService()

    def fake_fetch(direction, limit=None):
        return [
            {
                "title": "Dynamic Paper 2026",
                "url": "https://arxiv.org/abs/2601.99999",
                "authors": ["Alice"],
                "year": 2026,
                "venue": "arXiv cs.CL",
                "summary": "latest",
                "source": "arxiv",
                "tag": "arXiv 最新",
            }
        ]

    monkeypatch.setattr(service, "_fetch_arxiv", fake_fetch)
    service._refresh("llm_agents")
    data = service.get_hotspots("llm_agents")
    assert data["source"] == "arxiv"
    assert data["papers"][0]["title"] == "Dynamic Paper 2026"
    assert any(p["tag"] == "经典会议论文" for p in data["papers"])


def test_parse_atom():
    """arXiv Atom XML → 论文字典。"""
    papers = HotspotService._parse_atom(SAMPLE_ATOM)
    assert len(papers) == 1
    p = papers[0]
    assert p["title"] == "Sample LLM Agent Paper"
    assert p["url"] == "http://arxiv.org/abs/2401.00001v1"
    assert p["year"] == 2024
    assert p["authors"] == ["Alice Zhang", "Bob Li"]
    assert "arXiv cs.CL" in p["venue"]
    assert p["source"] == "arxiv"


def test_unknown_direction_raises():
    service = HotspotService()
    with pytest.raises(KeyError):
        service.get_hotspots("not_a_direction")


def test_api_hotspots(client, teacher):
    """API：方向列表与热点详情均秒回且带可点击论文。"""
    headers = {"Authorization": f"Bearer {teacher['token']}"}
    r = client.get("/api/research/hotspots/directions", headers=headers)
    assert r.status_code == 200
    directions = r.json()
    assert len(directions) >= 12

    r2 = client.get(f"/api/research/hotspots?direction={directions[0]['id']}", headers=headers)
    assert r2.status_code == 200
    data = r2.json()
    assert data["papers"]
    assert all(p["url"].startswith("http") for p in data["papers"])
