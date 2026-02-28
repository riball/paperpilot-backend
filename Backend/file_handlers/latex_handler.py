import re


def extract_text_from_latex(file_path: str) -> str:
    """
    Reads a .tex file and extracts plain text suitable for parse_sections.
    Returns a structured text with 'SectionName: content' format.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    return parse_latex_to_structured_text(raw)


def parse_latex_to_structured_text(raw: str) -> str:
    """
    Parses LaTeX source into a structured 'Key: value' text
    that parse_sections() can understand.
    """
    sections = {}

    # ── Remove comments ──────────────────────────────────────────────────────
    raw = re.sub(r"%.*", "", raw)

    # ── Title ────────────────────────────────────────────────────────────────
    title_match = re.search(r"\\title\{([^}]*)\}", raw, re.DOTALL)
    if title_match:
        sections["title"] = clean_latex(title_match.group(1))

    # ── Abstract ─────────────────────────────────────────────────────────────
    abstract_match = re.search(
        r"\\begin\{abstract\}(.*?)\\end\{abstract\}", raw, re.DOTALL
    )
    if abstract_match:
        sections["abstract"] = clean_latex(abstract_match.group(1))

    # ── Keywords ─────────────────────────────────────────────────────────────
    kw_match = re.search(
        r"\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}", raw, re.DOTALL
    )
    if not kw_match:
        kw_match = re.search(r"\\keywords\{([^}]*)\}", raw, re.DOTALL)
    if kw_match:
        sections["keywords"] = clean_latex(kw_match.group(1))

    # ── Named sections (Introduction, Methodology, Results, Conclusion, etc.) ─
    section_pattern = re.compile(
        r"\\section\*?\{([^}]+)\}(.*?)(?=\\section|\\end\{document\}|$)",
        re.DOTALL,
    )
    for m in section_pattern.finditer(raw):
        name = m.group(1).strip().lower()
        body = clean_latex(m.group(2))
        sections[name] = body

    # ── References ───────────────────────────────────────────────────────────
    refs_match = re.search(
        r"\\begin\{thebibliography\}.*?(.*?)\\end\{thebibliography\}", raw, re.DOTALL
    )
    if refs_match:
        sections["references"] = clean_latex(refs_match.group(1))

    # ── Serialise to "Key: value\n" ──────────────────────────────────────────
    lines = []
    for key, value in sections.items():
        if value.strip():
            lines.append(f"{key}: {value.strip()}")

    return "\n\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────────

_KNOWN_CMDS = re.compile(
    r"\\(?:textbf|textit|emph|textrm|texttt|textsc|textsl|"
    r"label|ref|cite|footnote|url|href|centering|noindent|"
    r"newline|linebreak|pagebreak|par|vspace|hspace|"
    r"includegraphics|caption|subcaption)\*?\{[^}]*\}",
    re.DOTALL,
)

_SIMPLE_CMDS = re.compile(r"\\[a-zA-Z]+\*?")
_BRACES = re.compile(r"\{([^{}]*)\}")
_EXTRA_SPACE = re.compile(r"\s{2,}")


def clean_latex(text: str) -> str:
    """Strip LaTeX markup and return readable plain text."""
    # Remove known single-arg commands but keep their content
    text = re.sub(
        r"\\(?:textbf|textit|emph|textrm|texttt|textsc|textsl)\{([^}]*)\}",
        r"\1",
        text,
    )
    # Remove environments we don't care about
    text = re.sub(r"\\begin\{[^}]*\}|\\end\{[^}]*\}", "", text)
    # Remove \cite{...}, \label{...}, \ref{...} etc.
    text = re.sub(r"\\(?:cite|label|ref|footnote|url)\{[^}]*\}", "", text)
    # Remove remaining commands with args
    text = re.sub(r"\\[a-zA-Z]+\*?\{[^}]*\}", "", text)
    # Remove standalone commands
    text = re.sub(r"\\[a-zA-Z]+\*?", "", text)
    # Remove leftover braces
    text = text.replace("{", "").replace("}", "")
    # Collapse whitespace
    text = _EXTRA_SPACE.sub(" ", text.replace("\r", " ").replace("\n", " "))
    return text.strip()
