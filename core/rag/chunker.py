import hashlib
import re
from dataclasses import dataclass

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config.settings import Settings
from core.rag.models import ChunkMetadata, DocumentMetadata

HEADER_PATTERN = re.compile(r"^(#{2,4})\s+(.+)$", re.MULTILINE)
TABLE_LINE_PATTERN = re.compile(r"^\|.+\|$", re.MULTILINE)


@dataclass
class SectionBlock:
    title: str
    level: int
    text: str
    char_start: int
    char_end: int
    is_table: bool


class MarkdownChunker:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._encoding = tiktoken.get_encoding("cl100k_base")
        self._recursive = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", " ", ""],
            chunk_size=settings.chunk_max_tokens,
            chunk_overlap=settings.chunk_overlap_tokens,
            length_function=self._count_tokens,
        )

    def _count_tokens(self, text: str) -> int:
        return len(self._encoding.encode(text))

    def _split_tables(self, text: str) -> list[tuple[str, bool]]:
        lines = text.splitlines(keepends=True)
        blocks: list[tuple[str, bool]] = []
        buffer: list[str] = []
        in_table = False

        def flush(buf: list[str], is_table: bool) -> None:
            if buf:
                blocks.append(("".join(buf), is_table))
                buf.clear()

        for line in lines:
            is_table_line = bool(TABLE_LINE_PATTERN.match(line.strip()))
            if is_table_line != in_table and buffer:
                flush(buffer, in_table)
                in_table = is_table_line
            elif not buffer:
                in_table = is_table_line
            buffer.append(line)
        flush(buffer, in_table)
        return blocks if blocks else [(text, False)]

    def _parse_sections(self, body: str) -> list[SectionBlock]:
        matches = list(HEADER_PATTERN.finditer(body))
        if not matches:
            return [
                SectionBlock(
                    title="",
                    level=2,
                    text=body,
                    char_start=0,
                    char_end=len(body),
                    is_table=False,
                )
            ]

        sections: list[SectionBlock] = []
        for idx, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
            text = body[start:end].strip()
            if not text:
                continue
            table_blocks = self._split_tables(text)
            offset = start
            for block_text, is_table in table_blocks:
                if not block_text.strip():
                    continue
                char_start = body.find(block_text, offset)
                if char_start < 0:
                    char_start = offset
                char_end = char_start + len(block_text)
                sections.append(
                    SectionBlock(
                        title=title,
                        level=level,
                        text=block_text,
                        char_start=char_start,
                        char_end=char_end,
                        is_table=is_table,
                    )
                )
                offset = char_end
        return sections

    def _split_section(self, section: SectionBlock) -> list[str]:
        if section.is_table:
            return [section.text]
        if self._count_tokens(section.text) <= self._settings.chunk_max_tokens:
            return [section.text]
        if section.level <= 3:
            sub_headers = list(HEADER_PATTERN.finditer(section.text))
            if sub_headers:
                parts: list[str] = []
                for idx, match in enumerate(sub_headers):
                    sub_start = match.end()
                    sub_end = (
                        sub_headers[idx + 1].start()
                        if idx + 1 < len(sub_headers)
                        else len(section.text)
                    )
                    part = section.text[sub_start:sub_end].strip()
                    if part:
                        parts.append(f"{match.group(2).strip()}\n\n{part}")
                if parts:
                    oversized = [
                        p
                        for p in parts
                        if self._count_tokens(p) > self._settings.chunk_max_tokens
                    ]
                    if not oversized:
                        return parts
        return self._recursive.split_text(section.text)

    def chunk_document(
        self,
        metadata: DocumentMetadata,
        body: str,
        source_file: str,
    ) -> list[ChunkMetadata]:
        chunks: list[ChunkMetadata] = []
        for section in self._parse_sections(body):
            for piece in self._split_section(section):
                if not piece.strip():
                    continue
                chunk_id = self._make_chunk_id(metadata.doc_id, piece, section.title)
                char_start = body.find(piece)
                char_end = char_start + len(piece) if char_start >= 0 else len(piece)
                chunks.append(
                    ChunkMetadata(
                        **metadata.model_dump(exclude={"extra"}),
                        chunk_id=chunk_id,
                        section_title=section.title,
                        char_start=max(char_start, 0),
                        char_end=char_end,
                        source_file=source_file,
                        is_table=section.is_table,
                        text=piece.strip(),
                    )
                )
        return chunks

    @staticmethod
    def _make_chunk_id(doc_id: str, text: str, section: str) -> str:
        digest = hashlib.sha256(f"{doc_id}:{section}:{text[:200]}".encode()).hexdigest()
        return f"{doc_id}_{digest[:12]}"
