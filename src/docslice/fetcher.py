"""Blueprint fetcher: read docslice.yml, crawl pages, write Markdown files."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin

import httpx
import typer
from ruamel.yaml import YAML

from docslice.converter import html_to_markdown
from docslice.extractor import ExtractionError, extract_content
from docslice.models import Blueprint, TocNode
from docslice.utils import polite_sleep, slugify_title


class BlueprintError(Exception):
    pass


@dataclass
class FetchSummary:
    total: int
    succeeded: int
    failed: list[tuple[str, str]] = field(default_factory=list)  # (title, reason)
    output_dir: Path = field(default_factory=lambda: Path("./output"))

    def print(self) -> None:
        typer.echo(f"Fetched : {self.succeeded}/{self.total}")
        typer.echo(f"Output  : {self.output_dir}")
        if self.failed:
            typer.echo(f"\nFailed ({len(self.failed)}):")
            for title, reason in self.failed:
                typer.echo(f"  - {title}: {reason}")
        typer.echo(
            "\nNote: stale files from previous runs are NOT removed automatically."
            " Clear the output directory manually if you need a clean slate.",
            err=True,
        )


def load_blueprint(path: Path) -> Blueprint:
    """Parse *path* into a Blueprint model. Raises BlueprintError on any failure."""
    if not path.exists():
        raise BlueprintError(f"Blueprint file not found: {path}")

    yaml = YAML()
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.load(fh)
    except Exception as exc:
        raise BlueprintError(f"Failed to parse YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise BlueprintError("Blueprint file must be a YAML mapping at the top level.")

    try:
        return Blueprint(**data)
    except Exception as exc:
        raise BlueprintError(f"Invalid blueprint structure: {exc}") from exc


def validate_blueprint(blueprint: Blueprint) -> None:
    """Check blueprint for semantic validity. Raises BlueprintError on failure."""
    seen: set[str] = set()
    _validate_nodes(blueprint.toc, blueprint.base_url, seen)


def _validate_nodes(
    nodes: list[TocNode], base_url: str, seen: set[str]
) -> None:
    for node in nodes:
        if node.url is not None:
            abs_url = urljoin(base_url, node.url)
            if abs_url in seen:
                raise BlueprintError(
                    f"Duplicate URL in blueprint: {node.url!r} (node: {node.title!r})"
                )
            seen.add(abs_url)
        _validate_nodes(node.children, base_url, seen)


def assign_prefixes(
    nodes: list[TocNode], parent_prefix: str | None = None
) -> list[tuple[TocNode, str]]:
    """Return ``(node, prefix)`` pairs for every URL-bearing node in DFS order.

    All nodes participate in numbering; only nodes with a URL are included in
    the output list.  Prefixes use two-digit zero-padded indices joined by ``_``.
    """
    result: list[tuple[TocNode, str]] = []
    for i, node in enumerate(nodes):
        index_str = f"{i:02d}"
        prefix = f"{parent_prefix}_{index_str}" if parent_prefix is not None else index_str
        if node.url is not None:
            result.append((node, prefix))
        result.extend(assign_prefixes(node.children, prefix))
    return result


def fetch_all(
    blueprint: Blueprint,
    output_dir: Path,
    *,
    delay_override: float | None = None,
    client: httpx.Client,
) -> FetchSummary:
    """Fetch all URL nodes from *blueprint* and write numbered Markdown files."""
    delay = delay_override if delay_override is not None else blueprint.config.delay
    pairs = assign_prefixes(blueprint.toc)

    output_dir.mkdir(parents=True, exist_ok=True)

    summary = FetchSummary(total=len(pairs), succeeded=0, output_dir=output_dir)
    content_selector = blueprint.config.content_selector

    for node, prefix in pairs:
        abs_url = urljoin(blueprint.base_url, node.url)

        # --- fetch ---
        try:
            response = _fetch_with_retry(client, abs_url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            summary.failed.append(
                (node.title, f"HTTP {exc.response.status_code}")
            )
            polite_sleep(delay)
            continue
        except httpx.HTTPError as exc:
            summary.failed.append((node.title, str(exc)))
            continue

        final_url = str(response.url)

        # --- extract ---
        try:
            content_html = extract_content(
                response.text,
                final_url,
                content_selector=content_selector,
            )
        except ExtractionError as exc:
            summary.failed.append((node.title, f"Extraction failed: {exc}"))
            polite_sleep(delay)
            continue

        # --- convert ---
        md_body = html_to_markdown(content_html)

        # --- write ---
        slug = slugify_title(node.title)
        filename = f"{prefix}_{slug}.md"
        file_path = output_dir / filename
        file_path.write_text(
            f"<!-- source: {final_url} -->\n\n{md_body}\n",
            encoding="utf-8",
        )

        summary.succeeded += 1
        polite_sleep(delay)

    return summary


def _fetch_with_retry(
    client: httpx.Client, url: str, *, max_retries: int = 3
) -> httpx.Response:
    """Fetch *url*, retrying up to *max_retries* times on 429 / 503."""
    response = client.get(url)
    for _ in range(max_retries):
        if response.status_code not in (429, 503):
            break
        time.sleep(5)
        response = client.get(url)
    return response
