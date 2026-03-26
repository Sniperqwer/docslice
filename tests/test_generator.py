from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from docslice.generator import write_blueprint, _dedup_nodes, _make_relative
from docslice.models import Blueprint, Config, TocNode


def _make_blueprint(**kwargs) -> Blueprint:
    defaults = dict(
        project_name="test_project",
        base_url="https://docs.example.com",
        toc=[TocNode(title="Overview", url="/docs/overview")],
    )
    defaults.update(kwargs)
    return Blueprint(**defaults)


# ---------------------------------------------------------------------------
# write_blueprint: field order
# ---------------------------------------------------------------------------

def test_write_blueprint_field_order(tmp_path: Path) -> None:
    bp = _make_blueprint(
        generated_from="https://docs.example.com/",
        config=Config(toc_selector="nav", content_selector="article"),
    )
    out = tmp_path / "docslice.yml"
    write_blueprint(bp, out)

    yaml = YAML()
    data = yaml.load(out)
    keys = list(data.keys())
    assert keys == ["version", "project_name", "base_url", "generated_from", "config", "toc"]


def test_write_blueprint_config_field_order(tmp_path: Path) -> None:
    bp = _make_blueprint(
        config=Config(toc_selector="nav", content_selector="article", delay=2.0),
    )
    out = tmp_path / "docslice.yml"
    write_blueprint(bp, out)

    yaml = YAML()
    data = yaml.load(out)
    cfg_keys = list(data["config"].keys())
    assert cfg_keys == ["toc_selector", "content_selector", "delay"]


def test_write_blueprint_omits_none_fields(tmp_path: Path) -> None:
    bp = _make_blueprint()  # no generated_from, no selectors
    out = tmp_path / "docslice.yml"
    write_blueprint(bp, out)

    yaml = YAML()
    data = yaml.load(out)
    assert "generated_from" not in data
    assert "toc_selector" not in data["config"]
    assert "content_selector" not in data["config"]


def test_write_blueprint_toc_structure(tmp_path: Path) -> None:
    bp = _make_blueprint(
        toc=[
            TocNode(
                title="Getting Started",
                children=[
                    TocNode(title="Overview", url="/docs/overview"),
                ],
            ),
            TocNode(title="Concepts", url="/docs/concepts"),
        ]
    )
    out = tmp_path / "docslice.yml"
    write_blueprint(bp, out)

    yaml = YAML()
    data = yaml.load(out)
    toc = data["toc"]
    assert toc[0]["title"] == "Getting Started"
    assert "url" not in toc[0]
    assert toc[0]["children"][0]["title"] == "Overview"
    assert toc[1]["url"] == "/docs/concepts"


# ---------------------------------------------------------------------------
# _dedup_nodes
# ---------------------------------------------------------------------------

def test_dedup_removes_second_occurrence() -> None:
    nodes = [
        TocNode(title="Page A", url="https://example.com/a"),
        TocNode(title="Page A duplicate", url="https://example.com/a"),
        TocNode(title="Page B", url="https://example.com/b"),
    ]
    deduped, count = _dedup_nodes(nodes)
    assert count == 1
    assert len(deduped) == 2
    assert deduped[0].title == "Page A"
    assert deduped[1].title == "Page B"


def test_dedup_works_across_tree_levels() -> None:
    nodes = [
        TocNode(
            title="Section",
            children=[
                TocNode(title="Page A", url="https://example.com/a"),
            ],
        ),
        TocNode(title="Page A again", url="https://example.com/a"),
    ]
    deduped, count = _dedup_nodes(nodes)
    assert count == 1
    # Top-level duplicate should be removed
    assert len(deduped) == 1
    assert deduped[0].children[0].url == "https://example.com/a"


def test_dedup_does_not_remove_dir_nodes() -> None:
    nodes = [
        TocNode(title="Section 1"),
        TocNode(title="Section 2"),
    ]
    deduped, count = _dedup_nodes(nodes)
    assert count == 0
    assert len(deduped) == 2


# ---------------------------------------------------------------------------
# _make_relative
# ---------------------------------------------------------------------------

def test_make_relative_strips_scheme_and_host() -> None:
    nodes = [TocNode(title="Page", url="https://docs.example.com/docs/intro")]
    result = _make_relative(nodes, "https://docs.example.com")
    assert result[0].url == "/docs/intro"


def test_make_relative_preserves_query() -> None:
    nodes = [TocNode(title="Page", url="https://docs.example.com/docs/intro?v=2")]
    result = _make_relative(nodes, "https://docs.example.com")
    assert result[0].url == "/docs/intro?v=2"


def test_make_relative_leaves_none_urls_intact() -> None:
    nodes = [TocNode(title="Dir")]
    result = _make_relative(nodes, "https://docs.example.com")
    assert result[0].url is None
