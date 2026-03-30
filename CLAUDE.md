# Bibliography Skills for Claude Code

## Overview

This repository provides two Claude Code commands backed by shared Python scripts:

- `/bib-extractor`
- `/bib-searcher`

Claude-specific assets live under `claude/`. Codex-specific skills live under `skills/`.

## Installation

### Marketplace

```bash
/plugin marketplace add fangrh/bibliography-skills
/plugin install bibliography-skills@fangrh-bibliography-skills
```

### Manual Installation

See [INSTALL.md](INSTALL.md).

## File Layout

- `claude/commands/` - Claude command definitions
- `claude/manifest.json` - Claude plugin manifest
- `scripts/` - shared Python implementations

## License

MIT License
