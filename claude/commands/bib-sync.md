# /bib-sync

Sync LaTeX citations with papis bibliography.

## Usage

```
/bib-sync [options]
```

## Examples

```bash
/bib-sync               # Sync citations in current document
/bib-sync --force       # Force rebuild of cite_order
```

## Notes

Extracts citations from LaTeX files, queries papis library for paper data, and populates the `cite_order` field to track citation counts and recent usage. Requires papis installed and configured with a bibliography database. The `cite_order` field stores semicolon-separated entries in format `paper_id:timestamp:last_position` to enable ranking by paper contribution.
