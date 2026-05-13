from __future__ import annotations

from app.schemas.chunks import ChunkedPaper, ChunkMetadata, PaperChunk
from app.schemas.parsed import ParsedPaper, SectionCandidate


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


def _section_for_page(sections: list[SectionCandidate], page_number: int) -> str | None:
    active = [section for section in sections if section.page_number <= page_number]
    if not active:
        return None
    return active[-1].title


def _split_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current = ""
    for paragraph in [part.strip() for part in text.split("\n\n") if part.strip()]:
        if current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append(current.strip())
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}".strip() if current else paragraph

    if current:
        chunks.append(current.strip())

    if not chunks:
        chunks = [text[i : i + max_chars] for i in range(0, len(text), max_chars)]
    return chunks


def chunk_parsed_paper(parsed: ParsedPaper, max_chars: int = 2500) -> ChunkedPaper:
    chunks: list[PaperChunk] = []
    chunk_index = 0

    for page in parsed.page_texts:
        text = page.text.strip()
        if not text:
            continue
        section_title = _section_for_page(parsed.section_candidates, page.page_number)
        for part in _split_text(text, max_chars=max_chars):
            chunks.append(
                PaperChunk(
                    content=part,
                    metadata=ChunkMetadata(
                        chunk_index=chunk_index,
                        page_start=page.page_number,
                        page_end=page.page_number,
                        section_title=section_title,
                        token_estimate=_estimate_tokens(part),
                    ),
                )
            )
            chunk_index += 1

    return ChunkedPaper(chunks=chunks, chunk_count=len(chunks))
