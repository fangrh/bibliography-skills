# Bibliography Skills for Codex

Guide for using bibliography skills with OpenAI Codex via native skill discovery.

## Quick Install

Tell Codex:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/fangrh/bibliography-skills/refs/heads/main/.codex/INSTALL.md
```

## Manual Installation

### Prerequisites

- OpenAI Codex CLI
- Git
- Python 3

### Steps

1. Clone the repo:
   ```bash
   git clone https://github.com/fangrh/bibliography-skills.git ~/.codex/bibliography-skills
   ```

2. Install Python dependencies:
   ```bash
   cd ~/.codex/bibliography-skills
   pip install -r requirements.txt
   ```

3. Expose the Codex skills directory:
   ```bash
   mkdir -p ~/.agents/skills
   ln -s ~/.codex/bibliography-skills/skills ~/.agents/skills/bibliography-skills
   ```

4. Restart Codex.

### Windows

Use a junction instead of a symlink:

```powershell
git clone https://github.com/fangrh/bibliography-skills.git "$env:USERPROFILE\.codex\bibliography-skills"
Set-Location "$env:USERPROFILE\.codex\bibliography-skills"
pip install -r requirements.txt
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"
cmd /c mklink /J "$env:USERPROFILE\.agents\skills\bibliography-skills" "$env:USERPROFILE\.codex\bibliography-skills\skills"
```

## How It Works

Codex scans `~/.agents/skills/` at startup, parses `SKILL.md` frontmatter, and loads matching skills on demand. This repository exposes two Codex skills through one repository-level symlink:

```text
~/.agents/skills/bibliography-skills/ -> ~/.codex/bibliography-skills/skills/
```

The skills are:

- `bib-extractor`
- `bib-searcher`

## Usage

After restart, ask Codex to use the skills with prompts like:

- `Use bib-extractor to add DOI 10.1038/s41586-021-03926-0 to references.bib`
- `Use bib-searcher to search draft.tex and update citations using references.bib first`

## Updating

```bash
cd ~/.codex/bibliography-skills && git pull
```

If the symlink already points to `skills/`, Codex will pick up the updated skill files after restart.

## Uninstalling

```bash
rm ~/.agents/skills/bibliography-skills
```

Optionally delete the clone:

```bash
rm -rf ~/.codex/bibliography-skills
```
