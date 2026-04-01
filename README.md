# Bibliography Skills

Bibliography helpers for Codex and Claude Code. The repository exposes four maintained workflows:

- `bib-extractor`: normalize a known DOI, URL, PMID, or arXiv ID into BibTeX
- `bib-searcher`: audit a draft sentence by sentence, reuse the local bibliography first, and search for supporting papers only when needed
- `bib-sync`: sync LaTeX citations with the papis bibliography
- `bib-manage`: maintain the papis bibliography and clean metadata

## Platforms

- Codex: see [.codex/INSTALL.md](.codex/INSTALL.md)
- Claude Code: see [INSTALL.md](INSTALL.md)

## Repository Layout

```text
bibliography-skills/
  .codex/                  # Codex installation docs
  claude/                  # Claude plugin and marketplace assets
  skills/                  # Codex-discovered skills
    bib-extractor/
    bib-searcher/
  scripts/                 # Shared Python implementations
```

This mirrors the `superpowers` pattern: Codex consumes `skills/`, Claude consumes `claude/`, and shared logic stays out of the platform wrappers.

## Codex

Codex should symlink the repository's `skills/` directory into `~/.agents/skills/bibliography-skills`. After restart, Codex will discover:

- `bib-extractor`
- `bib-searcher`

Quick install prompt:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/fangrh/bibliography-skills/refs/heads/main/.codex/INSTALL.md
```

## Claude Code

Claude plugin assets now live under `claude/`:

- `claude/commands/`
- `claude/manifest.json`
- `claude/packages/bibliography-skills/manifest.json`
- `claude/marketplace.json`

Marketplace install remains:

```bash
/plugin marketplace add fangrh/bibliography-skills
/plugin install bibliography-skills@bibliography-skills-marketplace
```

To install a non-default branch, add the branch-qualified marketplace URL first, then run the same install command.

Manual installation copies files from `claude/commands/` and shared scripts from `scripts/`.

## Version Sync

Release metadata sync:

```bash
npm run sync-version
# or
python3 scripts/sync_version.py 1.0.2
```

This keeps the repository package metadata, Claude plugin metadata, marketplace metadata, and the sibling marketplace repo in sync.

## License

MIT
