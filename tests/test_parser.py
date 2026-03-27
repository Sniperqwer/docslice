from __future__ import annotations

from bs4 import BeautifulSoup

from docslice.parser import parse_toc

BASE = "https://docs.example.com"


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


# ---------------------------------------------------------------------------
# Standard nested navigation
# ---------------------------------------------------------------------------

def test_parse_flat_list() -> None:
    soup = _soup("""
    <nav class="sidebar">
      <ul>
        <li><a href="/docs/intro">Introduction</a></li>
        <li><a href="/docs/quickstart">Quickstart</a></li>
      </ul>
    </nav>
    """)
    result = parse_toc(soup, ".sidebar", BASE)
    assert len(result.nodes) == 2
    assert result.nodes[0].title == "Introduction"
    assert result.nodes[0].url == "https://docs.example.com/docs/intro"
    assert result.nodes[1].title == "Quickstart"


def test_parse_nested_list() -> None:
    soup = _soup("""
    <nav class="sidebar">
      <ul>
        <li>
          <a href="/docs/getting-started">Getting Started</a>
          <ul>
            <li><a href="/docs/overview">Overview</a></li>
            <li><a href="/docs/install">Installation</a></li>
          </ul>
        </li>
      </ul>
    </nav>
    """)
    result = parse_toc(soup, ".sidebar", BASE)
    assert len(result.nodes) == 1
    parent = result.nodes[0]
    assert parent.title == "Getting Started"
    assert parent.url == "https://docs.example.com/docs/getting-started"
    assert len(parent.children) == 2
    assert parent.children[0].title == "Overview"


# ---------------------------------------------------------------------------
# Pure directory node (no link, but has children)
# ---------------------------------------------------------------------------

def test_parse_pure_directory_node() -> None:
    soup = _soup("""
    <nav class="sidebar">
      <ul>
        <li>
          <span>Getting Started</span>
          <ul>
            <li><a href="/docs/overview">Overview</a></li>
          </ul>
        </li>
      </ul>
    </nav>
    """)
    result = parse_toc(soup, ".sidebar", BASE)
    assert len(result.nodes) == 1
    parent = result.nodes[0]
    assert parent.title == "Getting Started"
    assert parent.url is None
    assert len(parent.children) == 1
    assert parent.children[0].url == "https://docs.example.com/docs/overview"


def test_parse_plain_text_directory_node() -> None:
    soup = _soup("""
    <nav class="sidebar">
      <ul>
        <li>
          Core Concepts
          <ul>
            <li><a href="/docs/concepts">Concepts</a></li>
          </ul>
        </li>
      </ul>
    </nav>
    """)
    result = parse_toc(soup, ".sidebar", BASE)
    assert result.nodes[0].title == "Core Concepts"
    assert result.nodes[0].url is None


# ---------------------------------------------------------------------------
# Anchor-only links are filtered (url=None, not counted as external)
# ---------------------------------------------------------------------------

def test_anchor_links_produce_none_url() -> None:
    soup = _soup("""
    <nav class="sidebar">
      <ul>
        <li><a href="#section-1">Section 1</a></li>
        <li><a href="/docs/real-page">Real Page</a></li>
      </ul>
    </nav>
    """)
    result = parse_toc(soup, ".sidebar", BASE)
    # anchor link node: url is None (not external, not counted in filtered_external)
    assert result.nodes[0].url is None
    assert result.nodes[1].url is not None
    assert result.filtered_external == 0


# ---------------------------------------------------------------------------
# External links are filtered and counted
# ---------------------------------------------------------------------------

def test_external_links_are_filtered_and_counted() -> None:
    soup = _soup("""
    <nav class="sidebar">
      <ul>
        <li><a href="https://external.com/page">External</a></li>
        <li><a href="/docs/local">Local</a></li>
      </ul>
    </nav>
    """)
    result = parse_toc(soup, ".sidebar", BASE)
    assert result.filtered_external == 1
    assert result.nodes[0].url is None   # external filtered → None
    assert result.nodes[1].url is not None


# ---------------------------------------------------------------------------
# Selector not found
# ---------------------------------------------------------------------------

def test_returns_empty_when_selector_not_found() -> None:
    soup = _soup("<html><body><p>No nav here</p></body></html>")
    result = parse_toc(soup, ".nonexistent", BASE)
    assert result.nodes == []
    assert result.filtered_external == 0


def test_returns_empty_when_container_has_no_list() -> None:
    soup = _soup('<nav class="sidebar"><p>No lists here</p></nav>')
    result = parse_toc(soup, ".sidebar", BASE)
    assert result.nodes == []


# ---------------------------------------------------------------------------
# UTM params and fragment stripping happen via normalize_url
# ---------------------------------------------------------------------------

def test_utm_params_stripped_from_toc_urls() -> None:
    soup = _soup("""
    <nav class="sidebar">
      <ul>
        <li><a href="/docs/page?utm_source=nav&keep=1#section">Page</a></li>
      </ul>
    </nav>
    """)
    result = parse_toc(soup, ".sidebar", BASE)
    assert result.nodes[0].url == "https://docs.example.com/docs/page?keep=1"


# ---------------------------------------------------------------------------
# First selector match is used when multiple containers exist
# ---------------------------------------------------------------------------

def test_uses_first_matching_container() -> None:
    soup = _soup("""
    <nav class="sidebar">
      <ul>
        <li><a href="/docs/first">First Nav</a></li>
      </ul>
    </nav>
    <nav class="sidebar">
      <ul>
        <li><a href="/docs/second">Second Nav</a></li>
      </ul>
    </nav>
    """)
    result = parse_toc(soup, ".sidebar", BASE)
    assert result.nodes[0].title == "First Nav"


# ---------------------------------------------------------------------------
# Multiple sibling <ul> elements (e.g. Mintlify sidebar)
# ---------------------------------------------------------------------------

def test_parse_multiple_sibling_uls() -> None:
    soup = _soup("""
    <div id="navigation-items">
      <ul>
        <li><a href="/docs/overview">Overview</a></li>
        <li><a href="/docs/quickstart">Quickstart</a></li>
      </ul>
      <ul>
        <li><a href="/docs/concepts">Concepts</a></li>
      </ul>
      <ul>
        <li><a href="/docs/api">API Reference</a></li>
        <li><a href="/docs/faq">FAQ</a></li>
      </ul>
    </div>
    """)
    result = parse_toc(soup, "#navigation-items", BASE)
    assert len(result.nodes) == 5
    titles = [n.title for n in result.nodes]
    assert titles == ["Overview", "Quickstart", "Concepts", "API Reference", "FAQ"]
