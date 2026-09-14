"""EPUB 文档解析：container.xml → OPF spine → XHTML/HTML 文本。"""

from __future__ import annotations

import html
import posixpath
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote
from xml.etree import ElementTree as ET

from app.services.parsing.blocks import BlockType, ParsedDocument, StructuredBlock
from app.services.parsing.code import detect_code_language, looks_like_code
from app.services.parsing.formula import FormulaExtractor


_HTML_MEDIA_TYPES = {
    "application/xhtml+xml",
    "text/html",
    "application/xml",
    "text/xml",
}

_BLOCK_TAGS = {
    "article",
    "aside",
    "blockquote",
    "div",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "li",
    "nav",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "thead",
    "tfoot",
    "tr",
}


def parse_epub(path: Path, progress=None) -> ParsedDocument:
    """解析 EPUB 为结构化块。"""
    if path.suffix.lower() != ".epub":
        raise ValueError(f"不是 EPUB 文件：{path.suffix}")
    if not zipfile.is_zipfile(path):
        raise ValueError("文件头无效：不是有效的 EPUB 文件")

    blocks: list[StructuredBlock] = []
    title = path.stem
    with zipfile.ZipFile(path) as zf:
        opf_path = _find_opf_path(zf)
        package = ET.fromstring(zf.read(opf_path))
        title = _first_text(package, "title") or title
        manifest = _read_manifest(package)
        spine_hrefs = _read_spine_hrefs(package, manifest, opf_path)
        if not spine_hrefs:
            spine_hrefs = _fallback_html_hrefs(manifest, opf_path)

        total = max(1, len(spine_hrefs))
        for index, href in enumerate(spine_hrefs, 1):
            member = _zip_member_path(opf_path, href)
            if member not in zf.namelist():
                continue
            text = _extract_html_text(zf.read(member))
            if not text.strip():
                continue
            for para in _split_paragraphs(text):
                blocks.append(_classify_text_block(para, index, "epub"))
            if progress:
                try:
                    progress(min(90, int(index * 90 / total)), f"解析 EPUB 第{index}/{total}个章节文件")
                except Exception:  # noqa: BLE001
                    pass

    if progress:
        try:
            progress(95, "EPUB 结构化完成")
        except Exception:  # noqa: BLE001
            pass
    return ParsedDocument(blocks=blocks, title=title, source_path=str(path), parser="epub")


def _find_opf_path(zf: zipfile.ZipFile) -> str:
    try:
        container = ET.fromstring(zf.read("META-INF/container.xml"))
    except KeyError as exc:
        raise ValueError("EPUB 结构损坏：缺少 META-INF/container.xml") from exc
    except ET.ParseError as exc:
        raise ValueError("EPUB 结构损坏：container.xml 解析失败") from exc

    ns = {"container": "urn:oasis:names:tc:opendocument:xmlns:container"}
    rootfile = container.find(".//container:rootfile", ns)
    if rootfile is None:
        raise ValueError("EPUB 结构损坏：未找到 OPF 根文件")
    full_path = rootfile.attrib.get("full-path", "").strip()
    if not full_path:
        raise ValueError("EPUB 结构损坏：OPF 根文件路径为空")
    return full_path


def _read_manifest(package: ET.Element) -> dict[str, dict[str, str]]:
    manifest: dict[str, dict[str, str]] = {}
    manifest_node = _find_first_node(package, "manifest")
    if manifest_node is None:
        return manifest
    for item in list(manifest_node):
        if _local_name(item.tag) != "item":
            continue
        item_id = (item.attrib.get("id") or "").strip()
        href = (item.attrib.get("href") or "").strip()
        if not item_id or not href:
            continue
        manifest[item_id] = {
            "href": href,
            "media_type": (item.attrib.get("media-type") or "").strip(),
        }
    return manifest


def _first_text(package: ET.Element, local_name: str) -> str:
    for node in package.iter():
        if _local_name(node.tag) == local_name:
            text = "".join(node.itertext()).strip()
            if text:
                return text
    return ""


