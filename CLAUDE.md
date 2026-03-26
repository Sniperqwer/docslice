# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**docslice** is a CLI tool that slices documentation websites into semantically-organized Markdown files for use with LLMs (especially NotebookLM). It parses a documentation site's table of contents, generates a structured `docslice.yml` blueprint, then fetches and converts pages into clean Markdown files with hierarchical numbering prefixes (e.g., `00_01_Overview.md`).

## Architecture

The tool is driven by a YAML blueprint file (`docslice.yml`) that defines:
- `project_name`, `base_url`: project metadata
- `config`: global settings (CSS selector, request delay)
- `toc`: nested tree of documentation sections with `title`, `url`, and hierarchical nesting

### Core CLI Commands (V1)

| Command | Purpose |
|---------|---------|
| `docslice gen <url>` | Parse a TOC page and generate `docslice.yml` blueprint |
| `docslice fetch` | Read `docslice.yml`, crawl pages, output numbered Markdown files |

### Key Mechanisms
- **Dynamic numbering**: Hierarchical prefixes generated at fetch time based on TOC order (e.g., parent index `01` + child index `00` → file prefix `01_00_`). No IDs stored in yml.
- **Anti-scraping**: fixed UA, random sleep, simple retry on 429/503
- **Framework presets**: auto-detect Docusaurus, MkDocs, GitBook, Sphinx, VitePress

## Documentation

- Product requirements & vision: [PRD.md](./PRD.md) (in Chinese)
- Technical specification: [tech_spec.md](./tech_spec.md)

## Development Environment

- **Python 环境**：使用 miniconda 管理，环境名 `docslice`（`conda activate docslice`）
- **不要使用** `env311` 或其他环境
- 包安装统一使用 `pip install`，不使用 `conda install`
- GitHub CLI `gh` 已安装，用于 repo 操作

## Development Status

Project is in planning phase.
