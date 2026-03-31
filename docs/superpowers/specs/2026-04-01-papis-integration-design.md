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
│  - Fetch metadata via papis add --from doi                      │
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
│  - Track citation order in papis.bib via custom 'cite_order' field    │
│  - Auto-fetch missing references via papis                         │
│  - Unused references have no cite_order field                            │
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

### Papis Library Configuration

Papis uses a library path to store its database. By default, this is `~/Documents/papers/`. For this plugin, we configure papis to use the current project directory:

```bash
papis -l . add --from doi <doi>
```

The `-l .` flag sets the library to the current directory, ensuring:
- PDFs are downloaded to the current directory
- `papis export --format bibtex` exports from the correct location
- papis.bib is created/updated in the current directory

Users can override this by setting `PAPIS_LIB_DIR` environment variable or creating a local `.papis` config file.

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
- Can use `papis add --from doi`, `papis update`, `papis export` commands

### Workflow

1. **Input**: DOI, URL, PMID, or arXiv ID
2. **Normalize**: Convert to DOI format if needed
3. **Fetch**: Call `papis -l . add --from doi <doi> --set tags=extracted --set note=""`
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

The subagent is launched using Claude Code's `Agent` tool with the following mechanism:

```python
def launch_note_subagent(pdf_path: str, doi: str) -> str:
    """
    Launch a subagent to parse PDF and generate note.
    The subagent runs in isolation to preserve main context.
    """
    # Read PDF content for context
    pdf_content = read_pdf_for_context(pdf_path)

    # Launch subagent with focused prompt
    result = Agent(
        subagent_type="general-purpose",
        prompt=f"""
        Parse the PDF at {pdf_path} and extract information for the papis note field.

        Answer these questions:
        1. What system/approach does this paper use?
        2. What does it implement/achieve?
        3. What methods/algorithms are used?
        4. What are the key results/findings?
        5. What are the limitations or future work?
        6. Extract key conclusions that can be used to correct sentences in main.tex.

        Format as markdown with sections:
        ## System
        ## Implementation
        ## Methods
        ## Results
        ## Limitations
        ## Key Conclusions
        """,
        run_in_background=True
    )

    # Subagent context is discarded after completion
    return result
```

Key points:
- Subagent runs independently with its own context window
- PDF content is provided as context to the subagent
- Subagent returns only the structured note content
- Main agent context is not polluted with PDF parsing details
- Error handling: if subagent fails, log error and continue without note

### Note Storage

Update papis note field:
```bash
papis update --from doi <doi> --set note="<markdown content>"
```

## bib-sync

### Workflow

1. Agent scans for main .tex file (guided by skill)
2. Extract bibliography file name from .tex
3. Compile .tex to generate .bbl file
4. Parse .bbl to extract cited citation keys in order
5. Read papis.bib entries
6. Compare and sync:
   - Add 'cite_order' field to entries found in .bbl (e.g., cite_order=1, cite_order=2, ...)
   - Remove 'cite_order' field from entries not in .bbl (so they appear at end when sorted)
   - For missing entries, call papis to fetch
7. Export updated papis.bib

### Python Script (`scripts/bib_sync.py`)

```python
def parse_bbl_citations(bbl_path: Path) -> List[str]:
    """Extract citation keys from .bbl file in order."""

def sync_references(tex_path: Path, bib_path: Path, papis_bib_path: Path):
    """Main sync function."""
    # 1. Compile tex to get bbl
    # Try pdflatex first, fallback to latex
    compile_latex(tex_path, compilers=['pdflatex', 'xelatex', 'lualatex'])

    # 2. Parse cited keys
    cited_keys = parse_bbl_citations(tex_path.with_suffix('.bbl'))

    # 3. Read papis.bib
    papis_entries = read_bibtex(papis_bib_path)
    papis_keys = set(entry['key'] for entry in papis_entries)

    # 4. Find missing
    missing = cited_keys - papis_keys

    # 5. Fetch missing via papis
    # For each missing key, try to find in original .bib for DOI
    # If no DOI, ask user to provide or search by title/author
    for key in missing:
        doi = extract_doi_from_original_bib(bib_path, key)
        if doi:
            papis_add(f'papis -l . add --from doi {doi}')
        else:
            # Ask user for DOI/URL or search by title/author
            print(f"Missing DOI for citation key: {key}")
            user_input = input("Enter DOI/URL, or press Enter to skip: ")
            if user_input:
                papis_add(f'papis -l . add --from doi {user_input}')

    # 6. Add cite_order field to cited entries
    for idx, key in enumerate(cited_keys, start=1):
        papis_update(key, extra_fields={'cite_order': str(idx)})

    # 7. Remove cite_order field from unused entries
    for entry in papis_entries:
        if entry['key'] not in cited_keys:
            papis_update(entry['key'], remove_fields=['cite_order'])

    # 8. Sort and export papis.bib by cite_order
    sorted_entries = sorted(papis_entries,
                         key=lambda e: int(e.get('cite_order', '9999')))
    write_bibtex(sorted_entries, papis_bib_path)
```