def _read_spine_hrefs(
    package: ET.Element,
    manifest: dict[str, dict[str, str]],
    opf_path: str,
) -> list[str]:
    hrefs: list[str] = []
    spine_node = _find_first_node(package, "spine")
    if spine_node is None:
        return hrefs
    for itemref in list(spine_node):
        if _local_name(itemref.tag) != "itemref":
            continue
        if (itemref.attrib.get("linear") or "yes").lower() == "no":
            continue
        idref = (itemref.attrib.get("idref") or "").strip()
        item = manifest.get(idref)
        if not item:
            continue
        href = item["href"]
        media_type = item["media_type"]
        if media_type and media_type not in _HTML_MEDIA_TYPES and not href.lower().endswith((".html", ".htm", ".xhtml")):
            continue
        hrefs.append(href)
    return _dedupe(hrefs, opf_path)


def _fallback_html_hrefs(manifest: dict[str, dict[str, str]], opf_path: str) -> list[str]:
    hrefs = []
    for item in manifest.values():
        href = item["href"]
        media_type = item["media_type"]
        if media_type in _HTML_MEDIA_TYPES or href.lower().endswith((".html", ".htm", ".xhtml")):
            hrefs.append(href)
    return _dedupe(hrefs, opf_path)


def _find_first_node(root: ET.Element, local_name: str) -> ET.Element | None:
    for node in root.iter():
        if _local_name(node.tag) == local_name:
            return node
    return None


def _local_name(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _dedupe(hrefs: Iterable[str], opf_path: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for href in hrefs:
        member = _zip_member_path(opf_path, href)
        if member in seen:
            continue
        seen.add(member)
        out.append(href)
    return out


def _zip_member_path(opf_path: str, href: str) -> str:
    base = posixpath.dirname(opf_path)
    joined = posixpath.normpath(posixpath.join(base, unquote(href)))
    return joined.lstrip("./")


def _extract_html_text(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    parser = _EpubHtmlTextExtractor()
    parser.feed(text)
    parser.close()
    return parser.text()


def _split_paragraphs(text: str) -> list[str]:
    cleaned = html.unescape(text)
    cleaned = cleaned.replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    parts = [part.strip() for part in re.split(r"\n\s*\n", cleaned) if part.strip()]
    return parts


def _classify_text_block(text: str, page: int | None, source: str) -> StructuredBlock:
    if looks_like_code(text):
        return StructuredBlock(
            block_type=BlockType.CODE,
            text=text,
            page=page,
            language=detect_code_language(text) or "text",
            source=source,
        )
    if FormulaExtractor.looks_like_formula(text):
        return StructuredBlock(
            block_type=BlockType.FORMULA,
            text=text.strip("$ "),
            page=page,
            source=source,
        )
    if len(text) <= 60 and re.match(
        r"^(第[一二三四五六七八九十百0-9]+[章篇节]\s*\S+|chapter\s+\d+[.:\s]\S+|[0-9]+(\.[0-9]+){1,3}\s*\S+)",
        text,
        re.I,
    ):
        return StructuredBlock(block_type=BlockType.HEADING, text=text, page=page, source=source)
    if any(text.startswith(prefix) for prefix in ("1. ", "2. ", "3. ", "4. ", "5. ", "• ", "- ", "（1）", "(1)")):
        return StructuredBlock(block_type=BlockType.LIST, text=text, page=page, source=source)
    return StructuredBlock(block_type=BlockType.PARAGRAPH, text=text, page=page, source=source)


class _EpubHtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):  # noqa: D401
        tag = tag.lower()
        if tag in {"head", "script", "style", "svg", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "br":
            self._parts.append("\n")
            return
        if tag in _BLOCK_TAGS:
            self._parts.append("\n\n")

    def handle_endtag(self, tag):  # noqa: D401
        tag = tag.lower()
        if tag in {"head", "script", "style", "svg", "noscript"}:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag in _BLOCK_TAGS:
            self._parts.append("\n\n")

    def handle_data(self, data):  # noqa: D401
        if self._skip_depth:
            return
        text = html.unescape(data or "")
        if text:
            self._parts.append(text)

    def text(self) -> str:
        text = "".join(self._parts)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
