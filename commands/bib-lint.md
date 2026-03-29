# /bib-lint - Check Bibliography Format

Validate BibTeX files for format correctness, required fields, and consistency issues.

## Usage

```
/bib-lint [bib-file] [options]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|-----------|
| `bib-file` | Path to BibTeX file (default: references.bib) | Optional |
| `--strict` | Treat all warnings as errors | Optional |
| `--errors-only` | Only show errors, hide warnings and info | Optional |
| `--quiet` | Only show summary, no detailed issues | Optional |
| `--format` | Output format: `text` or `json` (default: text) | Optional |

## Checks Performed

### Entry-Level Checks

| Check | Severity | Description |
|-------|----------|-------------|
| Citation key format | INFO | Key should follow AuthorYear format |
| Citation key spaces | ERROR | Keys should not contain spaces |
| Citation key special chars | WARNING | Keys should only use alphanumeric, `:`, `-`, `_` |
| Required fields | ERROR | Type-specific required fields must exist |
| Recommended fields | WARNING | Common optional fields like DOI, pages |
| Brace balance | ERROR | Opening and closing braces must match |

### Field Format Checks

| Field | Check |
|-------|-------|
| `doi` | Must match pattern `10.xxxx/xxxxx` |
| `url` | Must start with `http://`, `https://`, or `ftp://` |
| `year` | Must be 4 digits |
| `pages` | Should use `--` for ranges, not single `-` |
| `volume` | Should be numeric |
| `number` | Should typically be numeric |
| `issn` | Should match `XXXX-XXXX` format |
| `isbn` | Should be valid ISBN-10 or ISBN-13 |
| `month` | Should use standard abbreviations |

### Cross-Entry Checks

| Check | Severity | Description |
|-------|----------|-------------|
| Duplicate keys | ERROR | Same citation key used multiple times |
| Duplicate DOIs | WARNING | Same DOI in multiple entries |
| Duplicate titles | WARNING | Similar titles may indicate duplicates |
| Journal inconsistency | INFO | Same journal with different name formats |

## Required Fields by Type

| Type | Required Fields |
|------|-----------------|
| `article` | author, title, journal, year |
| `book` | author, title, publisher, year |
| `inproceedings` | author, title, booktitle, year |
| `incollection` | author, title, booktitle, year |
| `phdthesis` | author, title, school, year |
| `techreport` | author, title, institution, year |
| `misc` | (none required) |

## Examples

```bash
# Basic lint check
/bib-lint references.bib

# Strict mode (warnings become errors)
/bib-lint references.bib --strict

# Only show errors
/bib-lint references.bib --errors-only

# JSON output for CI/CD
/bib-lint references.bib --format json

# Quick summary only
/bib-lint references.bib --quiet
```

## Sample Output

```
============================================================
BibTeX Lint Report
============================================================
Total entries: 45
Entries with issues: 12
Total issues: 18
  Errors: 3
  Warnings: 8
  Info: 7

------------------------------------------------------------
ERRORS:
  ✗ [Smith2020Method] Missing required field "journal" for @article entry
  ✗ [Jones2021] Unbalanced braces: 5 opening, 4 closing
  ✗ Duplicate citation key appears 2 times: Wang2022Review

------------------------------------------------------------
WARNINGS:
  ⚠ [Zhang2019] Invalid DOI format: doi.org/10.1234/xyz
  ⚠ [Lee2020] Missing recommended fields: volume, pages, doi
  ⚠ [Author2023] Possible typo in field name: "autthor" → should be "author"

------------------------------------------------------------
INFO:
  ℹ [ref1] Citation key does not follow common convention (AuthorYear format)
  ℹ [Brown2021] Use double hyphen (--) for page ranges, not single: 123-456
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No errors (warnings/info may exist) |
| 1 | Errors found (or warnings in strict mode) |

## CI/CD Integration

```yaml
# GitHub Actions example
- name: Lint BibTeX
  run: python scripts/bib_lint.py references.bib --strict --format json > lint-report.json

- name: Check lint results
  run: |
    if [ $? -ne 0 ]; then
      echo "BibTeX lint failed!"
      cat lint-report.json
      exit 1
    fi
```
