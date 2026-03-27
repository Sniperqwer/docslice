"""Tests for fetch orchestration, numbering, blueprint loading, and validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from docslice.fetcher import (
    BlueprintError,
    FetchSummary,
    assign_prefixes,
    fetch_all,
    load_blueprint,
    validate_blueprint,
)
from docslice.models import Blueprint, TocNode

BASE = "https://example.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bp(**kwargs) -> Blueprint:
    defaults: dict = {
        "project_name": "test",
        "base_url": BASE,
        "toc": [TocNode(title="Page", url="/page")],
    }
    defaults.update(kwargs)
    return Blueprint(**defaults)


def _response(
    html: str = "<html><body><article><p>Content</p></article></body></html>",
    status: int = 200,
    url: str = f"{BASE}/page",
) -> httpx.Response:
    request = httpx.Request("GET", url)
    return httpx.Response(status_code=status, text=html, request=request)


# ---------------------------------------------------------------------------
# assign_prefixes — flat list
# ---------------------------------------------------------------------------

def test_prefixes_flat_list() -> None:
    nodes = [
        TocNode(title="A", url="/a"),
        TocNode(title="B", url="/b"),
        TocNode(title="C", url="/c"),
    ]
    pairs = assign_prefixes(nodes)
    assert [(n.title, p) for n, p in pairs] == [
        ("A", "00"),
        ("B", "01"),
        ("C", "02"),
    ]


def test_prefixes_nested_matches_spec_example() -> None:
    nodes = [
        TocNode(title="Getting Started", url=None, children=[
            TocNode(title="Overview", url="/docs/overview"),
            TocNode(title="Quickstart", url="/docs/quickstart"),
        ]),
        TocNode(title="Core Concepts", url="/docs/core-concepts", children=[
            TocNode(title="How It Works", url="/docs/how-it-works"),
        ]),
    ]
    pairs = assign_prefixes(nodes)
    assert [(n.title, p) for n, p in pairs] == [
        ("Overview", "00_00"),
        ("Quickstart", "00_01"),
        ("Core Concepts", "01"),
        ("How It Works", "01_00"),
    ]


def test_dir_node_excluded_from_output_but_participates_in_numbering() -> None:
    nodes = [
        TocNode(title="Dir", url=None, children=[
            TocNode(title="Child", url="/child"),
        ]),
    ]
    pairs = assign_prefixes(nodes)
    assert len(pairs) == 1
    assert pairs[0][0].title == "Child"
    assert pairs[0][1] == "00_00"


def test_prefixes_deeply_nested() -> None:
    nodes = [
        TocNode(title="A", url="/a", children=[
            TocNode(title="B", url="/b", children=[
                TocNode(title="C", url="/c"),
            ]),
        ]),
    ]
    pairs = assign_prefixes(nodes)
    assert [(n.title, p) for n, p in pairs] == [
        ("A", "00"),
        ("B", "00_00"),
        ("C", "00_00_00"),
    ]


def test_second_top_level_node_gets_01() -> None:
    nodes = [
        TocNode(title="Intro", url=None),
        TocNode(title="Guide", url="/guide"),
    ]
    pairs = assign_prefixes(nodes)
    assert pairs[0][1] == "01"


def test_prefixes_beyond_nine_use_two_digits() -> None:
    nodes = [TocNode(title=str(i), url=f"/{i}") for i in range(11)]
    pairs = assign_prefixes(nodes)
    assert pairs[10][1] == "10"


# ---------------------------------------------------------------------------
# validate_blueprint
# ---------------------------------------------------------------------------

def test_validate_ok() -> None:
    validate_blueprint(_bp())  # must not raise


def test_validate_duplicate_url_raises() -> None:
    bp = _bp(toc=[
        TocNode(title="A", url="/same"),
        TocNode(title="B", url="/same"),
    ])
    with pytest.raises(BlueprintError, match="Duplicate URL"):
        validate_blueprint(bp)


def test_validate_nested_duplicate_raises() -> None:
    bp = _bp(toc=[
        TocNode(title="Parent", url="/page", children=[
            TocNode(title="Child", url="/page"),
        ]),
    ])
    with pytest.raises(BlueprintError, match="Duplicate URL"):
        validate_blueprint(bp)


def test_validate_distinct_urls_ok() -> None:
    bp = _bp(toc=[
        TocNode(title="A", url="/a"),
        TocNode(title="B", url="/b"),
    ])
    validate_blueprint(bp)  # must not raise


# ---------------------------------------------------------------------------
# load_blueprint
# ---------------------------------------------------------------------------

def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(BlueprintError, match="not found"):
        load_blueprint(tmp_path / "nonexistent.yml")


def test_load_valid_blueprint(tmp_path: Path) -> None:
    yaml_text = (
        "version: 1\n"
        "project_name: myproject\n"
        "base_url: https://example.com\n"
        "config:\n"
        "  delay: 2.0\n"
        "toc:\n"
        "  - title: Overview\n"
        "    url: /overview\n"
    )
    bp_file = tmp_path / "docslice.yml"
    bp_file.write_text(yaml_text)
    bp = load_blueprint(bp_file)
    assert bp.project_name == "myproject"
    assert bp.toc[0].url == "/overview"
    assert bp.config.delay == 2.0


def test_load_invalid_yaml_raises(tmp_path: Path) -> None:
    bp_file = tmp_path / "docslice.yml"
    bp_file.write_text(": : : broken :")
    with pytest.raises(BlueprintError):
        load_blueprint(bp_file)


def test_load_non_mapping_yaml_raises(tmp_path: Path) -> None:
    bp_file = tmp_path / "docslice.yml"
    bp_file.write_text("- just\n- a\n- list\n")
    with pytest.raises(BlueprintError, match="YAML mapping"):
        load_blueprint(bp_file)


def test_load_missing_required_field_raises(tmp_path: Path) -> None:
    yaml_text = (
        "version: 1\n"
        "base_url: https://example.com\n"  # no project_name
        "toc:\n"
        "  - title: A\n"
        "    url: /a\n"
    )
    bp_file = tmp_path / "docslice.yml"
    bp_file.write_text(yaml_text)
    with pytest.raises(BlueprintError):
        load_blueprint(bp_file)


# ---------------------------------------------------------------------------
# fetch_all — basic flow
# ---------------------------------------------------------------------------

def test_fetch_all_writes_file(tmp_path: Path) -> None:
    bp = _bp(toc=[TocNode(title="My Page", url="/page")])
    mock_client = MagicMock()
    mock_client.get.return_value = _response(url=f"{BASE}/page")

    with patch("docslice.fetcher.polite_sleep"):
        summary = fetch_all(bp, tmp_path, delay_override=0.0, client=mock_client)

    assert summary.total == 1
    assert summary.succeeded == 1
    assert not summary.failed

    files = list(tmp_path.glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text()
    assert "<!-- source:" in content
    assert content.startswith("<!-- source:")


def test_fetch_all_file_naming_uses_prefix_and_slug(tmp_path: Path) -> None:
    bp = _bp(toc=[
        TocNode(title="Getting Started", url=None, children=[
            TocNode(title="Overview", url="/overview"),
        ]),
    ])
    mock_client = MagicMock()
    mock_client.get.return_value = _response(url=f"{BASE}/overview")

    with patch("docslice.fetcher.polite_sleep"):
        fetch_all(bp, tmp_path, delay_override=0.0, client=mock_client)

    files = list(tmp_path.glob("*.md"))
    assert len(files) == 1
    assert files[0].name == "00_00_overview.md"


def test_fetch_all_source_comment_uses_final_url(tmp_path: Path) -> None:
    bp = _bp(toc=[TocNode(title="Page", url="/page")])
    final_url = f"{BASE}/page-redirected"
    mock_client = MagicMock()
    mock_client.get.return_value = _response(url=final_url)

    with patch("docslice.fetcher.polite_sleep"):
        fetch_all(bp, tmp_path, delay_override=0.0, client=mock_client)

    content = next(tmp_path.glob("*.md")).read_text()
    assert f"<!-- source: {final_url} -->" in content


# ---------------------------------------------------------------------------
# fetch_all — failure handling
# ---------------------------------------------------------------------------

def test_fetch_continues_after_http_error(tmp_path: Path) -> None:
    bp = _bp(toc=[
        TocNode(title="Page A", url="/a"),
        TocNode(title="Page B", url="/b"),
    ])
    mock_client = MagicMock()
    mock_client.get.side_effect = [
        _response(status=404, url=f"{BASE}/a"),
        _response(url=f"{BASE}/b"),
    ]

    with patch("docslice.fetcher.polite_sleep"):
        summary = fetch_all(bp, tmp_path, delay_override=0.0, client=mock_client)

    assert summary.total == 2
    assert summary.succeeded == 1
    assert len(summary.failed) == 1
    assert summary.failed[0][0] == "Page A"
    assert "404" in summary.failed[0][1]


def test_fetch_failure_does_not_affect_numbering(tmp_path: Path) -> None:
    bp = _bp(toc=[
        TocNode(title="A", url="/a"),
        TocNode(title="B", url="/b"),
        TocNode(title="C", url="/c"),
    ])
    mock_client = MagicMock()
    mock_client.get.side_effect = [
        _response(status=500, url=f"{BASE}/a"),
        _response(url=f"{BASE}/b"),
        _response(url=f"{BASE}/c"),
    ]

    with patch("docslice.fetcher.polite_sleep"):
        fetch_all(bp, tmp_path, delay_override=0.0, client=mock_client)

    names = {f.name for f in tmp_path.glob("*.md")}
    assert any(name.startswith("01_") for name in names), names
    assert any(name.startswith("02_") for name in names), names


def test_fetch_network_error_recorded_in_failed(tmp_path: Path) -> None:
    bp = _bp(toc=[TocNode(title="Page", url="/page")])
    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")

    with patch("docslice.fetcher.polite_sleep"):
        summary = fetch_all(bp, tmp_path, delay_override=0.0, client=mock_client)

    assert summary.succeeded == 0
    assert len(summary.failed) == 1


# ---------------------------------------------------------------------------
# fetch_all — retry logic
# ---------------------------------------------------------------------------

def test_retries_on_429(tmp_path: Path) -> None:
    bp = _bp(toc=[TocNode(title="Page", url="/page")])
    mock_client = MagicMock()
    mock_client.get.side_effect = [
        _response(status=429, url=f"{BASE}/page"),
        _response(url=f"{BASE}/page"),
    ]

    with patch("docslice.fetcher.polite_sleep"), patch("time.sleep"):
        summary = fetch_all(bp, tmp_path, delay_override=0.0, client=mock_client)

    assert summary.succeeded == 1
    assert mock_client.get.call_count == 2


def test_retries_on_503(tmp_path: Path) -> None:
    bp = _bp(toc=[TocNode(title="Page", url="/page")])
    mock_client = MagicMock()
    mock_client.get.side_effect = [
        _response(status=503, url=f"{BASE}/page"),
        _response(status=503, url=f"{BASE}/page"),
        _response(url=f"{BASE}/page"),
    ]

    with patch("docslice.fetcher.polite_sleep"), patch("time.sleep"):
        summary = fetch_all(bp, tmp_path, delay_override=0.0, client=mock_client)

    assert summary.succeeded == 1
    assert mock_client.get.call_count == 3


def test_stops_retrying_after_max_retries(tmp_path: Path) -> None:
    bp = _bp(toc=[TocNode(title="Page", url="/page")])
    mock_client = MagicMock()
    # Return 429 four times (initial + 3 retries = 4 total calls)
    mock_client.get.return_value = _response(status=429, url=f"{BASE}/page")

    with patch("docslice.fetcher.polite_sleep"), patch("time.sleep"):
        summary = fetch_all(bp, tmp_path, delay_override=0.0, client=mock_client)

    assert summary.succeeded == 0
    assert mock_client.get.call_count == 4  # initial + 3 retries


# ---------------------------------------------------------------------------
# fetch_all — delay override
# ---------------------------------------------------------------------------

def test_delay_override_used_instead_of_blueprint_delay(tmp_path: Path) -> None:
    from docslice.models import Config
    bp = _bp()
    bp = Blueprint(
        project_name=bp.project_name,
        base_url=bp.base_url,
        toc=bp.toc,
        config=Config(delay=99.0),
    )
    mock_client = MagicMock()
    mock_client.get.return_value = _response()

    sleep_calls: list[float] = []

    def fake_sleep(d: float) -> float:
        sleep_calls.append(d)
        return d

    with patch("docslice.fetcher.polite_sleep", side_effect=fake_sleep):
        fetch_all(bp, tmp_path, delay_override=0.1, client=mock_client)

    assert all(d <= 0.2 for d in sleep_calls), sleep_calls
