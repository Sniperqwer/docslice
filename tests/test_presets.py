from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from docslice.presets import PRESETS, detect_preset, get_preset


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


# ---------------------------------------------------------------------------
# detect_preset
# ---------------------------------------------------------------------------

def test_detect_docusaurus_via_meta() -> None:
    soup = _soup('<meta name="generator" content="Docusaurus v3.0">')
    preset = detect_preset(soup)
    assert preset is not None
    assert preset.name == "docusaurus"


def test_detect_docusaurus_via_class() -> None:
    soup = _soup('<nav class="navbar"><a class="navbar__brand">Logo</a></nav>')
    preset = detect_preset(soup)
    assert preset is not None
    assert preset.name == "docusaurus"


def test_detect_mkdocs_via_meta() -> None:
    soup = _soup('<meta name="generator" content="mkdocs 1.5">')
    preset = detect_preset(soup)
    assert preset is not None
    assert preset.name == "mkdocs"


def test_detect_mkdocs_via_class() -> None:
    soup = _soup('<div class="md-container"><nav class="md-nav"></nav></div>')
    preset = detect_preset(soup)
    assert preset is not None
    assert preset.name == "mkdocs"


def test_detect_gitbook_via_meta() -> None:
    soup = _soup('<meta name="generator" content="GitBook">')
    preset = detect_preset(soup)
    assert preset is not None
    assert preset.name == "gitbook"


def test_detect_sphinx_via_meta() -> None:
    soup = _soup('<meta name="generator" content="Sphinx 7.0">')
    preset = detect_preset(soup)
    assert preset is not None
    assert preset.name == "sphinx"


def test_detect_vitepress_via_meta() -> None:
    soup = _soup('<meta name="generator" content="VitePress v1.0">')
    preset = detect_preset(soup)
    assert preset is not None
    assert preset.name == "vitepress"


def test_detect_mintlify_via_meta() -> None:
    soup = _soup('<meta name="generator" content="Mintlify"/>')
    preset = detect_preset(soup)
    assert preset is not None
    assert preset.name == "mintlify"


def test_detect_mintlify_via_dom() -> None:
    soup = _soup(
        '<div id="sidebar-content"></div>'
        '<div class="mdx-content"></div>'
    )
    preset = detect_preset(soup)
    assert preset is not None
    assert preset.name == "mintlify"


def test_detect_returns_none_for_unknown_site() -> None:
    soup = _soup("<html><body><p>Just a page</p></body></html>")
    assert detect_preset(soup) is None


# ---------------------------------------------------------------------------
# get_preset
# ---------------------------------------------------------------------------

def test_get_preset_returns_correct_preset() -> None:
    for preset in PRESETS:
        result = get_preset(preset.name)
        assert result.name == preset.name


def test_get_preset_raises_on_unknown_name() -> None:
    with pytest.raises(ValueError, match="Unknown preset"):
        get_preset("nonexistent")


# ---------------------------------------------------------------------------
# Preset structure
# ---------------------------------------------------------------------------

def test_all_presets_have_required_fields() -> None:
    for preset in PRESETS:
        assert preset.name
        assert preset.toc_selector
        assert preset.content_selector
        assert isinstance(preset.noise_selectors, list)
        assert callable(preset.detect)
