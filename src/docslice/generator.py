"""Blueprint generation: fetch TOC page → parse → write docslice.yml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx
import typer
from bs4 import BeautifulSoup
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from slugify import slugify

from docslice.models import Blueprint, Config, TocNode
from docslice.parser import parse_toc
from docslice.presets import Preset, detect_preset, get_preset


@dataclass
class GenerationSummary:
    preset_name: str
    total_nodes: int
    url_nodes: int
    dir_nodes: int
    filtered_external: int
    filtered_duplicates: int
    blueprint_path: Path

    def print(self) -> None:
        typer.echo(f"Preset/selector  : {self.preset_name}")
        typer.echo(f"Total TOC nodes  : {self.total_nodes}")
        typer.echo(f"  URL nodes      : {self.url_nodes}")
        typer.echo(f"  Dir nodes      : {self.dir_nodes}")
        typer.echo(f"Filtered external: {self.filtered_external}")
        typer.echo(f"Filtered dupes   : {self.filtered_duplicates}")
        typer.echo(f"Blueprint saved  : {self.blueprint_path}")


def generate(
    url: str,
    *,
    toc_selector: str | None = None,
    content_selector: str | None = None,
    preset_name: str | None = None,
    client: httpx.Client,
    output_path: Path = Path("docslice.yml"),
) -> GenerationSummary:
    """Fetch *url*, parse its TOC, and write a blueprint to *output_path*."""

    # 1. Fetch entry page
    try:
        response = client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        typer.echo(f"Error: failed to fetch {url}: {exc}", err=True)
        raise typer.Exit(code=1)

    final_url = str(response.url)
    soup = BeautifulSoup(response.text, "lxml")

    # 2. Derive base_url from final (post-redirect) URL
    parsed_final = urlparse(final_url)
    base_url = f"{parsed_final.scheme}://{parsed_final.netloc}"

    # 3. Resolve preset
    preset: Preset | None
    if preset_name is not None:
        try:
            preset = get_preset(preset_name)
        except ValueError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=2)
        detected_name = preset.name
    else:
        preset = detect_preset(soup)
        detected_name = preset.name if preset else "manual selector"

    # 4. Resolve toc_selector (user > preset)
    effective_toc_selector = toc_selector or (preset.toc_selector if preset else None)
    if effective_toc_selector is None:
        typer.echo(
            "Error: No preset detected and --toc-selector was not provided.",
            err=True,
        )
        raise typer.Exit(code=2)

    # 5. Resolve content_selector (user > preset)
    effective_content_selector = content_selector or (
        preset.content_selector if preset else None
    )

    # 6. Parse TOC
    parse_result = parse_toc(soup, effective_toc_selector, base_url)
    if not parse_result.nodes:
        typer.echo(
            f"Error: No usable TOC nodes found under selector '{effective_toc_selector}'.",
            err=True,
        )
        raise typer.Exit(code=1)

    # 7. Dedup across entire tree
    deduped_nodes, dup_count = _dedup_nodes(parse_result.nodes)

    # 8. Convert absolute URLs → relative paths for blueprint storage
    relative_nodes = _make_relative(deduped_nodes, base_url)

    # 9. Derive project_name from hostname
    hostname = parsed_final.netloc
    project_name = slugify(hostname, separator="_") or "project"

    # 10. Build Blueprint
    config = Config(
        toc_selector=effective_toc_selector,
        content_selector=effective_content_selector,
    )
    blueprint = Blueprint(
        project_name=project_name,
        base_url=base_url,
        generated_from=final_url,
        config=config,
        toc=relative_nodes,
    )

    # 11. Write blueprint
    write_blueprint(blueprint, output_path)

    # 12. Compute summary stats
    url_count = _count_url_nodes(relative_nodes)
    dir_count = _count_dir_nodes(relative_nodes)

    return GenerationSummary(
        preset_name=detected_name,
        total_nodes=url_count + dir_count,
        url_nodes=url_count,
        dir_nodes=dir_count,
        filtered_external=parse_result.filtered_external,
        filtered_duplicates=dup_count,
        blueprint_path=output_path,
    )


def write_blueprint(blueprint: Blueprint, path: Path) -> None:
    """Serialize *blueprint* to *path* using ruamel.yaml (preserves field order)."""
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 4096  # prevent line wrapping

    data = _to_ordered_map(blueprint)
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_ordered_map(blueprint: Blueprint) -> CommentedMap:
    """Convert Blueprint → CommentedMap with spec-mandated field order."""
    data = CommentedMap()
    data["version"] = blueprint.version
    data["project_name"] = blueprint.project_name
    data["base_url"] = blueprint.base_url
    if blueprint.generated_from is not None:
        data["generated_from"] = blueprint.generated_from

    cfg = CommentedMap()
    if blueprint.config.toc_selector is not None:
        cfg["toc_selector"] = blueprint.config.toc_selector
    if blueprint.config.content_selector is not None:
        cfg["content_selector"] = blueprint.config.content_selector
    cfg["delay"] = blueprint.config.delay
    data["config"] = cfg

    data["toc"] = _toc_to_seq(blueprint.toc)
    return data


def _toc_to_seq(nodes: list[TocNode]) -> CommentedSeq:
    seq = CommentedSeq()
    for node in nodes:
        item = CommentedMap()
        item["title"] = node.title
        if node.url is not None:
            item["url"] = node.url
        if node.children:
            item["children"] = _toc_to_seq(node.children)
        seq.append(item)
    return seq


def _dedup_nodes(nodes: list[TocNode]) -> tuple[list[TocNode], int]:
    """Remove duplicate URLs from the tree (keep first occurrence)."""
    seen: set[str] = set()
    dup_count = 0

    def _walk(node_list: list[TocNode]) -> list[TocNode]:
        nonlocal dup_count
        result: list[TocNode] = []
        for node in node_list:
            if node.url is not None:
                if node.url in seen:
                    dup_count += 1
                    continue
                seen.add(node.url)
            result.append(
                TocNode(
                    title=node.title,
                    url=node.url,
                    children=_walk(node.children),
                )
            )
        return result

    return _walk(nodes), dup_count


def _make_relative(nodes: list[TocNode], base_url: str) -> list[TocNode]:
    """Convert absolute URLs to relative paths (path + query, no scheme/host)."""
    result: list[TocNode] = []
    for node in nodes:
        rel_url: str | None = None
        if node.url is not None:
            parsed = urlparse(node.url)
            path = parsed.path
            rel_url = f"{path}?{parsed.query}" if parsed.query else path
        result.append(
            TocNode(
                title=node.title,
                url=rel_url,
                children=_make_relative(node.children, base_url),
            )
        )
    return result


def _count_url_nodes(nodes: list[TocNode]) -> int:
    return sum(
        (1 if n.url is not None else 0) + _count_url_nodes(n.children)
        for n in nodes
    )


def _count_dir_nodes(nodes: list[TocNode]) -> int:
    return sum(
        (1 if n.url is None else 0) + _count_dir_nodes(n.children)
        for n in nodes
    )