### File Detection (Skill-Guided)

The bib-sync skill instructs the agent to:
1. Scan current directory for `.tex` files
2. Ask user which is the main document (if multiple)
3. Extract bibliography filename(s) from .tex:
   - `\bibliography{filename}` - Standard LaTeX
   - `\addbibresource{filename}` - BibLaTeX
   - Handle multiple files: `\bibliography{ref1,ref2}`
   - Handle subdirectories: `\bibliography{refs/refs}`
4. If multiple bibliography files found, ask user which to sync or sync all
5. Proceed with sync using identified files

```python
def extract_bibliography_files(tex_content: str) -> List[str]:
    """
    Extract bibliography files from LaTeX content.
    Handles multiple formats and multiple files.
    """
    # Match \bibliography{...}
    bib_pattern = r'\\bibliography\s*\{([^}]+)\}'
    matches = re.findall(bib_pattern, tex_content)

    # Match \addbibresource{...} (BibLaTeX)
    addbib_pattern = r'\\addbibresource\s*\{([^}]+)\}'
    matches.extend(re.findall(addbib_pattern, tex_content))

    # Parse comma-separated lists
    files = []
    for match in matches:
        for f in match.split(','):
            f = f.strip()
            if f:
                # Add .bib if not present
                if not f.endswith('.bib'):
                    f = f + '.bib'
                files.append(f)

    return files
```

## bib-manage

### Command Syntax

```bash
/bib-manage <action> [options]
```

### Available Actions

| Action | Description | Python Script | Example |
|---------|-------------|---------------|---------|
| `check-duplicates` | Find duplicate entries in papis.bib | `check_duplicates()` | `/bib-manage check-duplicates` |
| `sync-to-main` | Copy verified references to main.bib with corrected metadata | `sync_to_main()` | `/bib-manage sync-to-main --tex-file main.tex --output refs.bib` |
| `validate-metadata` | Check and fix incomplete/incorrect metadata | `validate_metadata()` | `/bib-manage validate-metadata papis.bib` |
| `cleanup` | Remove unused entries, fix formatting | `cleanup()` | `/bib-manage cleanup --remove-uncited --main main.tex` |
| `migrate` | Import existing .bib file into papis | `migrate_bib()` | `/bib-manage migrate --from existing.bib` |

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

## Papis Initialization

On first use in a new project, the system initializes a papis library in the current directory:

```python
def ensure_papis_initialized():
    """
    Ensure papis library exists in current directory.
    Creates minimal .papis config if needed.
    """
    papis_dir = Path('.papis')
    if not papis_dir.exists():
        papis_dir.mkdir()
        print("Initialized papis library in current directory")
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

## Migration Strategy

### Migrating Existing Bibliographies

For users with existing `.bib` files, provide migration capability:

```bash
/bib-manage migrate --from existing.bib
```

This command:
1. Reads the existing .bib file
2. Calls `papis -l . add --from bibtex existing.bib` for each entry
3. Fetches PDFs for entries with DOIs
4. Exports new `papis.bib`
5. Preserves original .bib as backup

### Migration Notes

1. `papis.bib` becomes the source of truth (not the original .bib file)
2. Original .bib files are preserved but not modified directly
3. After migration, user can delete or archive original .bib files

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
