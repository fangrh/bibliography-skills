# Bibliography Skills for Claude Code

## Overview

This repository provides four Claude Code commands backed by shared Python scripts:

- `/bib-extractor`
- `/bib-searcher`
- `/bib-sync`
- `/bib-manage`

Claude-specific assets live under `claude/`. Codex-specific skills live under `skills/`.

## Installation

### Marketplace

```bash
/plugin marketplace add fangrh/bibliography-skills
/plugin install bibliography-skills@bibliography-skills-marketplace
```

To install a non-default branch, add the branch-qualified marketplace URL first, then run the same `/plugin install bibliography-skills@bibliography-skills-marketplace` command.

### Manual Installation

See [INSTALL.md](INSTALL.md).

## File Layout

- `claude/commands/` - Claude command definitions
- `claude/manifest.json` - Claude plugin manifest
- `scripts/` - shared Python implementations

## License

MIT License
