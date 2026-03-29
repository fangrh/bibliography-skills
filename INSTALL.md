# Installation Guide for Bibliography Skills

## Quick Install (Plugin Market)

```bash
# Add the market source
/plugin add market

# Install the bibliography skills
/plugin install bibliography-skills
```

## Manual Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/bibliography-skills.git
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

## Troubleshooting

**Commands not found**: Ensure the command files are in `~/.claude/commands/`

**Python not found**: Ensure Python 3 is installed and in PATH

**requests module not found**: Run `pip install requests`

## License

MIT License - See LICENSE file for details
