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

Supported presets (auto-detected): `docusaurus`, `mkdocs`, `gitbook`, `sphinx`, `vitepress`, `mintlify`.

If no preset is detected, pass `--toc-selector` with the CSS selector for the navigation list. Use `--content-selector` to override where the page body is extracted from.

**Example output:**

```
Preset/selector  : docusaurus
Total TOC nodes  : 42
  URL nodes      : 38
  Dir nodes      : 4
Filtered external: 2
Filtered dupes   : 0
Blueprint saved  : docslice.yml
```

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | Blueprint generated successfully |
| `1` | Runtime error (HTTP failure, no usable TOC nodes) |
| `2` | Input error (unknown preset, `--toc-selector` required but missing) |

### `docslice fetch`

```bash
docslice fetch [--output PATH] [--delay FLOAT]
```

Reads `docslice.yml`, assigns hierarchical numeric prefixes to every node, then fetches and converts each page to Markdown. Output files are named like `00_01_Overview.md`.

Options:
- `--output PATH` — output directory (default: `./output`)
- `--delay FLOAT` — seconds between requests; overrides `config.delay` in the blueprint

**Example output:**

```
Fetched : 38/38
Output  : ./output

Note: stale files from previous runs are NOT removed automatically. Clear the output directory manually if you need a clean slate.
```

If some pages fail:

```
Fetched : 35/38
Output  : ./output

Failed (3):
  - Advanced Topics: HTTP 404
  - Changelog: HTTP 503
  - Legacy API: extraction failed
```

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | All pages fetched successfully |
| `1` | One or more pages failed (other pages are still written) |
| `2` | Blueprint missing, unparseable, or structurally invalid |

## Blueprint (`docslice.yml`)

The blueprint describes what to fetch. Edit it to remove sections you don't need before running `fetch`.

```yaml
version: 1
project_name: "docs_example_com"
base_url: "https://docs.example.com"
generated_from: "https://docs.example.com/guide"
config:
  toc_selector: "nav.sidebar"      # CSS selector for the navigation list
  content_selector: "article"      # CSS selector for the page body
  delay: 1.5                       # seconds between requests
toc:
  - title: "Getting Started"
    children:
      - title: "Overview"
        url: "/guide/overview"
      - title: "Quickstart"
        url: "/guide/quickstart"
  - title: "Core Concepts"
    url: "/guide/core"
    children:
      - title: "How It Works"
        url: "/guide/how-it-works"
```

**Node types:**

| Type | `url` | `children` | Behaviour |
|------|-------|------------|-----------|
| Directory node | absent | present | Participates in numbering; no file written |
| Leaf node | present | absent | Fetched and written to a file |
| Parent with URL | present | present | Both the parent and children are fetched |

## Output format

Files are written to `./output/` by default. Each file:

- Is prefixed with a stable hierarchical number (e.g. `01_00_`, `02_03_`)
- Begins with a `<!-- source: <url> -->` comment
- Contains clean Markdown with headings, code blocks, tables, and links preserved
- Does **not** include navigation bars, sidebars, footers, or in-page TOCs

Example output directory:

```
output/
├── 00_00_overview.md
├── 00_01_quickstart.md
├── 01_core.md
└── 01_00_how-it-works.md
```

## Known limitations (V1)

- Only static HTML pages are supported; JavaScript-rendered content is not fetched.
- Images are linked (remote URLs preserved) but not downloaded.
- No incremental sync — re-running `fetch` overwrites existing files, stale files are not removed.

## Development

```bash
conda activate docslice
pip install -e ".[dev]"
pytest
```
