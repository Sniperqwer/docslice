"""Framework presets for documentation site detection and extraction."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from bs4 import BeautifulSoup


@dataclass
class Preset:
    name: str
    detect: Callable[[BeautifulSoup], bool]
    toc_selector: str
    content_selector: str
    noise_selectors: list[str] = field(default_factory=list)


def _detect_docusaurus(soup: BeautifulSoup) -> bool:
    meta = soup.find("meta", attrs={"name": "generator"})
    if meta and "docusaurus" in (meta.get("content") or "").lower():
        return True
    if soup.select_one(".navbar__brand") or soup.select_one(
        ".theme-doc-sidebar-container"
    ):
        return True
    return False


def _detect_mkdocs(soup: BeautifulSoup) -> bool:
    meta = soup.find("meta", attrs={"name": "generator"})
    if meta and "mkdocs" in (meta.get("content") or "").lower():
        return True
    if soup.select_one(".md-container") or soup.select_one(".md-nav"):
        return True
    return False


def _detect_gitbook(soup: BeautifulSoup) -> bool:
    meta = soup.find("meta", attrs={"name": "generator"})
    if meta and "gitbook" in (meta.get("content") or "").lower():
        return True
    if soup.select_one(".gitbook-root") or soup.select_one(".book-summary"):
        return True
    return False


def _detect_sphinx(soup: BeautifulSoup) -> bool:
    meta = soup.find("meta", attrs={"name": "generator"})
    if meta and "sphinx" in (meta.get("content") or "").lower():
        return True
    if soup.select_one(".sphinxsidebar") or soup.select_one(
        ".sphinxsidebarwrapper"
    ):
        return True
    return False


def _detect_vitepress(soup: BeautifulSoup) -> bool:
    meta = soup.find("meta", attrs={"name": "generator"})
    if meta and "vitepress" in (meta.get("content") or "").lower():
        return True
    if soup.select_one(".VPSidebar") or soup.select_one(".vp-doc"):
        return True
    return False


PRESETS: list[Preset] = [
    Preset(
        name="docusaurus",
        detect=_detect_docusaurus,
        toc_selector="nav.menu",
        content_selector="article",
        noise_selectors=[
            ".theme-doc-toc-mobile",
            ".pagination-nav",
            ".theme-edit-this-page",
            ".theme-doc-footer",
        ],
    ),
    Preset(
        name="mkdocs",
        detect=_detect_mkdocs,
        toc_selector=".md-nav--primary",
        content_selector=".md-content__inner",
        noise_selectors=[
            ".md-footer",
            ".md-search",
            ".md-tabs",
            ".md-nav--secondary",
        ],
    ),
    Preset(
        name="gitbook",
        detect=_detect_gitbook,
        toc_selector=".book-summary",
        content_selector=".page-inner",
        noise_selectors=[
            ".navigation",
            ".book-header",
            ".gitbook-link",
        ],
    ),
    Preset(
        name="sphinx",
        detect=_detect_sphinx,
        toc_selector=".sphinxsidebarwrapper",
        content_selector="div.body",
        noise_selectors=[
            ".related",
            ".sphinxsidebar",
            ".footer",
        ],
    ),
    Preset(
        name="vitepress",
        detect=_detect_vitepress,
        toc_selector=".VPSidebarNav",
        content_selector=".vp-doc",
        noise_selectors=[
            ".VPNav",
            ".VPLocalNav",
            ".VPDocFooter",
        ],
    ),
]


def detect_preset(soup: BeautifulSoup) -> Preset | None:
    """Return the first matching preset, or None if none matches."""
    for preset in PRESETS:
        if preset.detect(soup):
            return preset
    return None


def get_preset(name: str) -> Preset:
    """Return preset by name, raising ValueError if not found."""
    for preset in PRESETS:
        if preset.name == name:
            return preset
    available = ", ".join(p.name for p in PRESETS)
    raise ValueError(f"Unknown preset '{name}'. Available: {available}")
