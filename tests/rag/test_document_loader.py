import pytest

from core.config.settings import Settings
from core.rag.document_loader import DocumentLoader, parse_front_matter
from core.rag.models import DocumentCategory


def test_parse_front_matter():
    content = """---
doc_id: test_doc_v1
category: system
audience: [rop, manager]
tags: [faq]
version: 1.0
last_updated: 2026-05-25
---
# Title

Body text.
"""
    meta, body = parse_front_matter(content)
    assert meta["doc_id"] == "test_doc_v1"
    assert "Body text" in body


def test_load_system_faq(settings: Settings):
    loader = DocumentLoader(settings)
    path = settings.rag_docs_path / "system" / "system_faq.md"
    if not path.exists():
        pytest.skip("rag_docs not available")
    metadata, body = loader.load(path)
    assert metadata.doc_id == "system_faq_v1"
    assert metadata.category == DocumentCategory.SYSTEM
    assert len(body) > 100
