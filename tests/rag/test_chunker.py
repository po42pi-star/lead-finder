from core.rag.chunker import MarkdownChunker
from core.rag.models import AudienceRole, DocumentCategory, DocumentMetadata, Priority


def test_chunker_splits_by_headers(settings):
    chunker = MarkdownChunker(settings)
    metadata = DocumentMetadata(
        doc_id="test_chunk_v1",
        category=DocumentCategory.PRODUCT,
        audience=[AudienceRole.MANAGER],
        tags=["test"],
        priority=Priority.HIGH,
    )
    body = """## Section A

Paragraph A with enough text for chunking validation.

### Subsection

Details about product.

## Section B

| Col1 | Col2 |
|------|------|
| a | b |
| c | d |
"""
    chunks = chunker.chunk_document(metadata, body, "products/test.md")
    assert len(chunks) >= 2
    assert any(chunk.section_title == "Section A" for chunk in chunks)
    assert all(chunk.doc_id == "test_chunk_v1" for chunk in chunks)
    assert all(chunk.chunk_id for chunk in chunks)
