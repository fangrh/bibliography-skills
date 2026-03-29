# Bibliography Skills for Claude Code and Codex

## Overview

This project provides two focused bibliography tools for Claude Code and Codex: `bib-extractor` for metadata capture and normalization, and `bib-searcher` for sentence-aware citation search and document updates.

## Installation

### Via Plugin Market (Recommended)

```bash
/plugin add market
/plugin install bibliography-skills
```

### Manual Installation

See [INSTALL.md](INSTALL.md) for detailed instructions.

## Commands

| Command | Description |
|---------|-------------|
| `/bib-extractor` | Extract and normalize BibTeX from DOIs, URLs, PMIDs, arXiv IDs |
| `/bib-searcher` | Read a document, reuse existing references first, then search and suggest or update citations |

## Quick Start

```bash
# Extract a paper by DOI
/bib-extractor 10.1038/s41586-021-03926-0

# Analyze and update a draft
/bib-searcher paper.tex
```

## Documentation

- [README.md](README.md) - Full documentation
- [INSTALL.md](INSTALL.md) - Installation guide
- [SKILL.md](SKILL.md) - Portable skill definition for Claude Code and Codex

## License

MIT License
