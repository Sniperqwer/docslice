"""TOC extraction from HTML documentation pages."""

from __future__ import annotations

from dataclasses import dataclass, field

from bs4 import BeautifulSoup, NavigableString, Tag

from docslice.models import TocNode
from docslice.utils import normalize_url


@dataclass
class TocParseResult:
    nodes: list[TocNode]
    filtered_external: int = 0


def parse_toc(
    soup: BeautifulSoup, toc_selector: str, base_url: str
) -> TocParseResult:
    """Extract a TOC tree from soup using the given CSS selector.

    Returns a TocParseResult with the node tree and the count of external
    links that were filtered out.
    """
    container = soup.select_one(toc_selector)
    if container is None:
        return TocParseResult(nodes=[])

    # Use the container itself if it IS a list; otherwise find the first list inside.
    if container.name in ("ul", "ol"):
        root_list: Tag = container
    else:
        found = container.find(["ul", "ol"])
        if found is None:
            return TocParseResult(nodes=[])
        root_list = found

    filtered_external = 0

    def _parse_list(list_el: Tag) -> list[TocNode]:
        nonlocal filtered_external
        nodes: list[TocNode] = []
        for li in list_el.find_all("li", recursive=False):
            a_tag = _find_shallow_anchor(li)
            nested = _find_nested_list(li)
            children = _parse_list(nested) if nested else []

            if a_tag is not None:
                title = a_tag.get_text(strip=True) or "untitled"
                href = a_tag.get("href") or ""
                url: str | None = None
                if href and not href.startswith("#"):
                    url = normalize_url(href, base_url)
                    if url is None:
                        # Had a non-anchor href that was filtered (external domain)
                        filtered_external += 1
                nodes.append(TocNode(title=title, url=url, children=children))
            else:
                # Pure directory node: text title but no link
                title = _get_li_text(li)
                if title and (children or nested is not None):
                    nodes.append(TocNode(title=title, url=None, children=children))
        return nodes

    nodes = _parse_list(root_list)
    return TocParseResult(nodes=nodes, filtered_external=filtered_external)


def _find_shallow_anchor(li: Tag) -> Tag | None:
    """Find the first <a> that is a direct or shallow child of li,
    but not inside a nested <ul>/<ol>."""
    for child in li.children:
        if isinstance(child, NavigableString):
            continue
        if child.name in ("ul", "ol"):
            continue
        if child.name == "a":
            return child
        # One level deeper inside non-list wrapper elements (span, div, button…)
        found = child.find("a")
        if found:
            return found
    return None


def _find_nested_list(li: Tag) -> Tag | None:
    """Return the first direct-child <ul> or <ol> of this li."""
    for child in li.children:
        if isinstance(child, NavigableString):
            continue
        if child.name in ("ul", "ol"):
            return child
    return None


def _get_li_text(li: Tag) -> str:
    """Collect visible text from li, excluding content inside nested lists."""
    parts: list[str] = []
    for child in li.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                parts.append(text)
        elif child.name not in ("ul", "ol"):
            text = child.get_text(strip=True)
            if text:
                parts.append(text)
    return " ".join(parts).strip()
