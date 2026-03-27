"""Tests for content extraction and noise removal."""

from __future__ import annotations

import pytest

from docslice.extractor import ExtractionError, extract_content

BASE = "https://docs.example.com"


# ---------------------------------------------------------------------------
# Content root selection
# ---------------------------------------------------------------------------

def test_extracts_article_by_default() -> None:
    html = """
    <html><body>
      <nav>Navigation</nav>
      <article><h1>Title</h1><p>Content here</p></article>
      <footer>Footer text</footer>
    </body></html>
    """
    result = extract_content(html, BASE)
    assert "Title" in result
    assert "Content here" in result
    assert "Navigation" not in result
    assert "Footer text" not in result


def test_custom_selector_takes_priority_over_article() -> None:
    html = """
    <html><body>
      <article>Article content</article>
      <div class="custom-main">Custom content</div>
    </body></html>
    """
    result = extract_content(html, BASE, content_selector=".custom-main")
    assert "Custom content" in result
    assert "Article content" not in result


def test_falls_back_to_main_when_no_article() -> None:
    html = """
    <html><body>
      <main><p>Main content</p></main>
    </body></html>
    """
    result = extract_content(html, BASE)
    assert "Main content" in result


def test_falls_back_to_role_main() -> None:
    html = """
    <html><body>
      <div role="main"><p>Role main content</p></div>
    </body></html>
    """
    result = extract_content(html, BASE)
    assert "Role main content" in result


def test_falls_back_to_dot_content() -> None:
    html = """
    <html><body>
      <div class="content"><p>Dot content</p></div>
    </body></html>
    """
    result = extract_content(html, BASE)
    assert "Dot content" in result


def test_falls_back_to_body_as_last_resort() -> None:
    html = "<html><body><p>Body content</p></body></html>"
    result = extract_content(html, BASE)
    assert "Body content" in result


def test_raises_when_no_node_found() -> None:
    # A document with literally nothing — lxml will still create <body>,
    # so we make the selector point to something that cannot exist.
    with pytest.raises(ExtractionError):
        extract_content("<html></html>", BASE, content_selector=".nonexistent-abc123")


# ---------------------------------------------------------------------------
# Noise removal (universal selectors)
# ---------------------------------------------------------------------------

def test_removes_nav_inside_article() -> None:
    html = """
    <html><body><article>
      <nav>Side nav</nav>
      <p>Real content</p>
    </article></body></html>
    """
    result = extract_content(html, BASE)
    assert "Side nav" not in result
    assert "Real content" in result


def test_removes_header_footer_inside_article() -> None:
    html = """
    <html><body><article>
      <header>Page header</header>
      <p>Body text</p>
      <footer>Page footer</footer>
    </article></body></html>
    """
    result = extract_content(html, BASE)
    assert "Page header" not in result
    assert "Page footer" not in result
    assert "Body text" in result


def test_removes_breadcrumbs_and_toc() -> None:
    html = """
    <html><body><article>
      <div class="breadcrumb">Home &gt; Page</div>
      <div class="toc">Table of Contents</div>
      <div class="table-of-contents">TOC</div>
      <p>Main text</p>
    </article></body></html>
    """
    result = extract_content(html, BASE)
    assert "Home" not in result
    assert "Table of Contents" not in result
    assert "Main text" in result


def test_removes_script_and_style() -> None:
    html = """
    <html><body><article>
      <script>alert(1)</script>
      <style>.foo { color: red; }</style>
      <p>Content</p>
    </article></body></html>
    """
    result = extract_content(html, BASE)
    assert "alert" not in result
    assert ".foo" not in result
    assert "Content" in result


def test_removes_copy_buttons_and_edit_links() -> None:
    html = """
    <html><body><article>
      <button class="copy-button">Copy</button>
      <a class="edit-this-page">Edit</a>
      <p>Content</p>
    </article></body></html>
    """
    result = extract_content(html, BASE)
    assert "Copy" not in result
    assert "Edit" not in result
    assert "Content" in result


def test_extra_noise_selectors_applied() -> None:
    html = """
    <html><body><article>
      <div class="theme-doc-toc-mobile">Mobile TOC</div>
      <div class="pagination-nav">Prev / Next</div>
      <p>Content</p>
    </article></body></html>
    """
    result = extract_content(
        html,
        BASE,
        extra_noise_selectors=[".theme-doc-toc-mobile", ".pagination-nav"],
    )
    assert "Mobile TOC" not in result
    assert "Prev / Next" not in result
    assert "Content" in result


# ---------------------------------------------------------------------------
# Link absolutization
# ---------------------------------------------------------------------------

def test_absolutizes_relative_href() -> None:
    html = """
    <html><body><article>
      <a href="/docs/page">Page</a>
    </article></body></html>
    """
    result = extract_content(html, BASE)
    assert 'href="https://docs.example.com/docs/page"' in result


def test_absolutizes_relative_img_src() -> None:
    html = """
    <html><body><article>
      <img src="/images/pic.png" />
    </article></body></html>
    """
    result = extract_content(html, BASE)
    assert 'src="https://docs.example.com/images/pic.png"' in result


def test_preserves_anchor_links() -> None:
    html = """
    <html><body><article>
      <a href="#section-two">Jump</a>
    </article></body></html>
    """
    result = extract_content(html, BASE)
    assert 'href="#section-two"' in result


def test_preserves_already_absolute_links() -> None:
    html = """
    <html><body><article>
      <a href="https://docs.example.com/other">Other</a>
    </article></body></html>
    """
    result = extract_content(html, BASE)
    assert 'href="https://docs.example.com/other"' in result
