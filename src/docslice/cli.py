"""CLI entrypoint for docslice."""

from __future__ import annotations

import typer

app = typer.Typer(
    help="Slice documentation sites into clean Markdown files for LLM workflows."
)


@app.command()
def gen(
    url: str,
    toc_selector: str | None = typer.Option(None, "--toc-selector"),
    content_selector: str | None = typer.Option(None, "--content-selector"),
    preset: str | None = typer.Option(None, "--preset"),
) -> None:
    """Generate a docslice blueprint from a documentation landing page."""
    from pathlib import Path

    from docslice.generator import generate
    from docslice.utils import create_http_client

    with create_http_client() as client:
        summary = generate(
            url,
            toc_selector=toc_selector,
            content_selector=content_selector,
            preset_name=preset,
            client=client,
            output_path=Path("docslice.yml"),
        )
    summary.print()


@app.command()
def fetch(
    output: str = typer.Option("./output", "--output"),
    delay: float | None = typer.Option(None, "--delay"),
) -> None:
    """Fetch blueprint pages and write Markdown outputs."""
    from pathlib import Path

    from docslice.fetcher import BlueprintError, fetch_all, load_blueprint, validate_blueprint
    from docslice.utils import create_http_client

    bp_path = Path("docslice.yml")

    try:
        blueprint = load_blueprint(bp_path)
    except BlueprintError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2)

    try:
        validate_blueprint(blueprint)
    except BlueprintError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2)

    output_dir = Path(output)

    with create_http_client() as client:
        summary = fetch_all(blueprint, output_dir, delay_override=delay, client=client)

    summary.print()

    if summary.failed:
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
