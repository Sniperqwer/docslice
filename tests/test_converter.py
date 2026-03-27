"""Tests for HTML → Markdown conversion."""

from __future__ import annotations

from docslice.converter import html_to_markdown


# ---------------------------------------------------------------------------
# Headings
# ---------------------------------------------------------------------------

def test_converts_h1_to_atx() -> None:
    md = html_to_markdown("<h1>Title</h1>")
    assert "# Title" in md


def test_converts_h2_h3() -> None:
    md = html_to_markdown("<h2>Section</h2><h3>Subsection</h3>")
    assert "## Section" in md
    assert "### Subsection" in md


# ---------------------------------------------------------------------------
# Paragraphs
# ---------------------------------------------------------------------------

def test_converts_paragraphs() -> None:
    md = html_to_markdown("<p>First</p><p>Second</p>")
    assert "First" in md
    assert "Second" in md


# ---------------------------------------------------------------------------
# Code blocks
# ---------------------------------------------------------------------------

def test_fenced_code_block_with_language() -> None:
    md = html_to_markdown('<pre><code class="language-python">x = 1</code></pre>')
    assert "```python" in md
    assert "x = 1" in md


def test_fenced_code_block_without_language() -> None:
    md = html_to_markdown("<pre><code>some code</code></pre>")
    assert "```" in md
    assert "some code" in md


def test_inline_code() -> None:
    md = html_to_markdown("<p>Use <code>print()</code> here.</p>")
    assert "`print()`" in md


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------

def test_unordered_list() -> None:
    md = html_to_markdown("<ul><li>Item A</li><li>Item B</li></ul>")
    assert "Item A" in md
    assert "Item B" in md


def test_ordered_list() -> None:
    md = html_to_markdown("<ol><li>First</li><li>Second</li></ol>")
    assert "First" in md
    assert "Second" in md


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------

def test_converts_simple_table() -> None:
    html = """
    <table>
      <thead><tr><th>Name</th><th>Value</th></tr></thead>
      <tbody><tr><td>foo</td><td>bar</td></tr></tbody>
    </table>
    """
    md = html_to_markdown(html)
    assert "Name" in md
    assert "Value" in md
    assert "foo" in md
    assert "bar" in md


# ---------------------------------------------------------------------------
# Links and images
# ---------------------------------------------------------------------------

def test_preserves_links() -> None:
    html = '<a href="https://example.com/page">Link text</a>'
    md = html_to_markdown(html)
    assert "Link text" in md
    assert "https://example.com/page" in md


def test_preserves_images() -> None:
    html = '<img src="https://example.com/img.png" alt="A picture" />'
    md = html_to_markdown(html)
    assert "https://example.com/img.png" in md


# ---------------------------------------------------------------------------
# Output hygiene
# ---------------------------------------------------------------------------

def test_no_excessive_blank_lines() -> None:
    html = "<p>A</p><p>B</p><p>C</p>"
    md = html_to_markdown(html)
    assert "\n\n\n" not in md


def test_output_is_stripped() -> None:
    md = html_to_markdown("  <p>Content</p>  ")
    assert md == md.strip()


def test_empty_html_returns_empty_string() -> None:
    md = html_to_markdown("")
    assert md == ""
