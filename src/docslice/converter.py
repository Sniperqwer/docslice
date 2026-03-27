"""HTML-to-Markdown conversion."""

from __future__ import annotations

import re

from bs4 import Tag
from markdownify import markdownify as _markdownify


def _extract_code_language(pre_el: Tag) -> str:
    """Return the code language from a <pre>'s inner <code> class attribute.

    Looks for a class like ``language-python`` on the child ``<code>`` tag.
    Returns an empty string if no language hint is found.
    """
    code_el = pre_el.find("code")
    if code_el is None:
        return ""
    for cls in code_el.get("class") or []:
        if cls.startswith("language-"):
            return cls[len("language-"):]
    return ""


def html_to_markdown(html: str) -> str:
    """Convert cleaned content HTML to Markdown.

    Uses ATX headings (# style), dash bullets, and extracts code block
    language hints from ``language-*`` CSS classes on ``<code>`` elements.
    """
    md: str = _markdownify(
        html,
        heading_style="ATX",
        bullets="-",
        strip=["script", "style"],
        code_language_callback=_extract_code_language,
    )
    # Collapse runs of 3+ blank lines down to 2.
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()
