"""Content extraction and cleaning from HTML pages."""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

# Noise elements removed from all pages, regardless of preset.
UNIVERSAL_NOISE_SELECTORS: list[str] = [
    "nav",
    "footer",
    "header",
    ".sidebar",
    ".breadcrumb",
    ".breadcrumbs",
    ".pagination",
    ".table-of-contents",
    ".toc",
    ".copy-button",
    ".copy-code-button",
    ".prev-next",
    ".edit-this-page",
    ".edit-link",
    "script",
    "style",
    "iframe",
    "noscript",
]

# Tried in order when no content_selector is configured.
_CONTENT_FALLBACK_CHAIN: list[str] = [
    "article",
    "main",
    "[role='main']",
    ".content",
    "body",
]


class ExtractionError(Exception):
    pass


def extract_content(
    html: str,
    base_url: str,
    *,
    content_selector: str | None = None,
    extra_noise_selectors: list[str] | None = None,
) -> str:
    """Locate the main content node, strip noise, absolutize links.

    Returns a cleaned HTML string ready for Markdown conversion.
    Raises ExtractionError if no content node can be found.
    """
    soup = BeautifulSoup(html, "lxml")

    root = _find_content_root(soup, content_selector)
    if root is None:
        raise ExtractionError("Could not locate any content node in the page.")

    _remove_noise(root, extra_noise_selectors or [])
    _absolutize_links(root, base_url)

    return str(root)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_content_root(
    soup: BeautifulSoup, content_selector: str | None
) -> Tag | None:
    """Find the content root using the priority chain defined in the spec."""
    if content_selector:
        node = soup.select_one(content_selector)
        if node is not None:
            return node

    for selector in _CONTENT_FALLBACK_CHAIN:
        node = soup.select_one(selector)
        if node is not None:
            return node

    return None


def _remove_noise(root: Tag, extra_selectors: list[str]) -> None:
    """Decompose all noise elements from *root* in-place."""
    for selector in UNIVERSAL_NOISE_SELECTORS + extra_selectors:
        for element in root.select(selector):
            element.decompose()


def _absolutize_links(root: Tag, base_url: str) -> None:
    """Convert relative hrefs and img srcs to absolute URLs in-place.

    Pure anchor links (href starting with '#') are left untouched.
    """
    for a_tag in root.find_all("a", href=True):
        href: str = a_tag["href"]
        if href.startswith("#"):
            continue
        a_tag["href"] = urljoin(base_url, href)

    for img_tag in root.find_all("img", src=True):
        img_tag["src"] = urljoin(base_url, img_tag["src"])
