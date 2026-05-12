from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from textwrap import shorten

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import registerFont, stringWidth
from reportlab.pdfgen.canvas import Canvas


PDF_FONT_NAME = "STSong-Light"
PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 18 * mm
RIGHT_MARGIN = 18 * mm
TOP_MARGIN = 18 * mm
BOTTOM_MARGIN = 18 * mm
FOOTER_Y = 10 * mm


@dataclass
class PdfBlock:
    kind: str
    text: str = ""
    level: int = 0


class ReportPdfRenderer:
    def __init__(self, canvas: Canvas) -> None:
        self.canvas = canvas
        self.page = 1
        self.y = PAGE_HEIGHT - TOP_MARGIN

    def finish(self) -> None:
        self._draw_footer()
        self.canvas.save()

    def draw_block(self, block: PdfBlock) -> None:
        if block.kind == "page_break":
            self._new_page()
            return
        if block.kind == "spacer":
            self._move_down(5)
            return

        if block.kind == "heading":
            font_size = 18 if block.level == 1 else 14 if block.level == 2 else 12
            leading = 24 if block.level == 1 else 20 if block.level == 2 else 17
            color = colors.HexColor("#172033")
            self._move_down(8 if block.level > 1 else 0)
            self._draw_wrapped(block.text, font_size=font_size, leading=leading, color=color)
            self._move_down(4)
            return

        if block.kind == "quote":
            self._draw_wrapped(block.text, font_size=10, leading=15, color=colors.HexColor("#647084"), indent=5 * mm)
            self._move_down(3)
            return

        if block.kind == "bullet":
            self._draw_wrapped(block.text, font_size=10, leading=15, bullet="-", indent=6 * mm)
            return

        if block.kind == "code":
            for line in block.text.splitlines() or [""]:
                self._draw_wrapped(line, font_size=8.5, leading=12, color=colors.HexColor("#334155"), indent=5 * mm)
            self._move_down(4)
            return

        self._draw_wrapped(block.text, font_size=10.5, leading=16)

    def _draw_wrapped(
        self,
        text: str,
        *,
        font_size: float,
        leading: float,
        color=colors.black,
        indent: float = 0,
        bullet: str | None = None,
    ) -> None:
        max_width = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN - indent
        lines = _wrap_text(text, max_width=max_width, font_size=font_size)
        if not lines:
            return
        for index, line in enumerate(lines):
            self._ensure_space(leading)
            self.canvas.setFont(PDF_FONT_NAME, font_size)
            self.canvas.setFillColor(color)
            x = LEFT_MARGIN + indent
            if bullet and index == 0:
                self.canvas.drawString(LEFT_MARGIN, self.y, bullet)
            self.canvas.drawString(x, self.y, line)
            self.y -= leading

    def _move_down(self, amount: float) -> None:
        self._ensure_space(amount)
        self.y -= amount

    def _ensure_space(self, needed: float) -> None:
        if self.y - needed < BOTTOM_MARGIN:
            self._new_page()

    def _new_page(self) -> None:
        self._draw_footer()
        self.canvas.showPage()
        self.page += 1
        self.y = PAGE_HEIGHT - TOP_MARGIN

    def _draw_footer(self) -> None:
        self.canvas.setFont(PDF_FONT_NAME, 8)
        self.canvas.setFillColor(colors.HexColor("#647084"))
        self.canvas.drawCentredString(PAGE_WIDTH / 2, FOOTER_Y, f"Paper2Repo Report - Page {self.page}")


_font_registered = False


def _ensure_font() -> None:
    global _font_registered
    if not _font_registered:
        registerFont(UnicodeCIDFont(PDF_FONT_NAME))
        _font_registered = True


def build_report_pdf(title: str, markdown: str) -> bytes:
    _ensure_font()
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=A4)
    canvas.setTitle(title)
    renderer = ReportPdfRenderer(canvas)
    for block in _markdown_to_blocks(markdown):
        renderer.draw_block(block)
    renderer.finish()
    return buffer.getvalue()


def _markdown_to_blocks(markdown: str) -> list[PdfBlock]:
    blocks: list[PdfBlock] = []
    code_lines: list[str] = []
    in_code_block = False

    def flush_code() -> None:
        nonlocal code_lines
        if code_lines:
            blocks.append(PdfBlock(kind="code", text="\n".join(code_lines)))
            code_lines = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                flush_code()
                in_code_block = False
            else:
                in_code_block = True
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(shorten(line, width=220, placeholder="..."))
            continue

        if not stripped:
            blocks.append(PdfBlock(kind="spacer"))
            continue

        if stripped == "---":
            blocks.append(PdfBlock(kind="page_break"))
            continue

        heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading_match:
            blocks.append(
                PdfBlock(
                    kind="heading",
                    text=_clean_inline(heading_match.group(2)),
                    level=len(heading_match.group(1)),
                )
            )
            continue

        if stripped.startswith(">"):
            blocks.append(PdfBlock(kind="quote", text=_clean_inline(stripped.lstrip("> ").strip())))
            continue

        bullet_match = re.match(r"^[-*]\s+(?:\[[ xX]\]\s+)?(.+)$", stripped)
        if bullet_match:
            blocks.append(PdfBlock(kind="bullet", text=_clean_inline(bullet_match.group(1))))
            continue

        ordered_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if ordered_match:
            blocks.append(PdfBlock(kind="bullet", text=f"{ordered_match.group(1)}. {_clean_inline(ordered_match.group(2))}"))
            continue

        blocks.append(PdfBlock(kind="body", text=_clean_inline(stripped)))

    flush_code()
    return blocks


def _clean_inline(text: str) -> str:
    cleaned = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    cleaned = re.sub(r"[*_`]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _wrap_text(text: str, *, max_width: float, font_size: float) -> list[str]:
    if not text:
        return []

    lines: list[str] = []
    current = ""
    for token in _wrap_tokens(text):
        candidate = f"{current}{token}" if current else token.lstrip()
        if current and stringWidth(candidate, PDF_FONT_NAME, font_size) > max_width:
            lines.append(current.rstrip())
            current = token.lstrip()
        else:
            current = candidate
    if current.strip():
        lines.append(current.rstrip())
    return lines


def _wrap_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for part in re.split(r"(\s+)", text):
        if not part:
            continue
        if part.isspace():
            tokens.append(part)
            continue
        if len(part) > 80:
            tokens.extend(part[index : index + 40] for index in range(0, len(part), 40))
        else:
            tokens.append(part)
    return tokens
