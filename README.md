# Bibliography Skills for Codex

Installation guide for using Bibliography Skills with OpenAI Codex via native skill discovery.

## Quick Install

Tell Codex:

```text
Clone this repo to ~/.codex/bibliography-skills, symlink it into ~/.agents/skills/bibliography-skills, install requirements.txt, and tell me when to restart Codex.
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

3. Create the skills symlink:
   ```bash
   mkdir -p ~/.agents/skills
   ln -s ~/.codex/bibliography-skills ~/.agents/skills/bibliography-skills
   ```

4. Restart Codex.

### Windows

Use a junction instead of a symlink:

```powershell
git clone https://github.com/fangrh/bibliography-skills.git "$env:USERPROFILE\.codex\bibliography-skills"
Set-Location "$env:USERPROFILE\.codex\bibliography-skills"
pip install -r requirements.txt
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"
cmd /c mklink /J "$env:USERPROFILE\.agents\skills\bibliography-skills" "$env:USERPROFILE\.codex\bibliography-skills"
```

## Verify Installation

After restart, ask Codex:

```text
Use bib-extractor to add DOI 10.1038/s41586-021-03926-0 to references.bib
```

If Codex does not find the skill:

1. Verify the symlink: `ls -la ~/.agents/skills/bibliography-skills`
2. Check the files exist: `ls ~/.codex/bibliography-skills`
3. Reinstall dependencies: `cd ~/.codex/bibliography-skills && pip install -r requirements.txt`
4. Restart Codex again

## How It Works

Codex scans `~/.agents/skills/` at startup, reads each `SKILL.md`, and loads matching skills on demand. This repository becomes visible to Codex through a single symlink:

```text
~/.agents/skills/bibliography-skills/ -> ~/.codex/bibliography-skills/
```

The main Codex skill definition lives in `SKILL.md`, and optional UI metadata lives in `agents/openai.yaml`.

## Basic Usage

After restart, ask Codex to use the skill with prompts like:

- `Use bib-extractor to add DOI 10.1038/s41586-021-03926-0 to references.bib`
- `Use bib-extractor to add these URLs to my bibliography file`
- `Use bib-extractor to clean up metadata in references.bib`

You can also run the helper script directly:

```bash
python3 ~/.codex/bibliography-skills/scripts/bib_extractor.py --print-only 10.1038/s41586-021-03926-0
```

## Updating

```bash
cd ~/.codex/bibliography-skills && git pull
```

If the symlink already points to this clone, Codex will continue using the updated files after restart.

## Uninstalling

```bash
rm ~/.agents/skills/bibliography-skills
```

Optionally delete the clone:

```bash
rm -rf ~/.codex/bibliography-skills
```

**Windows (PowerShell):**

```powershell
Remove-Item "$env:USERPROFILE\.agents\skills\bibliography-skills"
Remove-Item -Recurse -Force "$env:USERPROFILE\.codex\bibliography-skills"
```

## Troubleshooting

### Windows junction issues

If junction creation fails, try PowerShell as administrator.

## Repository Structure

- `SKILL.md`: skill definition discovered by Codex
- `agents/openai.yaml`: Codex skill metadata
- `scripts/`: helper scripts used by the skill
- `commands/`: Claude-oriented command files kept for cross-platform support

## License

MIT
