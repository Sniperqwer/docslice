# docslice

Slice documentation websites into clean, numbered Markdown files for LLM workflows (e.g. NotebookLM).

## Workflow

```
docslice gen <url>       # parse TOC → generate docslice.yml blueprint
# manually trim docslice.yml
docslice fetch           # crawl pages → write numbered Markdown files
```

## Installation

```bash
pip install docslice
```

## Usage

### `docslice gen`

```bash
docslice gen <url> [--toc-selector "..."] [--content-selector "..."] [--preset NAME]
```

Fetches the given URL, detects the documentation framework, parses the table of contents, and writes a `docslice.yml` blueprint in the current directory.

Supported presets: `docusaurus`, `mkdocs`, `gitbook`, `sphinx`, `vitepress`.

### `docslice fetch`

```bash
docslice fetch [--output PATH] [--delay FLOAT]
```

Reads `docslice.yml`, assigns hierarchical numeric prefixes to every node, then fetches and converts each page to Markdown. Output files are named like `00_01_Overview.md`.

## Output format

Files are written to `./output/` by default. Each file:

- Is prefixed with a stable hierarchical number (e.g. `01_00_`, `02_03_`)
- Begins with a `<!-- source: <url> -->` comment
- Contains clean Markdown with headings, code blocks, tables, and links preserved

## Development

```bash
conda activate docslice
pip install -e ".[dev]"
pytest
```
