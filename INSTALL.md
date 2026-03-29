# Installation Guide for Bibliography Skills

This repository supports both Claude Code and Codex installations.

## Quick Install (Marketplace)

```bash
# Add the marketplace
/plugin marketplace add fangrh/bibliography-skills

# Install the bibliography skills
/plugin install bibliography-skills@fangrh-bibliography-skills
```

## Manual Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/fangrh/bibliography-skills.git
cd bibliography-skills
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Copy Commands to Claude Code

```bash
# Create commands directory if it doesn't exist
mkdir -p ~/.claude/commands

# Copy command files
cp commands/* ~/.claude/commands/

# Copy scripts
cp scripts/* ~/.claude/scripts/
```

### Step 4: Install SKILL.md (Optional)

```bash
# Copy to project directory if working on a specific project
cp SKILL.md ./

# Or copy to global skills directory
mkdir -p ~/.claude/skills
cp SKILL.md ~/.claude/skills/bib-extractor.md
```

## Codex Installation

Codex discovers skills from `~/.agents/skills/<skill-name>/SKILL.md`.

### Step 1: Install the Repository as a Skill Folder

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/fangrh/bibliography-skills.git ~/.agents/skills/bibliography-skills
cd ~/.agents/skills/bibliography-skills
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Restart Codex

Restart Codex so it rescans `~/.agents/skills/` and picks up the new `SKILL.md`.

## Verification

Test the installation:

```bash
# Test bib-extractor
/bib-extractor --help

# Test bib-preview
/bib-preview --help

# Test bib-search
/bib-search --help
```

For Codex, verify by asking it to use the skill from any workspace after restart:

```text
Use bib-extractor to add DOI 10.1038/s41586-021-03926-0 to references.bib
```

## Available Commands

| Command | Description |
|---------|-------------|
| `/bib-extractor` | Extract BibTeX from DOIs, URLs, PMIDs, arXiv IDs |
| `/bib-preview` | Generate LaTeX preview from BibTeX files |
| `/bib-search` | Search and extract bibliography from web |

## Uninstallation

```bash
# Remove command files
rm ~/.claude/commands/bib-extractor.md
rm ~/.claude/commands/bib-preview.md
rm ~/.claude/commands/bib-search.md

# Remove scripts
rm ~/.claude/scripts/bib_extractor.py
```

For Codex:

```bash
rm -rf ~/.agents/skills/bibliography-skills
```

## Troubleshooting

**Commands not found in Claude Code**: Ensure the command files are in `~/.claude/commands/`

**Skill not found in Codex**: Ensure the repo is installed at `~/.agents/skills/bibliography-skills` and restart Codex

**Python not found**: Ensure Python 3 is installed and in PATH

**requests module not found**: Run `pip install requests`

## License

MIT License - See LICENSE file for details
