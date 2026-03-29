# /bib-note - Generate Notes for Bibliography Entries

Generate concise notes for BibTeX entries with abstracts using LLM. Notes describe the main topic/contribution and what the paper could be cited for.

## Usage

```
/bib-note [bib-file] [options]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|-----------|
| `bib-file` | Path to BibTeX file (default: references.bib) | Optional |
| `--output, -o` | Output BibTeX file (default: overwrite input) | Optional |
| `--dry-run` | Preview changes without modifying file | Optional |
| `--force` | Regenerate notes even if note field exists | Optional |
| `--use-local` | Use local note generation (no API required) | Optional |
| `--model` | Claude model to use (default: claude-3-haiku-20240307) | Optional |
| `--timeout` | API request timeout in seconds (default: 30) | Optional |
| `--verbose, -v` | Show detailed progress | Optional |

## Process

1. **Parse BibTeX file** - Read all entries from the library

2. **For each entry with abstract**:
   - Extract the abstract text
   - Send to Claude API (or use local generation)
   - Generate 2-3 sentence note covering:
     - Main topic/contribution
     - What this paper could be cited for

3. **Update BibTeX entries**:
   - Add or update `note` field
   - Preserve all other fields
   - Create backup before modifying

## Examples

```
# Generate notes for all entries with abstracts
/bib-note references.bib

# Preview changes
/bib-note references.bib --dry-run

# Regenerate all notes (even existing ones)
/bib-note references.bib --force

# Use local generation (no API key needed)
/bib-note references.bib --use-local

# Use specific Claude model
/bib-note references.bib --model claude-3-sonnet-20240229
```

## Output Format

Generated notes follow this format:
```
note = {This paper presents [methodology/technique] for [topic]. Key contribution is [finding]. Useful for citing [specific aspect] in context of [research area].}
```

## Note Generation Methods

### Claude API (Default)
- Requires `ANTHROPIC_API_KEY` environment variable
- Uses haiku model by default (cost-effective)
- Generates high-quality, contextual notes

### Local Generation
- No API key required
- Extracts first sentence from abstract
- Simple but less detailed

## Integration

This command works with:
- `/bib-extractor` - Use `--abstract` to fetch abstracts first
- `/bib-sync` - Sync metadata before generating notes
- `/bib-preview` - Preview notes in formatted output

---

**Full workflow example:**
```bash
# 1. Extract entries with abstracts
/bib-extractor 10.1038/nature12373 --abstract

# 2. Generate notes for entries
/bib-note references.bib --verbose

# 3. Preview the result
/bib-preview references.bib
```
