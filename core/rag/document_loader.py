import logging
import re
from pathlib import Path

import yaml

from core.config.settings import Settings
from core.rag.models import AudienceRole, DocumentCategory, DocumentMetadata, Priority

logger = logging.getLogger(__name__)

FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _infer_category_from_path(path: Path, docs_root: Path) -> DocumentCategory | None:
    try:
        relative = path.relative_to(docs_root)
        folder = relative.parts[0].lower() if relative.parts else ""
    except ValueError:
        return None
    mapping = {
        "products": DocumentCategory.PRODUCT,
        "product": DocumentCategory.PRODUCT,
        "sales": DocumentCategory.SALES,
        "segments": DocumentCategory.SEGMENTS,
        "company": DocumentCategory.COMPANY,
        "system": DocumentCategory.SYSTEM,
    }
    return mapping.get(folder)


def parse_front_matter(content: str) -> tuple[dict, str]:
    match = FRONT_MATTER_PATTERN.match(content)
    if not match:
        return {}, content
    raw_yaml = match.group(1)
    body = content[match.end() :]
    metadata = yaml.safe_load(raw_yaml) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return metadata, body


def build_document_metadata(
    path: Path,
    raw_meta: dict,
    settings: Settings,
) -> DocumentMetadata:
    docs_root = settings.rag_docs_path.resolve()
    category_raw = raw_meta.get("category")
    if category_raw:
        category = DocumentCategory(str(category_raw).lower())
    else:
        inferred = _infer_category_from_path(path, docs_root)
        if inferred is None:
            raise ValueError(f"Cannot infer category for {path}")
        category = inferred

    audience_values = raw_meta.get("audience", [])
    if isinstance(audience_values, str):
        audience_values = [audience_values]
    audience = [AudienceRole(str(item).lower()) for item in audience_values]

    tags = raw_meta.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]

    priority_raw = raw_meta.get("priority", Priority.MEDIUM.value)
    priority = Priority(str(priority_raw).lower())

    known_keys = {
        "doc_id",
        "category",
        "audience",
        "tags",
        "version",
        "last_updated",
        "related_docs",
        "priority",
    }
    extra = {k: v for k, v in raw_meta.items() if k not in known_keys}

    doc_id = raw_meta.get("doc_id") or path.stem
    last_updated = raw_meta.get("last_updated")
    if last_updated is not None:
        last_updated = str(last_updated)

    return DocumentMetadata(
        doc_id=doc_id,
        category=category,
        audience=audience,
        tags=[str(t) for t in tags],
        version=str(raw_meta.get("version", "1.0")),
        last_updated=last_updated,
        related_docs=[str(r) for r in raw_meta.get("related_docs", [])],
        priority=priority,
        extra=extra,
    )


class DocumentLoader:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def discover_files(self, sub_path: str | None = None) -> list[Path]:
        root = self._settings.rag_docs_path.resolve()
        target = root / sub_path if sub_path and sub_path.strip() else root
        if not target.exists():
            raise FileNotFoundError(f"RAG path not found: {target}")
        return sorted(
            p
            for p in target.rglob("*.md")
            if p.is_file() and not p.name.startswith(".")
        )

    def load(self, path: Path) -> tuple[DocumentMetadata, str]:
        content = path.read_text(encoding="utf-8")
        raw_meta, body = parse_front_matter(content)
        metadata = build_document_metadata(path, raw_meta, self._settings)
        source_file = str(path.resolve().relative_to(self._settings.rag_docs_path.resolve()))
        metadata.extra["source_file"] = source_file
        return metadata, body.strip()
