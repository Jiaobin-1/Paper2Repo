from __future__ import annotations

import re


def build_report_latex(title: str, markdown: str) -> str:
    body = _markdown_to_latex(markdown)
    return f"""\\documentclass[11pt,a4paper]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{lmodern}}
\\usepackage[margin=2.5cm]{{geometry}}
\\usepackage{{hyperref}}
\\usepackage{{xcolor}}
\\definecolor{{accent}}{{HTML}}{{4F46E5}}
\\hypersetup{{colorlinks=true,linkcolor=accent,urlcolor=accent}}
\\usepackage{{enumitem}}
\\usepackage{{fancyvrb}}
\\usepackage{{longtable}}
\\usepackage{{booktabs}}
\\setlength{{\\parindent}}{{0pt}}
\\setlength{{\\parskip}}{{6pt}}
\\title{{{_escape_latex(title)}}}
\\date{{}}
\\begin{{document}}
\\maketitle
{body}
\\end{{document}}
"""


def _markdown_to_latex(md: str) -> str:
    lines: list[str] = []
    in_code = False
    code_lines: list[str] = []
    in_table = False
    table_rows: list[list[str]] = []

    def flush_code() -> None:
        nonlocal code_lines
        if code_lines:
            code_text = "\n".join(code_lines)
            lines.append(f"\\begin{{Verbatim}}[breaklines=true,fontsize=\\small]\n{code_text}\n\\end{{Verbatim}}")
            code_lines = []

    def flush_table() -> None:
        nonlocal table_rows, in_table
        if not table_rows:
            return
        ncols = len(table_rows[0]) if table_rows else 0
        col_spec = "|" .join(["l"] * ncols)
        lines.append(f"\\begin{{longtable}}{{|{col_spec}|}}")
        lines.append("\\hline")
        for i, row in enumerate(table_rows):
            cells = " & ".join(_escape_latex(c) for c in row)
            lines.append(f"{cells} \\\\")
            lines.append("\\hline")
            if i == 0:
                lines.append("\\hline")
        lines.append("\\end{{longtable}}")
        table_rows = []
        in_table = False

    for raw_line in md.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                if in_table:
                    flush_table()
                in_code = True
                code_lines = []
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            if in_table:
                flush_table()
            lines.append("")
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(set(c) <= set("- :") for c in cells):
                continue
            table_rows.append(cells)
            in_table = True
            continue

        if in_table:
            flush_table()

        if stripped == "---":
            lines.append("\\bigskip\\hrule\\bigskip")
            continue

        heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text = _escape_latex(heading_match.group(2))
            if level == 1:
                lines.append(f"\\section{{{text}}}")
            elif level == 2:
                lines.append(f"\\subsection{{{text}}}")
            else:
                lines.append(f"\\subsubsection{{{text}}}")
            continue

        if stripped.startswith(">"):
            text = _escape_latex(stripped.lstrip("> ").strip())
            lines.append(f"\\begin{{quote}}\\textit{{{text}}}\\end{{quote}}")
            continue

        bullet_match = re.match(r"^[-*]\s+(?:\[[ xX]\]\s+)?(.+)$", stripped)
        if bullet_match:
            text = _inline_latex(bullet_match.group(1))
            lines.append(f"\\item {text}")
            continue

        ordered_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if ordered_match:
            text = _inline_latex(ordered_match.group(2))
            lines.append(f"\\item {text}")
            continue

        lines.append(_inline_latex(stripped))

    flush_code()
    flush_table()

    result = "\n".join(lines)
    result = re.sub(r"(\\item [^\n]+(?:\n(?!\\item|\\end|\\section|\\subsection|\\subsubsection|\\bigskip))*?)", _wrap_enumerate, result)
    return result


def _wrap_enumerate(match: re.Match) -> str:
    text = match.group(0)
    if text.strip().startswith("\\item"):
        items = [line for line in text.split("\n") if line.strip().startswith("\\item")]
        return "\\begin{itemize}\n" + "\n".join(items) + "\n\\end{itemize}"
    return text


def _escape_latex(text: str) -> str:
    s = text
    for ch, rep in [("&", "\\&"), ("%", "\\%"), ("$", "\\$"), ("#", "\\#"), ("_", "\\_"), ("{", "\\{"), ("}", "\\}"), ("~", "\\textasciitilde{}"), ("^", "\\textasciicircum{}")]:
        s = s.replace(ch, rep)
    return s


def _inline_latex(text: str) -> str:
    s = _escape_latex(text)
    s = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", s)
    s = re.sub(r"\*(.+?)\*", r"\\textit{\1}", s)
    s = re.sub(r"`(.+?)`", r"\\texttt{\1}", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\\href{\2}{\1}", s)
    return s
