# Bibliography Skills for Claude Code and Codex

## Overview

This project provides Zotero-like bibliography extraction and management tools for Claude Code and Codex. It includes Claude command files and a portable `SKILL.md` that Codex can discover from `~/.agents/skills/<skill-name>/`.

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
| `/bib-extractor` | Extract BibTeX from DOIs, URLs, PMIDs, arXiv IDs |
| `/bib-preview` | Generate LaTeX preview from BibTeX files |
| `/bib-search` | Search and extract bibliography from web |
| `/bib-sync` | Sync library with online sources, update metadata |

## Quick Start

```bash
# Extract a paper by DOI
/bib-extractor 10.1038/s41586-021-03926-0

# Preview your bibliography
/bib-preview references.bib

# Search for papers
/bib-search "quantum computing"

# Sync library with online sources
/bib-sync references.bib
```

## Documentation

- [README.md](README.md) - Full documentation
- [INSTALL.md](INSTALL.md) - Installation guide
- [SKILL.md](SKILL.md) - Portable skill definition for Claude Code and Codex

## License

MIT License
