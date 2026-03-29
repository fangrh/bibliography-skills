# /bib-track - Track Citation Usage in Documents

Scan LaTeX/Markdown documents for citation patterns and update BibTeX entries with usage tracking in the `annotation` field.

## Usage

```
/bib-track [bib-file] --documents [files] [options]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|-----------|
| `bib-file` | Path to BibTeX file (default: references.bib) | Optional |
| `--documents, -d` | Document files to scan (.tex, .md, or directory) | Yes |
| `--output, -o` | Output BibTeX file (default: overwrite input) | Optional |
| `--dry-run` | Preview changes without modifying file | Optional |
| `--find-uncited` | Only list entries that are never cited | Optional |
| `--verbose, -v` | Show detailed progress | Optional |

## Supported Citation Formats

### LaTeX
- `\cite{key}`, `\citep{key}`, `\citet{key}`
- `\parencite{key}`, `\textcite{key}`
- `\autocite{key}`, `\bibentry{key}`, `\fullcite{key}`
- Multiple citations: `\cite{key1,key2,key3}`

### Markdown
- `[@key]` - Pandoc-style citations
- `@key` - At-word-boundary citations
- `[Author Year]` - Limited support

## Process

1. **Parse BibTeX file** - Read all entries from the library

2. **Scan documents** - Extract all citations with context:
   - For each citation found, capture the surrounding sentence
   - Store file location and line number

3. **Update annotations**:
   ```
   annotation = {Cited in paper.tex:
   1. Introduction: "Phonons play a central role [cite] in condensed matter."
   2. Methods: "We use the technique from [cite] to measure..."
   }
   ```

4. **Identify uncited entries** - Find entries never used in any document

## Examples

```
# Track citations in a single file
/bib-track references.bib --documents paper.tex

# Track citations in multiple files
/bib-track references.bib --documents *.tex

# Scan entire directory
/bib-track references.bib --documents .

# Find uncited entries only
/bib-track references.bib --documents . --find-uncited

# Preview changes
/bib-track references.bib --documents paper.tex --dry-run
```

## Annotation Format

The `annotation` field is updated with:
```
annotation = {
  Cited in [filename]:
  1. [Section/context]: "[sentence with citation]"
  2. [Section/context]: "[another sentence]"
}
```

## Use Cases

### Track how references are used
```
/bib-track references.bib --documents *.tex --verbose
```

### Clean up unused references
```
# First, find uncited entries
/bib-track references.bib --documents . --find-uncited

# Then remove them (manually or with other tools)
```

### Prepare for validation
```
# 1. Track citations
/bib-track references.bib --documents paper.tex

# 2. Validate citations with /bib-sync
/bib-sync references.bib --validate-citations
```

## Integration

This command works with:
- `/bib-sync --validate-citations` - Validate cited contexts
- `/bib-extractor --abstract` - Add abstracts for validation
- `/bib-note` - Add notes to help with citation decisions

---

**Full workflow example:**
```bash
# 1. Extract references with abstracts
/bib-extractor 10.1038/nature12373 --abstract

# 2. Track where they're cited
/bib-track references.bib --documents paper.tex

# 3. Validate citation support
/bib-sync references.bib --validate-citations --verbose
```
