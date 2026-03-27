"""CLI behaviour tests: exit codes, summary output, and error messages."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from docslice.cli import app
from docslice.fetcher import BlueprintError, FetchSummary
from docslice.generator import GenerationSummary

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_http_client():
    """Context-manager-compatible mock for create_http_client()."""
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=MagicMock())
    m.__exit__ = MagicMock(return_value=False)
    return m


def _gen_summary() -> GenerationSummary:
    return GenerationSummary(
        preset_name="docusaurus",
        total_nodes=5,
        url_nodes=4,
        dir_nodes=1,
        filtered_external=1,
        filtered_duplicates=0,
        blueprint_path=Path("docslice.yml"),
    )


# ---------------------------------------------------------------------------
# gen command
# ---------------------------------------------------------------------------

class TestGenCommand:
    def test_gen_success_exits_0(self):
        """Successful gen exits 0 and prints a summary to stdout."""
        with patch("docslice.generator.generate", return_value=_gen_summary()):
            with patch("docslice.utils.create_http_client", return_value=_mock_http_client()):
                result = runner.invoke(app, ["gen", "https://example.com"])

        assert result.exit_code == 0
        assert "Preset/selector" in result.output
        assert "Blueprint saved" in result.output
        assert "docusaurus" in result.output

    def test_gen_runtime_error_exits_1(self):
        """gen exits 1 on a runtime error (e.g. HTTP failure) with an error message to stderr."""
        def _http_fail(*_args, **_kwargs):
            typer.echo("Error: failed to fetch https://example.com: Connection refused", err=True)
            raise typer.Exit(code=1)

        with patch("docslice.generator.generate", side_effect=_http_fail):
            with patch("docslice.utils.create_http_client", return_value=_mock_http_client()):
                result = runner.invoke(app, ["gen", "https://example.com"])

        assert result.exit_code == 1
        assert "Error: failed to fetch" in result.stderr

    def test_gen_no_preset_no_selector_exits_2(self):
        """gen exits 2 when no preset is detected and --toc-selector is absent."""
        def _no_selector(*_args, **_kwargs):
            typer.echo(
                "Error: No preset detected and --toc-selector was not provided.", err=True
            )
            raise typer.Exit(code=2)

        with patch("docslice.generator.generate", side_effect=_no_selector):
            with patch("docslice.utils.create_http_client", return_value=_mock_http_client()):
                result = runner.invoke(app, ["gen", "https://example.com"])

        assert result.exit_code == 2
        assert "No preset detected" in result.stderr

    def test_gen_unknown_preset_exits_2(self):
        """gen exits 2 when --preset names an unknown preset."""
        def _bad_preset(*_args, **_kwargs):
            typer.echo("Error: Unknown preset: 'bogus'. Available: ...", err=True)
            raise typer.Exit(code=2)

        with patch("docslice.generator.generate", side_effect=_bad_preset):
            with patch("docslice.utils.create_http_client", return_value=_mock_http_client()):
                result = runner.invoke(app, ["gen", "https://example.com", "--preset", "bogus"])

        assert result.exit_code == 2
        assert "Error:" in result.stderr

    def test_gen_empty_toc_exits_1(self):
        """gen exits 1 when the selector matches no usable TOC nodes."""
        def _empty_toc(*_args, **_kwargs):
            typer.echo(
                "Error: No usable TOC nodes found under selector '.sidebar'.", err=True
            )
            raise typer.Exit(code=1)

        with patch("docslice.generator.generate", side_effect=_empty_toc):
            with patch("docslice.utils.create_http_client", return_value=_mock_http_client()):
                result = runner.invoke(
                    app, ["gen", "https://example.com", "--toc-selector", ".sidebar"]
                )

        assert result.exit_code == 1
        assert "No usable TOC nodes" in result.stderr


# ---------------------------------------------------------------------------
# fetch command
# ---------------------------------------------------------------------------

class TestFetchCommand:
    def test_fetch_missing_blueprint_exits_2(self):
        """fetch exits 2 when docslice.yml is absent."""
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["fetch"])

        assert result.exit_code == 2
        assert "Error:" in result.stderr

    def test_fetch_invalid_yaml_exits_2(self):
        """fetch exits 2 when docslice.yml contains unparseable YAML."""
        with runner.isolated_filesystem():
            Path("docslice.yml").write_text(": bad yaml [\n", encoding="utf-8")
            result = runner.invoke(app, ["fetch"])

        assert result.exit_code == 2
        assert "Error:" in result.stderr

    def test_fetch_validation_error_exits_2(self):
        """fetch exits 2 when blueprint loads but fails semantic validation."""
        mock_bp = MagicMock()
        with runner.isolated_filesystem():
            with patch("docslice.fetcher.load_blueprint", return_value=mock_bp):
                with patch(
                    "docslice.fetcher.validate_blueprint",
                    side_effect=BlueprintError("Duplicate URL in blueprint: '/docs/intro'"),
                ):
                    result = runner.invoke(app, ["fetch"])

        assert result.exit_code == 2
        assert "Error:" in result.stderr

    def test_fetch_all_success_exits_0(self):
        """fetch exits 0 and prints a summary when all pages succeed."""
        mock_bp = MagicMock()
        mock_summary = FetchSummary(
            total=3, succeeded=3, output_dir=Path("./output")
        )
        with runner.isolated_filesystem():
            with patch("docslice.fetcher.load_blueprint", return_value=mock_bp):
                with patch("docslice.fetcher.validate_blueprint"):
                    with patch("docslice.fetcher.fetch_all", return_value=mock_summary):
                        result = runner.invoke(app, ["fetch"])

        assert result.exit_code == 0
        assert "Fetched" in result.output
        assert "3/3" in result.output

    def test_fetch_partial_failure_exits_1(self):
        """fetch exits 1 and lists failed pages when some fetches fail."""
        mock_bp = MagicMock()
        mock_summary = FetchSummary(
            total=4,
            succeeded=3,
            failed=[("Missing Page", "HTTP 404")],
            output_dir=Path("./output"),
        )
        with runner.isolated_filesystem():
            with patch("docslice.fetcher.load_blueprint", return_value=mock_bp):
                with patch("docslice.fetcher.validate_blueprint"):
                    with patch("docslice.fetcher.fetch_all", return_value=mock_summary):
                        result = runner.invoke(app, ["fetch"])

        assert result.exit_code == 1
        assert "Failed" in result.output
        assert "Missing Page" in result.output
        assert "HTTP 404" in result.output

    def test_fetch_all_fail_exits_1(self):
        """fetch exits 1 when every page fails."""
        mock_bp = MagicMock()
        mock_summary = FetchSummary(
            total=2,
            succeeded=0,
            failed=[("Page A", "HTTP 503"), ("Page B", "HTTP 503")],
            output_dir=Path("./output"),
        )
        with runner.isolated_filesystem():
            with patch("docslice.fetcher.load_blueprint", return_value=mock_bp):
                with patch("docslice.fetcher.validate_blueprint"):
                    with patch("docslice.fetcher.fetch_all", return_value=mock_summary):
                        result = runner.invoke(app, ["fetch"])

        assert result.exit_code == 1
        assert "0/2" in result.output

    def test_fetch_respects_output_option(self):
        """fetch passes the --output path to fetch_all."""
        mock_bp = MagicMock()
        mock_summary = FetchSummary(
            total=1, succeeded=1, output_dir=Path("./custom_out")
        )
        captured_kwargs: dict = {}

        def _capture(*args, **kwargs):
            captured_kwargs.update(kwargs)
            captured_kwargs["output_dir"] = args[1] if len(args) > 1 else kwargs.get("output_dir")
            return mock_summary

        with runner.isolated_filesystem():
            with patch("docslice.fetcher.load_blueprint", return_value=mock_bp):
                with patch("docslice.fetcher.validate_blueprint"):
                    with patch("docslice.fetcher.fetch_all", side_effect=_capture):
                        result = runner.invoke(app, ["fetch", "--output", "./custom_out"])

        assert result.exit_code == 0
        assert captured_kwargs.get("output_dir") == Path("./custom_out")

    def test_fetch_respects_delay_option(self):
        """fetch passes the --delay value to fetch_all as delay_override."""
        mock_bp = MagicMock()
        mock_summary = FetchSummary(total=1, succeeded=1, output_dir=Path("./output"))
        captured_kwargs: dict = {}

        def _capture(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return mock_summary

        with runner.isolated_filesystem():
            with patch("docslice.fetcher.load_blueprint", return_value=mock_bp):
                with patch("docslice.fetcher.validate_blueprint"):
                    with patch("docslice.fetcher.fetch_all", side_effect=_capture):
                        result = runner.invoke(app, ["fetch", "--delay", "2.5"])

        assert result.exit_code == 0
        assert captured_kwargs.get("delay_override") == 2.5
