# Papis Integration Design

**Date:** 2026-04-01
**Version:** 2.0.0
**Target:** Academic researchers managing LaTeX papers and references

## Overview

This design documents the integration of [papis](https://github.com/papis/papis) into the bibliography-skills plugin. The existing `/bib-extractor` implementation will be replaced entirely with a papis-based CLI wrapper, with new `/bib-sync` and `/bib-manage` commands added for comprehensive bibliography management.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                      User Workspace                               │
│  <document>.tex  │  <references>.bib  │  .gitignore         │
│  bibnotes-config.yaml  │  papis.bib  │  *.pdf (gitignored) │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    bib-extractor Command                          │
│  - Replace current bib_extractor.py with papis-based implementation │
│  - Fetch metadata via papis add --from-doi                      │
│  - Download PDF to current directory                             │
│  - Append to papis.bib                                          │
│  - Auto-add *.pdf to .gitignore                                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     PDF Note Subagent                             │
│  - Parse PDF content                                            │
│  - Answer core questions (system, implementation, methods, etc.)  │
│  - Extract key conclusions                                       │
│  - Write to papis note field                                    │
│  - Subagent discarded after completion                           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       bib-sync Command                            │
│  - Parse <document>.tex → extract cited references               │
│  - Compare with papis.bib entries                               │
│  - Tag papis.bib entries with citation order (cite:1, cite:2, ...)│
│  - Auto-fetch missing references via papis                         │
│  - Clear tags from unused references                               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       bib-manage Command                          │
│  - AI agent management + Python utilities                         │
│  - Check duplicate references                                     │
│  - Copy verified references to main.bib                           │
│  - Validate and fix metadata                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### File Structure

```
project/
├── <document>.tex              # Any .tex file (not necessarily main.tex)
├── <references>.bib            # Original BibTeX (synced from papis)
├── papis.bib                  # Papis-managed source of truth (fixed name)
├── bibnotes-config.yaml        # Custom questions config (optional)
├── scripts/
│   ├── bib_extractor.py         # Replaced: papis-based implementation
│   ├── bib_sync.py            # New: sync main.tex ↔ papis
│   └── bib_utils.py           # New: management utilities
└── *.pdf                      # Downloaded PDFs (gitignored)
```

## bib-extractor

### Approach: papis CLI Wrapper

Uses Python subprocess to call `papis` commands directly.

**Pros:**
- Simple to implement, leverages papis's existing CLI
- papis handles all metadata fetching, PDF downloading, database management
- Easy to maintain as papis evolves
- Can use `papis add --from-doi`, `papis update`, `papis export` commands

### Workflow

1. **Input**: DOI, URL, PMID, or arXiv ID
2. **Normalize**: Convert to DOI format if needed
3. **Fetch**: Call `papis add --from-doi <doi> --set tags=extracted --set note=""`
4. **Download PDF**: papis automatically fetches available PDF to current directory
5. **Update .gitignore**: Check for `*.pdf` pattern, append if missing
6. **Export**: Call `papis export --format bibtex > papis.bib`
7. **Launch subagent**: For PDF parsing (see PDF Note Subagent section)

### Command Arguments

| Argument | Description |
|----------|-------------|
| `identifier` | DOI, URL, PMID, or arXiv ID |
| `--input, -i` | Batch input file |
| `--output, -o` | Output BibTeX file (default: papis.bib) |
| `--delay` | Delay between requests |
| `--timeout` | Request timeout |
| `--print-only` | Print without saving |
| `--no-pdf` | Skip PDF download |
| `--no-note` | Skip subagent note parsing |

### .gitignore Handling

```python
def ensure_pdf_gitignored():
    gitignore_path = Path('.gitignore')
    pattern = '*.pdf'
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if pattern not in content:
            with open(gitignore_path, 'a') as f:
                f.write(f'\n{pattern}')
```

## PDF Note Subagent

### Subagent Launch and Lifecycle

```python
def launch_note_subagent(pdf_path: str, doi: str) -> str:
    """
    Launch a subagent to parse PDF and generate note.
    Subagent is discarded after completion to preserve main context.
    """
    prompt = f"""
    Parse the PDF at {pdf_path} and extract information for the papis note field.

    Answer these questions:
    1. What system/approach does this paper use?
    2. What does it implement/achieve?
    3. What methods/algorithms are used?
    4. What are the key results/findings?
    5. What are the limitations or future work?
    6. Extract key conclusions that can be used to correct sentences in main.tex.

    Format as markdown:
    ## System
    ...
    ## Implementation
    ...
    ## Methods
    ...
    ## Results
    ...
    ## Limitations
    ...
    ## Key Conclusions
    ...
    """
    # Launch via Agent tool with isolation
    # Return note content
```

### Core Questions (Fixed)

| Question | Section in Note |
|----------|-----------------|
| What system/approach does this paper use? | `## System` |
| What does it implement/achieve? | `## Implementation` |
| What methods/algorithms are used? | `## Methods` |
| What are the key results/findings? | `## Results` |
| What are the limitations or future work? | `## Limitations` |
| Key conclusions for main.tex | `## Key Conclusions` |

### Custom Questions Config (`bibnotes-config.yaml`)

```yaml
custom_questions:
  - id: datasets
    question: "What datasets were used?"
  - id: reproducibility
    question: "Is the code/data publicly available?"
  - id: related_work
    question: "What related work is cited?"
```

### Subagent Isolation

Use the `Agent` tool with `run_in_background=true`:
- Subagent runs independently
- Returns structured note content
- Main agent context remains clean
- Subagent context is discarded after task completion

### Note Storage

Update papis note field:
```bash
papis update --from-doi <doi> --set note="<markdown content>"
```

## bib-sync

### Workflow

1. Agent scans for main .tex file (guided by skill)
2. Extract bibliography file name from .tex
3. Compile .tex to generate .bbl file
4. Parse .bbl to extract cited citation keys in order
5. Read papis.bib entries
6. Compare and sync:
   - Tag entries found in .bbl with citation order (e.g., tag="cite:1", "cite:2", ...)
   - For missing entries, call papis to fetch
   - Clear tags from entries not in .bbl (so they appear at end when sorted by tag)
7. Export updated papis.bib

### Python Script (`scripts/bib_sync.py`)

```python
def parse_bbl_citations(bbl_path: Path) -> List[str]:
    """Extract citation keys from .bbl file in order."""

def sync_references(tex_path: Path, bib_path: Path, papis_bib_path: Path):
    """Main sync function."""
    # 1. Compile tex to get bbl
    compile_latex(tex_path)

    # 2. Parse cited keys
    cited_keys = parse_bbl_citations(tex_path.with_suffix('.bbl'))

    # 3. Read papis.bib
    papis_entries = read_bibtex(papis_bib_path)
    papis_keys = set(entry['key'] for entry in papis_entries)

    # 4. Find missing
    missing = cited_keys - papis_keys

    # 5. Fetch missing via papis (requires DOI or URL)
    for key in missing:
        fetch_via_papis(key)

    # 6. Tag entries
    for idx, key in enumerate(cited_keys, start=1):
        papis_update(key, tags=[f"cite:{idx}"])

    # 7. Clear tags from unused
    for entry in papis_entries:
        if entry['key'] not in cited_keys:
            papis_update(entry['key'], tags=[])

    # 8. Export
    subprocess.run(['papis', 'export', '--format', 'bibtex'],
                  stdout=open(papis_bib_path, 'w'))
```

### File Detection (Skill-Guided)

The bib-sync skill instructs the agent to:
1. Scan current directory for `.tex` files
2. Ask user which is the main document (if multiple)
3. Extract bibliography filename from `\bibliography{...}` command
4. Proceed with sync using identified files

## bib-manage

### Available Actions

| Action | Description | Python Script |
|---------|-------------|---------------|
| `check-duplicates` | Find duplicate entries in papis.bib | `check_duplicates()` |
| `sync-to-main` | Copy verified references to main.bib with corrected metadata | `sync_to_main()` |
| `validate-metadata` | Check and fix incomplete/incorrect metadata | `validate_metadata()` |
| `cleanup` | Remove unused entries, fix formatting | `cleanup()` |

### Python Utilities (`scripts/bib_utils.py`)

```python
def check_duplicates(papis_bib: Path) -> List[Tuple[str, str]]:
    """
    Find duplicate references by comparing:
    - DOI
    - Title (normalized)
    - Author + Year
    Returns list of duplicate key pairs.
    """

def sync_to_main(papis_bib: Path, main_bib: Path, cited_keys: Set[str]):
    """
    Copy references from papis.bib to main.bib.
    Ensures metadata is correct using papis-verified data.
    Only copies cited references to keep main.bib clean.
    """

def validate_metadata(entry: Dict) -> List[str]:
    """
    Validate a BibTeX entry has required fields.
    Returns list of issues found.
    Required: author, title, journal/year, doi/url
    """

def fix_metadata(entry: Dict) -> Dict:
    """
    Fix common metadata issues:
    - Normalize journal abbreviations
    - Fix DOI format
    - Normalize author names
    """
```

## Dependencies

### Automatic Installation

When installing the bibliography-skills plugin, all dependencies including papis are installed automatically via `requirements.txt`.

### Updated `requirements.txt`

```txt
requests>=2.31.0
papis>=0.14.0
```

### Updated `manifest.json`

```json
{
  "name": "bibliography-skills",
  "version": "2.0.0",
  "description": "Bibliography management with papis integration for Claude Code",
  "author": "fangrh",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/fangrh/bibliography-skills"
  },
  "claude": {
    "commands": [
      "bib-extractor",
      "bib-searcher",
      "bib-sync",
      "bib-manage"
    ],
    "dependencies": [
      "requests",
      "papis"
    ]
  },
  "install": {
    "commands_dir": "claude/commands",
    "scripts_dir": "scripts",
    "dependencies": "requirements.txt"
  }
}
```

## Error Handling

Common errors to handle:

```python
errors = {
    'papis_not_installed': "papis CLI not found. Install with: pip install papis",
    'latex_not_found': "No .tex file found in current directory",
    'bibliography_not_found': "Could not find bibliography file in .tex",
    'compilation_failed': "LaTeX compilation failed. Check .tex for errors",
    'pdf_not_found': "PDF not available for this paper",
    'doi_invalid': "Invalid DOI format",
    'network_error': "Network error: could not fetch metadata",
}
```

## Migration Notes

Since this replaces the entire `bib-extractor` implementation:

1. `papis.bib` becomes the source of truth (not the original .bib file)
2. Original .bib files are preserved but not modified directly
3. First run: user may want to migrate existing references to papis
4. Optional enhancement: `/bib-extractor --migrate-from existing.bib`

## Testing Strategy

```python
# tests/test_bib_extractor.py
def test_papis_add_from_doi():
    """Test that papis add works with DOI."""

def test_gitignore_update():
    """Test .gitignore PDF pattern addition."""

# tests/test_bib_sync.py
def test_bbl_parsing():
    """Test .bbl citation extraction."""

def test_missing_reference_fetch():
    """Test auto-fetch of missing references."""

def test_tagging_order():
    """Test citation order tagging."""

# tests/test_bib_utils.py
def test_duplicate_detection():
    """Test duplicate reference detection."""

def test_sync_to_main():
    """Test syncing to main.bib."""
```

## Implementation Phases

1. **Phase 1**: Replace bib_extractor.py with papis CLI wrapper
2. **Phase 2**: Implement bib_sync.py command
3. **Phase 3**: Implement bib_utils.py utilities
4. **Phase 4**: Create bib-sync and bib-manage command files
5. **Phase 5**: Update manifest and requirements
6. **Phase 6**: Add tests
