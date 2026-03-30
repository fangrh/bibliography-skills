# Installation Guide for Bibliography Skills

This document covers Claude Code installation. For Codex, use [.codex/INSTALL.md](.codex/INSTALL.md).

## Claude Code Marketplace

```bash
/plugin marketplace add fangrh/bibliography-skills
/plugin install bibliography-skills@fangrh-bibliography-skills
```

The Claude plugin assets are now packaged from `claude/`.

## Claude Code Manual Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/fangrh/bibliography-skills.git
cd bibliography-skills
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Copy Claude Assets

```bash
mkdir -p ~/.claude/commands ~/.claude/scripts
cp claude/commands/* ~/.claude/commands/
cp scripts/bib_extractor.py ~/.claude/scripts/
cp scripts/bib_smart_search.py ~/.claude/scripts/
```

### Step 4: Verify Installation

In Claude Code, run:

```text
/bib-searcher paper.tex
```

## Available Commands

| Command | Description |
|---------|-------------|
| `/bib-extractor` | Extract BibTeX from DOIs, URLs, PMIDs, and arXiv IDs |
| `/bib-searcher` | Analyze text, reuse existing references first, and search for supporting citations |

## Uninstallation

```bash
rm -f ~/.claude/commands/bib-extractor.md
rm -f ~/.claude/commands/bib-searcher.md
rm -f ~/.claude/scripts/bib_extractor.py
rm -f ~/.claude/scripts/bib_smart_search.py
```

## Troubleshooting

**Commands not found in Claude Code**: Ensure the command files are in `~/.claude/commands/`

**Python not found**: Ensure Python 3 is installed and in `PATH`

**requests module not found**: Run `pip install requests`

## License

MIT License
