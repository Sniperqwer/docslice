from __future__ import annotations

import pytest
from pydantic import ValidationError

from docslice.models import Blueprint, Config, TocNode


def test_toc_node_requires_non_empty_title() -> None:
    with pytest.raises(ValidationError):
        TocNode(title="   ")


def test_config_defaults_are_applied() -> None:
    config = Config()
    assert config.delay == 1.5
    assert config.toc_selector is None
    assert config.content_selector is None


def test_config_rejects_non_positive_delay() -> None:
    with pytest.raises(ValidationError):
        Config(delay=0)


def test_blueprint_builds_with_nested_nodes() -> None:
    blueprint = Blueprint(
        project_name="docslice",
        base_url="https://example.com",
        toc=[
            TocNode(
                title="Getting Started",
                children=[TocNode(title="Overview", url="/docs/overview")],
            )
        ],
    )

    assert blueprint.version == 1
    assert blueprint.config.delay == 1.5
    assert blueprint.toc[0].children[0].url == "/docs/overview"


def test_blueprint_rejects_empty_toc() -> None:
    with pytest.raises(ValidationError):
        Blueprint(
            project_name="docslice",
            base_url="https://example.com",
            toc=[],
        )


def test_blueprint_rejects_invalid_version() -> None:
    with pytest.raises(ValidationError):
        Blueprint(
            version=2,
            project_name="docslice",
            base_url="https://example.com",
            toc=[TocNode(title="Overview", url="/docs/overview")],
        )

