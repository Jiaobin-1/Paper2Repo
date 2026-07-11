from __future__ import annotations

from app.services.reports.html import build_report_html
from app.services.reports.latex import build_report_latex


def test_html_export_blocks_active_link_schemes() -> None:
    html = build_report_html(
        "Report",
        "[unsafe](javascript:alert(1)) [file](file:///etc/passwd) [safe](https://example.com/paper)",
    )

    assert 'href="javascript:' not in html
    assert 'href="file:' not in html
    assert '<a href="https://example.com/paper" rel="noopener noreferrer">safe</a>' in html
    assert "unsafe" in html
    assert "file" in html


def test_latex_export_escapes_commands_in_text_and_title() -> None:
    latex = build_report_latex(
        r"Report \input{/etc/passwd}",
        r"Body \include{/etc/passwd} and 100% coverage.",
    )

    assert r"Report \input{/etc/passwd}" not in latex
    assert r"Body \include{/etc/passwd}" not in latex
    assert r"\textbackslash{}input\{/etc/passwd\}" in latex
    assert r"100\% coverage" in latex


def test_latex_export_cannot_close_verbatim_block_from_report_content() -> None:
    latex = build_report_latex(
        "Report",
        "```tex\n\\end{Verbatim}\n\\input{/etc/passwd}\n```",
    )

    assert latex.splitlines().count(r"\end{Verbatim}") == 1
    assert r"\\end{Verbatim}" in latex
