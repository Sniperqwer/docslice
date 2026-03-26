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
    _ = (url, toc_selector, content_selector, preset)
    typer.echo("gen is not implemented yet")
    raise typer.Exit(code=1)


@app.command()
def fetch(
    output: str = typer.Option("./output", "--output"),
    delay: float | None = typer.Option(None, "--delay"),
) -> None:
    """Fetch blueprint pages and write Markdown outputs."""
    _ = (output, delay)
    typer.echo("fetch is not implemented yet")
    raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
