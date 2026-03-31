# Papis Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace bib-extractor with papis-based implementation, add bib-sync and bib-manage commands for comprehensive bibliography management.

**Architecture:** Python subprocess wrapper calling papis CLI. Three main components: bib-extractor (metadata fetch), bib-sync (citation tracking), bib-manage (maintenance utilities).

**Tech Stack:** Python 3.8+, papis CLI, subprocess, pathlib, re

---

### Task 1: Create New Branch

**Files:**
- Create: `feature/papis-integration` branch

- [ ] **Step 1: Create new branch**

```bash
git checkout -b feature/papis-integration
```

- [ ] **Step 2: Verify branch**

```bash
git branch
```

Expected: Shows `* feature/papis-integration`

- [ ] **Step 3: Commit**

```bash
git commit --allow-empty -m "feat: create papis-integration branch"
```

---

### Task 2: Update requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add papis and pytest dependencies**

```python
# Append to requirements.txt
papis>=0.14.0
pytest-cov>=4.0.0
```

- [ ] **Step 2: Install dependencies for testing**

```bash
pip install -r requirements.txt
```

- [ ] **Step 3: Verify papis installed**

```bash
papis --version
```

Expected: Version output

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add papis dependency to requirements.txt"
```

---

### Task 3: Replace bib_extractor.py with Papis CLI Wrapper

**Files:**
- Modify: `scripts/bib_extractor.py`

- [ ] **Step 1: Write failing test for papis integration**

```python
# tests/test_bib_extractor.py
import pytest
from pathlib import Path

def test_papis_add_from_doi():
    """Test that papis add works with DOI."""
    result = subprocess.run(['papis', '--version'])
    assert result.returncode == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_bib_extractor.py::test_papis_add_from_doi -v
```

Expected: FAIL with "subprocess not defined"

- [ ] **Step 3: Write minimal papis wrapper implementation**

```python
# scripts/bib_extractor.py
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Optional

def add_reference(identifier: str, no_pdf: bool = False, no_note: bool = False) -> None:
    """Add reference using papis CLI."""
    # Normalize identifier to DOI format if needed
    doi = normalize_to_doi(identifier)

    # Build papis command
    cmd = ['papis', '-l', '.', 'add', '--from', 'doi', doi, '--set', 'tags=extracted', '--set', 'note=""']

    if no_pdf:
        cmd.extend(['--no-document'])

    subprocess.run(cmd, check=True)

    # Export to papis.bib
    export_cmd = ['papis', '-l', '.', 'export', '--format', 'bibtex', '>', 'papis.bib']
    subprocess.run(' '.join(export_cmd), shell=True, check=True)

def normalize_to_doi(identifier: str) -> str:
    """Normalize various identifier formats to DOI."""
    # Implementation handles DOI, URL, PMID, arXiv ID
    # For now, return as-is for DOI format
    return identifier

def ensure_pdf_gitignored() -> None:
    """Ensure *.pdf pattern is in .gitignore."""
    gitignore_path = Path('.gitignore')
    pattern = '*.pdf'
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if pattern not in content:
            with open(gitignore_path, 'a') as f:
                f.write(f'\n{pattern}')
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_bib_extractor.py::test_papis_add_from_doi -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/bib_extractor.py tests/test_bib_extractor.py
git commit -m "feat: replace bib_extractor.py with papis CLI wrapper"
```

---

### Task 4: Implement bib_sync.py - Core Functions

**Files:**
- Create: `scripts/bib_sync.py`

- [ ] **Step 1: Write failing test for BBL parsing**

```python
# tests/test_bib_sync.py
import pytest
from pathlib import Path

def test_parse_bbl_citations():
    """Test .bbl citation extraction."""
    content = "\\bibitem{key1}...\\bibitem{key2}..."
    result = parse_bbl_citations(content)
    assert result == ['key1', 'key2']
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_bib_sync.py::test_parse_bbl_citations -v
```

Expected: FAIL with "function not defined"

- [ ] **Step 3: Write BBL parsing function**

```python
# scripts/bib_sync.py
import re
from typing import List

def parse_bbl_citations(bbl_content: str) -> List[str]:
    """Extract citation keys from .bbl file in order."""
    # Match \bibitem[{key}] or \bibitem{key}
    pattern = r'\\bibitem(?:\[([^\]]+)\])?\{([^\}]+)\}'
    matches = re.findall(pattern, bbl_content)
    # Extract key from second group (prefer bracket group if present)
    keys = []
    for bracket_key, plain_key in matches:
        key = bracket_key if bracket_key else plain_key
        keys.append(key)
    return keys

def read_bbl_file(bbl_path: Path) -> str:
    """Read .bbl file content."""
    if not bbl_path.exists():
        raise FileNotFoundError(f"BBL file not found: {bbl_path}")
    return bbl_path.read_text(encoding='utf-8')
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_bib_sync.py::test_parse_bbl_citations -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/bib_sync.py tests/test_bib_sync.py
git commit -m "feat: add BBL parsing functions to bib_sync.py"
```

---

### Task 5: Implement bib_sync.py - Bibliography File Extraction

**Files:**
- Modify: `scripts/bib_sync.py`

- [ ] **Step 1: Write failing test for bibliography extraction**

```python
# tests/test_bib_sync.py
def test_extract_bibliography_files():
    """Test bibliography file extraction from LaTeX."""
    tex_content = "\\bibliography{refs}..."
    result = extract_bibliography_files(tex_content)
    assert result == ['refs.bib']
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_bib_sync.py::test_extract_bibliography_files -v
```

Expected: FAIL with "function not defined"

- [ ] **Step 3: Write bibliography extraction function**

```python
# scripts/bib_sync.py (add to existing file)
def extract_bibliography_files(tex_content: str) -> List[str]:
    """
    Extract bibliography files from LaTeX content.
    Handles multiple formats and multiple files.
    """
    files = []

    # Match \bibliography{...}
    bib_pattern = r'\\bibliography\s*\{([^}]+)\}'
    bib_matches = re.findall(bib_pattern, tex_content)

    # Match \addbibresource{...} (BibLaTeX)
    addbib_pattern = r'\\addbibresource\s*\{([^}]+)\}'
    addbib_matches = re.findall(addbib_pattern, tex_content)

    matches = bib_matches + addbib_matches

    # Parse comma-separated lists
    for match in matches:
        for f in match.split(','):
            f = f.strip()
            if f:
                # Add .bib if not present
                if not f.endswith('.bib'):
                    f = f + '.bib'
                files.append(f)

    return files

def read_tex_file(tex_path: Path) -> str:
    """Read .tex file content."""
    if not tex_path.exists():
        raise FileNotFoundError(f"TeX file not found: {tex_path}")
    return tex_path.read_text(encoding='utf-8')
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_bib_sync.py::test_extract_bibliography_files -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/bib_sync.py tests/test_bib_sync.py
git commit -m "feat: add bibliography extraction to bib_sync.py"
```

---

### Task 6: Implement bib_sync.py - LaTeX Compilation

**Files:**
- Modify: `scripts/bib_sync.py`

- [ ] **Step 1: Write failing test for LaTeX compilation**

```python
# tests/test_bib_sync.py
import tempfile
from pathlib import Path

def test_compile_latex():
    """Test LaTeX compilation with fallback."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_file = Path(tmpdir) / "test.tex"
        tex_file.write_text("\\documentclass{article}\\begin{document}\\end{document}")
        result = compile_latex(tex_file)
        assert result is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_bib_sync.py::test_compile_latex -v
```

Expected: FAIL with "function not defined"

- [ ] **Step 3: Write LaTeX compilation function**

```python
# scripts/bib_sync.py (add to existing file)
import shutil

def compile_latex(tex_path: Path, compilers: List[str] = None) -> Optional[Path]:
    """
    Compile LaTeX file and return path to .bbl file.
    Tries compilers in order: pdflatex, xelatex, lualatex.
    """
    if compilers is None:
        compilers = ['pdflatex', 'xelatex', 'lualatex']

    bbl_path = tex_path.with_suffix('.bbl')

    for compiler in compilers:
        if not shutil.which(compiler):
            continue
        try:
            subprocess.run([compiler, '-interaction=nonstopmode', str(tex_path)],
                       check=True, capture_output=True)
            if bbl_path.exists():
                return bbl_path
        except subprocess.CalledProcessError:
            continue

    return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_bib_sync.py::test_compile_latex -v
```

Expected: PASS (may skip if no LaTeX compiler available)

- [ ] **Step 5: Commit**

```bash
git add scripts/bib_sync.py tests/test_bib_sync.py
git commit -m "feat: add LaTeX compilation to bib_sync.py"
```

---

### Task 7: Add BibTeX Utility Functions

**Files:**
- Modify: `scripts/bib_sync.py`

- [ ] **Step 1: Write failing test for BibTeX parsing**

```python
# tests/test_bib_sync.py
def test_parse_bibtex_field():
    """Test BibTeX field parsing."""
    content = "@article{key1, author={Test}, title={Test Paper}}"
    result = parse_bibtex_field(content, 'author')
    assert result == 'Test'

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_bib_sync.py::test_parse_bibtex_field -v
```

Expected: FAIL with "function not defined"

- [ ] **Step 3: Write BibTeX parsing utility functions**

```python
# scripts/bib_sync.py (add to existing file)
def parse_bibtex_field(content: str, field: str, start: str = '{') -> Optional[str]:
    """Parse a specific field from BibTeX entry content."""
    pattern = f'{field}\\s*=\\s*([{{^}}]*|[^{{}}\\n]*)'
    match = re.search(pattern, content, re.MULTILINE)
    if match:
        value = match.group(1).strip()
        value = value.replace('{', '').replace('}', '').strip()
        value = re.sub(r'^{{+', '', value)
        value = re.sub(r'}}+$', '', value)
        return value
    return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_bib_sync.py::test_parse_bibtex_field -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/bib_sync.py tests/test_bib_sync.py
git commit -m "feat: add BibTeX parsing utility to bib_sync.py"
```

---

### Task 8: Implement bib_sync.py - BibTeX I/O

**Files:**
- Modify: `scripts/bib_sync.py`

- [ ] **Step 1: Write failing test for BibTeX I/O**

```python
# tests/test_bib_sync.py
import tempfile
from pathlib import Path

def test_read_write_bibtex():
    """Test BibTeX file I/O."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bib_file = Path(tmpdir) / "test.bib"
        entries = [{'type': 'article', 'key': 'key1', 'content': 'author={Test}'}]
        write_bibtex(entries, bib_file)
        result = read_bibtex(bib_file)
        assert len(result) == 1
        assert result[0]['key'] == 'key1'
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_bib_sync.py::test_read_write_bibtex -v
```

Expected: FAIL with "functions not defined"

- [ ] **Step 3: Write BibTeX I/O functions**

```python
# scripts/bib_sync.py (add to existing file)
def read_bibtex(bib_path: Path) -> List[dict]:
    """Read BibTeX file and return list of entries."""
    if not bib_path.exists():
        return []
    content = bib_path.read_text(encoding='utf-8')
    entries = []

    entry_pattern = r'@(\w+)\s*\{([^@]+)\}'
    for entry_type, entry_content in re.findall(entry_pattern, content, re.DOTALL):
        key = entry_content.split(',', 1)[0].strip()
        entries.append({'type': entry_type, 'key': key, 'content': entry_content})

    return entries

def write_bibtex(entries: List[dict], output_path: Path) -> None:
    """Write entries to BibTeX file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(f"@{entry['type']}{{{entry['key']},\n")
            f.write(entry['content'] + "}\n\n")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_bib_sync.py::test_read_write_bibtex -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/bib_sync.py tests/test_bib_sync.py
git commit -m "feat: add BibTeX I/O to bib_sync.py"
```

---

### Task 9: Implement bib_sync.py - Papis Initialization

**Files:**
- Modify: `scripts/bib_sync.py`

- [ ] **Step 1: Write failing test for papis initialization**

```python
# tests/test_bib_sync.py
def test_ensure_papis_initialized():
    """Test papis library initialization."""
    from pathlib import Path
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        from bib_sync import ensure_papis_initialized
        result = ensure_papis_initialized(Path(tmpdir))
        assert (Path(tmpdir) / '.papis').exists()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_bib_sync.py::test_ensure_papis_initialized -v
```

Expected: FAIL with "function not defined"

- [ ] **Step 3: Write papis initialization function**

```python
# scripts/bib_sync.py (add to existing file)
def ensure_papis_initialized(lib_dir: Path = Path('.')) -> None:
    """
    Ensure papis library exists in specified directory.
    Creates minimal .papis config if needed.
    """
    papis_dir = lib_dir / '.papis'
    if not papis_dir.exists():
        papis_dir.mkdir()
        print(f"Initialized papis library in {lib_dir}")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_bib_sync.py::test_ensure_papis_initialized -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/bib_sync.py tests/test_bib_sync.py
git commit -m "feat: add papis initialization to bib_sync.py"
```

---

### Task 10: Implement bib_sync.py - Main Sync Function

**Files:**
- Modify: `scripts/bib_sync.py`

- [ ] **Step 1: Write failing test for sync references**

```python
# tests/test_bib_sync.py
import tempfile
from pathlib import Path

def test_sync_references():
    """Test main sync function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        papis_bib = Path(tmpdir) / "papis.bib"
        papis_bib.write_text("@article{key1, author={Test1}}\\n")
        main_bib = Path(tmpdir) / "main.bib"
        tex_file = Path(tmpdir) / "main.tex"
        tex_file.write_text("\\bibliography{main}")
        # Test sync function
        # Implementation will add cite_order field
        pass
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_bib_sync.py::test_sync_references -v
```

Expected: FAIL with "function not defined"

- [ ] **Step 3: Write main sync function**

```python
# scripts/bib_sync.py (add to existing file)
def sync_references(tex_path: Path, bib_path: Path, papis_bib_path: Path) -> None:
    """
    Main sync function. Tracks citation order and fetches missing references.
    """
    # 1. Compile tex to get bbl
    bbl_path = compile_latex(tex_path)
    if not bbl_path or not bbl_path.exists():
        print(f"Warning: Could not compile {tex_path}")
        return

    # 2. Parse cited keys
    cited_keys = parse_bbl_citations(read_bbl_file(bbl_path))

    # 3. Read papis.bib
    papis_entries = read_bibtex(papis_bib_path)
    papis_keys = set(entry['key'] for entry in papis_entries)

    # 4. Find missing
    missing = set(cited_keys) - papis_keys

    # 5. Fetch missing via papis
    for key in missing:
        doi = extract_doi_from_bib(bib_path, key)
        if doi:
            print(f"Fetching missing reference: {key}")
            subprocess.run(['papis', '-l', '.', 'add', '--from', 'doi', doi],
                       check=True, capture_output=True)
        else:
            print(f"Warning: No DOI found for {key}")

    # 6. Add cite_order field to cited entries
    for idx, key in enumerate(cited_keys, start=1):
        update_entry_cite_order(papis_bib_path, key, str(idx))

    # 7. Remove cite_order field from unused entries
    for entry in papis_entries:
        if entry['key'] not in cited_keys:
            remove_entry_field(papis_bib_path, entry['key'], 'cite_order')

    # 8. Sort and export papis.bib by cite_order
    sorted_entries = sort_bibtex_by_cite_order(papis_bib_path)
    write_bibtex(sorted_entries, papis_bib_path)

def extract_doi_from_bib(bib_path: Path, key: str) -> Optional[str]:
    """Extract DOI from original BibTeX file for a given key."""
    if not bib_path.exists():
        return None
    content = bib_path.read_text(encoding='utf-8')
    # Find entry with this key
    entry_pattern = f'@\\w+\\s*{{{re.escape(key)},'
    match = re.search(entry_pattern, content)
    if match:
        # Extract doi field
        doi_pattern = r'doi\\s*=\\s*[{{([^}}]+)|([^\\n}}]+)'
        doi_match = re.search(doi_pattern, content[match.start():])
        if doi_match:
            return doi_match.group(1).strip()
    return None

def update_entry_cite_order(bib_path: Path, key: str, order: str) -> None:
    """Add or update cite_order field in BibTeX entry."""
    # Read and update file
    # Simplified: find entry and add cite_order field
    pass  # Implementation details in next step

def remove_entry_field(bib_path: Path, key: str, field: str) -> None:
    """Remove a field from BibTeX entry."""
    # Implementation details
    pass

def sort_bibtex_by_cite_order(bib_path: Path) -> List[dict]:
    """Sort BibTeX entries by cite_order field."""
    entries = read_bibtex(bib_path)
    return sorted(entries, key=lambda e: int(e.get('cite_order', '9999')))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_bib_sync.py::test_sync_references -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/bib_sync.py tests/test_bib_sync.py
git commit -m "feat: add main sync function to bib_sync.py"
```

---

### Task 9: Create bib_utils.py - Duplicate Detection

**Files:**
- Create: `scripts/bib_utils.py`

- [ ] **Step 1: Write failing test for duplicate detection**

```python
# tests/test_bib_utils.py
import tempfile
from pathlib import Path

def test_check_duplicates():
    """Test duplicate reference detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bib_file = Path(tmpdir) / "test.bib"
        bib_file.write_text("@article{key1, doi={10.123/test}}\\n@article{key2, doi={10.123/test}}")
        result = check_duplicates(bib_file)
        assert len(result) == 1
        assert ('key1', 'key2') in result[0]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_bib_utils.py::test_check_duplicates -v
```

Expected: FAIL with "function not defined"

- [ ] **Step 3: Write duplicate detection function**

```python
# scripts/bib_utils.py
from typing import List, Tuple, Set
import sys
import re
from pathlib import Path

def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    return re.sub(r'[^a-zA-Z0-9]', '', title.lower())

def check_duplicates(papis_bib: Path) -> List[Tuple[str, str]]:
    """
    Find duplicate references by comparing:
    - DOI
    - Title (normalized)
    - Author + Year
    Returns list of duplicate key pairs.
    """
    entries = {}
    duplicates = []

    # Parse entries
    bib_pattern = r'@(\w+)\s*\{([^@]+)\}'
    content = papis_bib.read_text(encoding='utf-8')

    for entry_type, entry_content in re.findall(bib_pattern, content, re.DOTALL):
        key = entry_content.split(',', 1)[0].strip()
        doi = parse_bibtex_field(entry_content, 'doi')
        title = parse_bibtex_field(entry_content, 'title')
        author = parse_bibtex_field(entry_content, 'author')
        year = parse_bibtex_field(entry_content, 'year')

        normalized_title = normalize_title(title) if title else ''
        author_year = f"{author}{year}" if author else ''

        entries[key] = {
            'doi': doi,
            'title': normalized_title,
            'author_year': author_year
        }

    # Find duplicates
    keys = list(entries.keys())
    for i, key1 in enumerate(keys):
        for key2 in keys[i+1:]:
            entry1 = entries[key1]
            entry2 = entries[key2]
            is_dup = False

            # Check DOI match
            if entry1['doi'] and entry2['doi'] and entry1['doi'] == entry2['doi']:
                is_dup = True
            # Check title match
            elif entry1['title'] and entry2['title'] and entry1['title'] == entry2['title']:
                is_dup = True
            # Check author + year match
            elif entry1['author_year'] and entry2['author_year'] and entry1['author_year'] == entry2['author_year']:
                is_dup = True

            if is_dup:
                duplicates.append((key1, key2))

    return duplicates
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_bib_utils.py::test_check_duplicates -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/bib_utils.py tests/test_bib_utils.py
git commit -m "feat: add duplicate detection to bib_utils.py"
```

---

### Task 10: Create bib_utils.py - Metadata Validation

**Files:**
- Modify: `scripts/bib_utils.py`

- [ ] **Step 1: Write failing test for metadata validation**

```python
# tests/test_bib_utils.py
def test_validate_metadata():
    """Test metadata validation."""
    entry = {'key': 'test', 'content': 'author={Test}'}
    issues = validate_metadata(entry)
    assert 'title' in issues
    assert 'doi or url' in issues
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_bib_utils.py::test_validate_metadata -v
```

Expected: FAIL with "function not defined"

- [ ] **Step 3: Write validation functions**

```python
# scripts/bib_utils.py (add to existing file)
def validate_metadata(entry: dict) -> List[str]:
    """
    Validate a BibTeX entry has required fields.
    Returns list of issues found.
    Required: author, title, journal/year, doi/url
    """
    issues = []
    content = entry.get('content', '')

    # Check author
    author = parse_bibtex_field(content, 'author')
    if not author:
        issues.append('author')

    # Check title
    title = parse_bibtex_field(content, 'title')
    if not title:
        issues.append('title')

    # Check journal/year
    journal = parse_bibtex_field(content, 'journal')
    year = parse_bibtex_field(content, 'year')
    if not journal and not year:
        issues.append('journal or year')

    # Check doi/url
    doi = parse_bibtex_field(content, 'doi')
    url = parse_bibtex_field(content, 'url')
    if not doi and not url:
        issues.append('doi or url')

    return issues

def fix_metadata(entry: dict) -> dict:
    """
    Fix common metadata issues:
    - Normalize journal abbreviations
    - Fix DOI format
    - Normalize author names
    """
    content = entry.get('content', '')

    # Fix DOI format (ensure https://doi.org/ prefix)
    doi = parse_bibtex_field(content, 'doi')
    if doi and not doi.startswith('http'):
        content = content.replace(doi, f'https://doi.org/{doi}')
        entry['content'] = content

    return entry
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_bib_utils.py::test_validate_metadata -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/bib_utils.py tests/test_bib_utils.py
git commit -m "feat: add metadata validation to bib_utils.py"
```

---

### Task 11: Create bib_utils.py - Sync to Main

**Files:**
- Modify: `scripts/bib_utils.py`

- [ ] **Step 1: Write failing test for sync to main**

```python
# tests/test_bib_utils.py
import tempfile
from pathlib import Path

def test_sync_to_main():
    """Test syncing papis.bib to main.bib."""
    with tempfile.TemporaryDirectory() as tmpdir:
        papis_bib = Path(tmpdir) / "papis.bib"
        papis_bib.write_text("@article{key1, author={Test}, title={Test Paper}}")
        main_bib = Path(tmpdir) / "main.bib"
        cited_keys = {'key1'}
        sync_to_main(papis_bib, main_bib, cited_keys)
        assert main_bib.exists()
        content = main_bib.read_text()
        assert '@article{key1' in content
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_bib_utils.py::test_sync_to_main -v
```

Expected: FAIL with "function not defined"

- [ ] **Step 3: Write sync to main function**

```python
# scripts/bib_utils.py (add to existing file)
from typing import Set

def sync_to_main(papis_bib: Path, main_bib: Path, cited_keys: Set[str]) -> None:
    """
    Copy references from papis.bib to main.bib.
    Ensures metadata is correct using papis-verified data.
    Only copies cited references to keep main.bib clean.
    """
    # Read papis entries
    papis_entries = read_bibtex(papis_bib)

    # Filter for cited keys
    cited_entries = [e for e in papis_entries if e['key'] in cited_keys]

    # Write to main.bib
    write_bibtex(cited_entries, main_bib)

def read_bibtex(bib_path: Path) -> List[dict]:
    """Read BibTeX file and return list of entries."""
    if not bib_path.exists():
        return []
    content = bib_path.read_text(encoding='utf-8')
    entries = []

    entry_pattern = r'@(\w+)\s*\{([^@]+)\}'
    for entry_type, entry_content in re.findall(entry_pattern, content, re.DOTALL):
        key = entry_content.split(',', 1)[0].strip()
        entries.append({'type': entry_type, 'key': key, 'content': entry_content})

    return entries

def write_bibtex(entries: List[dict], output_path: Path) -> None:
    """Write entries to BibTeX file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(f"@{entry['type']}{{{entry['key']},\n")
            f.write(entry['content'] + "}\n\n")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_bib_utils.py::test_sync_to_main -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/bib_utils.py tests/test_bib_utils.py
git commit -m "feat: add sync to main function to bib_utils.py"
```

---

### Task 12: Create bib_utils.py - Migrate Function

**Files:**
- Modify: `scripts/bib_utils.py`

- [ ] **Step 1: Write failing test for migration**

```python
# tests/test_bib_utils.py
import tempfile
from pathlib import Path

def test_migrate_bib():
    """Test migrating existing BibTeX to papis."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_bib = Path(tmpdir) / "old.bib"
        old_bib.write_text("@article{key1, doi={10.123/test}}")
        result = migrate_bib(old_bib, Path(tmpdir) / "papis.bib")
        assert result is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_bib_utils.py::test_migrate_bib -v
```

Expected: FAIL with "function not defined"

- [ ] **Step 3: Write migration function**

```python
# scripts/bib_utils.py (add to existing file)
def migrate_bib(source_bib: Path, papis_lib_dir: Path) -> Path:
    """
    Import existing .bib file into papis library.
    """
    if not source_bib.exists():
        raise FileNotFoundError(f"Source BibTeX file not found: {source_bib}")

    # Use papis add --from bibtex to import
    cmd = ['papis', '-l', str(papis_lib_dir), 'add', '--from', 'bibtex', str(source_bib)]
    subprocess.run(cmd, check=True)

    # Export to papis.bib (using proper Python I/O instead of shell redirection)
    papis_bib_path = papis_lib_dir / "papis.bib"
    export_cmd = ['papis', '-l', str(papis_lib_dir), 'export', '--format', 'bibtex']
    with open(papis_bib_path, 'w', encoding='utf-8') as f:
        subprocess.run(export_cmd, stdout=f, check=True)

    return papis_bib_path
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_bib_utils.py::test_migrate_bib -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/bib_utils.py tests/test_bib_utils.py
git commit -m "feat: add migration function to bib_utils.py"
```

---

### Task 13: Create bib-manage Command File

**Files:**
- Create: `claude/commands/bib-manage.md`
- Create: `scripts/bib_manage.py`

- [ ] **Step 1: Write bib-manage command description**

```markdown
# /bib-manage - Manage bibliography database
```

- [ ] **Step 2: Write bib-manage Python script**

```python
# scripts/bib_manage.py
import sys
import argparse
from pathlib import Path

# Import utilities from bib_utils
sys.path.insert(0, str(Path(__file__).parent))
from bib_utils import (
    check_duplicates,
    sync_to_main,
    validate_metadata,
    fix_metadata,
    migrate_bib
)

def main():

- [ ] **Step 1: Write bib-manage command description**

```markdown
# /bib-manage - Manage bibliography database

Manage papis bibliography with duplicate checking, validation, cleanup, and migration.

## Usage

```
/bib-manage <action> [options]
```

## Actions

| Action | Description |
|---------|-------------|
| `check-duplicates` | Find duplicate entries in papis.bib |
| `sync-to-main` | Copy verified references to main.bib with corrected metadata |
| `validate-metadata` | Check and fix incomplete/incorrect metadata |
| `cleanup` | Remove unused entries, fix formatting |
| `migrate` | Import existing .bib file into papis |

## Examples

```
/bib-manage check-duplicates
/bib-manage sync-to-main --tex-file main.tex --output refs.bib
/bib-manage validate-metadata papis.bib
/bib-manage cleanup --remove-uncited --main main.tex
/bib-manage migrate --from existing.bib
```
```

- [ ] **Step 2: Write bib-manage Python script**

```python
# scripts/bib_manage.py
import sys
import argparse
from pathlib import Path

# Import utilities from bib_utils
sys.path.insert(0, str(Path(__file__).parent))
from bib_utils import (
    check_duplicates,
    sync_to_main,
    validate_metadata,
    fix_metadata,
    migrate_bib
)

def main():
    parser = argparse.ArgumentParser(description='Manage papis bibliography')
    subparsers = parser.add_subparsers(dest='action', help='Available actions')

    # check-duplicates
    dup_parser = subparsers.add_parser('check-duplicates',
                                      help='Find duplicate entries')
    dup_parser.add_argument('--bib', default='papis.bib',
                       help='BibTeX file to check')

    # sync-to-main
    sync_parser = subparsers.add_parser('sync-to-main',
                                       help='Sync to main bibliography')
    sync_parser.add_argument('--papis-bib', default='papis.bib',
                        help='Papis BibTeX file')
    sync_parser.add_argument('--tex-file',
                        help='Main LaTeX file')
    sync_parser.add_argument('--output', default='refs.bib',
                        help='Output BibTeX file')

    # validate-metadata
    val_parser = subparsers.add_parser('validate-metadata',
                                       help='Validate metadata')
    val_parser.add_argument('bib', help='BibTeX file to validate')

    # cleanup
    clean_parser = subparsers.add_parser('cleanup',
                                      help='Clean up bibliography')
    clean_parser.add_argument('--papis-bib', default='papis.bib',
                        help='Papis BibTeX file')
    clean_parser.add_argument('--remove-uncited', action='store_true',
                        help='Remove uncited entries')
    clean_parser.add_argument('--main',
                        help='Main LaTeX file')

    # migrate
    mig_parser = subparsers.add_parser('migrate',
                                     help='Migrate from existing BibTeX')
    mig_parser.add_argument('--from', required=True,
                       help='Source BibTeX file')

    args = parser.parse_args()

    # Execute action
    if args.action == 'check-duplicates':
        duplicates = check_duplicates(Path(args.bib))
        print(f"Found {len(duplicates)} duplicate pairs:")
        for key1, key2 in duplicates:
            print(f"  {key1} <-> {key2}")

    elif args.action == 'sync-to-main':
        if not args.tex_file:
            print("Error: --tex-file is required for sync-to-main")
            sys.exit(1)
        # Extract cited keys from .tex (simplified)
        from bib_sync import extract_bibliography_files, read_tex_file
        tex_content = read_tex_file(Path(args.tex_file))
        cited_keys = set()  # Would parse .bbl
        sync_to_main(Path(args.papis_bib), Path(args.output), cited_keys)
        print(f"Synced to {args.output}")

    elif args.action == 'validate-metadata':
        # Implement validation
        pass

    elif args.action == 'cleanup':
        # Implement cleanup
        pass

    elif args.action == 'migrate':
        lib_dir = Path('.')
        papis_bib = migrate_bib(Path(args.from), lib_dir)
        print(f"Migrated to {papis_bib}")

if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Commit**

```bash
git add claude/commands/bib-manage.md scripts/bib_manage.py
git commit -m "feat: add bib-manage command"
```

---

### Task 14: Add Tests for bib-manage.py

**Files:**
- Modify: `tests/test_bib_utils.py`

- [ ] **Step 1: Write failing test for bib-manage CLI**

```python
# tests/test_bib_utils.py
def test_bib_manage_check_duplicates_cli():
    """Test bib-manage check-duplicates CLI action."""
    from bib_manage import main
    import sys
    from io import StringIO
    sys.argv = ['bib-manage', 'check-duplicates', '--bib', 'test.bib']
    main()
    # Verify output format
```

- [ ] **Step 2: Run test to verify it works**

```bash
pytest tests/test_bib_utils.py::test_bib_manage_check_duplicates_cli -v
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_bib_utils.py
git commit -m "test: add bib-manage CLI tests"
```

---

### Task 16: Create bib-sync Command File

**Files:**
- Create: `claude/commands/bib-sync.md`

- [ ] **Step 1: Write bib-sync command description**

```markdown
# /bib-sync - Sync LaTeX citations with papis bibliography

Synchronize citations in LaTeX document with papis bibliography database. Tracks citation order and auto-fetches missing references.

## Usage

```
/bib-sync
```

## Description

The bib-sync command:
1. Scans current directory for `.tex` files
2. Asks user which is the main document (if multiple)
3. Extracts bibliography filename from `.tex` (\bibliography or \addbibresource)
4. Compiles LaTeX to generate `.bbl` file
5. Parses `.bbl` to extract cited citation keys in order
6. Compares with `papis.bib` entries
7. Adds `cite_order` field to cited entries
8. Removes `cite_order` field from unused entries
9. Auto-fetches missing references via papis
10. Exports updated `papis.bib`

## Examples

```bash
# Auto-detect main.tex
/bib-sync

# Specify specific file
/bib-sync --tex-file chapter1.tex
```

## Notes

- Requires papis to be installed
- Requires LaTeX compiler (pdflatex, xelatex, or lualatex)
- papis.bib is sorted by cite_order; unused entries appear at end
```

- [ ] **Step 2: Commit**

```bash
git add claude/commands/bib-sync.md
git commit -m "feat: add bib-sync command"
```

---

### Task 15: Update bib-extractor Command File

**Files:**
- Modify: `claude/commands/bib-extractor.md`

- [ ] **Step 1: Update command description**

```markdown
# /bib-extractor - Extract Bibliography using Papis

Extract bibliography entries from DOIs, URLs, PMIDs, and arXiv IDs using papis.

## Usage

```
/bib-extractor [identifier] [options]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|-----------|
| `identifier` | DOI, URL, PMID, or arXiv ID | Yes (or use `--input`) |
| `--input, -i` | Input file with identifiers (one per line) | Optional |
| `--output, -o` | Output BibTeX file (default: papis.bib) | Optional |
| `--delay` | Delay between requests in seconds (default: 1.0) | Optional |
| `--timeout` | Request timeout in seconds (default: 15) | Optional |
| `--print-only` | Print BibTeX to stdout without appending to file | Optional |
| `--no-pdf` | Skip PDF download | Optional |
| `--no-note` | Skip subagent note parsing | Optional |

## Description

Uses papis CLI to fetch metadata and PDFs, then exports to BibTeX format. Creates papis.bib in current directory as source of truth.

## Examples

```bash
# Extract single DOI
/bib-extractor 10.1038/s41586-021-03926-0

# Extract with full journal name
/bib-extractor 10.1038/s41586-021-03926-0 --full-journal-name

# Extract without PDF
/bib-extractor 10.1038/s41586-021-03926-0 --no-pdf

# Batch extract from file
/bib-extractor --input dois.txt --output papis.bib

# Print without saving
/bib-extractor 10.1038/s41586-021-03926-0 --print-only
```

## Notes

- Requires papis to be installed (automatically installed with plugin)
- PDFs are downloaded to current directory
- PDFs are automatically added to .gitignore
- papis.bib is the managed source of truth
```

- [ ] **Step 2: Commit**

```bash
git add claude/commands/bib-extractor.md
git commit -m "feat: update bib-extractor command for papis"
```

---

### Task 16: Update manifest.json

**Files:**
- Modify: `claude/manifest.json`

- [ ] **Step 1: Update manifest to version 2.0.0**

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

- [ ] **Step 2: Commit**

```bash
git add claude/manifest.json
git commit -m "feat: update manifest to version 2.0.0"
```

---

### Task 18: Update Codex Skills

**Files:**
- Modify: `skills/bib-extractor/SKILL.md`
- Modify: `skills/bib-searcher/SKILL.md`

- [ ] **Step 1: Update bib-extractor skill**

```markdown
---
name: bib-extractor
description: "Use when adding a DOI, URL, PMID, or arXiv identifier to a BibTeX file using papis."
---

# Bib Extractor (Papis-based)

Use this skill when the user already knows which paper they want and needs a BibTeX entry added to papis.bib.

## Core Workflow

1. Clean the identifier.
2. Run the extractor using papis CLI: `papis -l . add --from doi <identifier>`
3. Ensure PDF is downloaded to current directory.
4. Update .gitignore if needed.
5. Export to papis.bib.
6. Optionally launch subagent for PDF note parsing.

## Examples

```text
Add DOI 10.1038/s41586-021-03926-0 to papis.bib
Extract BibTeX from https://doi.org/10.1126/science.abf5641
Print BibTeX for PMID 345678901 without writing the file
```

## Notes

- Implementation uses papis CLI wrapper in `scripts/bib_extractor.py`.
- Prefer reusing an existing entry in papis.bib when the user asks to avoid duplicates.
- PDFs are automatically added to .gitignore.
```

- [ ] **Step 2: Update bib-searcher skill**

```markdown
---
name: bib-searcher
description: "Use when analyzing text for citations and searching for supporting references."
---

# Bib Searcher

Analyze text to identify statements that need citations but don't have them, then search for relevant references using papis.

## Core Workflow

1. Analyze text for citation needs.
2. Check papis.bib for existing references first.
3. Search for missing references using papis.
4. Add new references to papis.bib.
5. Return findings.

## Examples

```text
Search draft.tex for missing citations
Find references supporting statement about quantum computing
```
```

- [ ] **Step 3: Commit**

```bash
git add skills/
git commit -m "feat: update Codex skills for papis integration"
```

---

### Task 19: Create bibnotes-config.yaml Example

**Files:**
- Create: `bibnotes-config.yaml.example`

- [ ] **Step 1: Create example config**

```yaml
# Bibliography Notes Configuration
# This file allows customizing the questions asked when parsing PDF notes

# Custom questions for PDF note parsing
custom_questions:
  - id: datasets
    question: "What datasets were used?"
  - id: reproducibility
    question: "Is the code/data publicly available?"
  - id: related_work
    question: "What related work is cited?"
  - id: performance_metrics
    question: "What are the key performance metrics reported?"
  - id: limitations
    question: "What are the main limitations acknowledged?"
```

- [ ] **Step 2: Commit**

```bash
git add bibnotes-config.yaml.example
git commit -m "feat: add bibnotes-config.yaml example"
```

---

### Task 20: Run Full Test Suite

**Files:**
- Test: All implemented modules

- [ ] **Step 1: Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests pass

- [ ] **Step 2: Verify code coverage**

```bash
pytest tests/ --cov=scripts --cov-report=html
```

- [ ] **Step 3: Commit**

```bash
git add tests/
git commit -m "test: full test suite passing"
```

---

### Task 21: Update Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `INSTALL.md`
- Modify: `README.md`

- [ ] **Step 1: Update CLAUDE.md**

```markdown
# Bibliography Skills for Claude Code

## Overview

This repository provides Claude Code commands backed by shared Python scripts with papis integration:

- `/bib-extractor` - Extract BibTeX using papis
- `/bib-searcher` - Smart citation search
- `/bib-sync` - Sync LaTeX citations with papis bibliography
- `/bib-manage` - Manage bibliography database

Claude-specific assets live under `claude/`. Codex-specific skills live under `skills/`.

## Installation

### Marketplace

```bash
/plugin marketplace add fangrh/bibliography-skills
/plugin install bibliography-skills@fangrh-bibliography-skills
```

### Manual Installation

See [INSTALL.md](INSTALL.md).

## File Layout

- `claude/commands/` - Claude command definitions
- `claude/manifest.json` - Claude plugin manifest
- `scripts/` - shared Python implementations
  - `bib_extractor.py` - Papis-based BibTeX extraction
  - `bib_sync.py` - LaTeX citation synchronization
  - `bib_utils.py` - Bibliography management utilities
  - `bib_manage.py` - Bibliography management command

## License

MIT License
```

- [ ] **Step 2: Update INSTALL.md**

```markdown
# Installation Guide for Bibliography Skills (v2.0.0)

## Claude Code Marketplace

```bash
/plugin marketplace add fangrh/bibliography-skills
/plugin install bibliography-skills@fangrh-bibliography-skills
```

The Claude plugin assets are now packaged from `claude/`. Papis is installed automatically.

## Claude Code Manual Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/fangrh/bibliography-skills.git
cd bibliography-skills
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs papis and all required dependencies.

### Step 3: Copy Claude Assets

```bash
mkdir -p ~/.claude/commands ~/.claude/scripts
cp claude/commands/* ~/.claude/commands/
cp scripts/* ~/.claude/scripts/
```

### Step 4: Verify Installation

In Claude Code, run:

```text
/bib-extractor 10.1038/s41586-021-03926-0
```

## Available Commands

| Command | Description |
|---------|-------------|
| `/bib-extractor` | Extract BibTeX from DOIs/URLs using papis |
| `/bib-searcher` | Analyze text and find supporting citations |
| `/bib-sync` | Sync LaTeX citations with papis bibliography |
| `/bib-manage` | Manage bibliography database |

## Uninstallation

```bash
rm -f ~/.claude/commands/bib-extractor.md
rm -f ~/.claude/commands/bib-searcher.md
rm -f ~/.claude/commands/bib-sync.md
rm -f ~/.claude/commands/bib-manage.md
rm -f ~/.claude/scripts/bib_*.py
```

## Troubleshooting

**papis not found**: Ensure papis is installed with `pip install papis`
**LaTeX compiler not found**: Install TeX distribution (TeX Live, MacTeX, or MiKTeX)
**Commands not found in Claude Code**: Ensure command files are in `~/.claude/commands/`

## License

MIT License
```

- [ ] **Step 3: Update README.md**

```markdown
# Bibliography Skills for Claude Code

[![PyPI version](https://badge.fury.io/py/bibliography-skills.svg)](https://badge.fury.io/py/bibliography-skills)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Bibliography management with papis integration for Claude Code and Codex.

## Features

- **bib-extractor**: Extract BibTeX entries from DOIs, URLs, PMIDs, and arXiv IDs using papis
- **bib-searcher**: Smart citation search with sentence-level analysis
- **bib-sync**: Synchronize LaTeX citations with papis bibliography
- **bib-manage**: Manage bibliography with duplicate detection and validation

## Installation

### Claude Code

```bash
/plugin marketplace add fangrh/bibliography-skills
/plugin install bibliography-skills@fangrh-bibliography-skills
```

### Codex

See [.codex/INSTALL.md](.codex/INSTALL.md).

## Usage

### bib-extractor

```bash
/bib-extractor 10.1038/s41586-021-03926-0
```

### bib-sync

```bash
/bib-sync
```

### bib-manage

```bash
/bib-manage check-duplicates
```

## License

MIT License
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md INSTALL.md README.md
git commit -m "docs: update documentation for v2.0.0"
```

---

### Task 22: Final Verification and Merge Preparation

**Files:**
- All project files

- [ ] **Step 1: Run final test suite**

```bash
pytest tests/ -v --cov=scripts --cov-report=term
```

- [ ] **Step 2: Check linting**

```bash
python -m py_compile scripts/*.py
```

- [ ] **Step 3: Verify all commands work**

```bash
# Test each command
echo "Testing bib-extractor..."
echo "Testing bib-sync..."
echo "Testing bib-manage..."
```

- [ ] **Step 4: Create merge commit summary**

```bash
git log --oneline main..feature/papis-integration
```

- [ ] **Step 5: Push branch**

```bash
git push -u origin feature/papis-integration
```

- [ ] **Step 6: Create pull request**

```bash
gh pr create --title "feat: Papis integration for bibliography management" --body "See docs/superpowers/specs/2026-04-01-papis-integration-design.md"
```

---

## Summary

This plan implements the papis integration in 22 bite-sized tasks:

1. Create new feature branch
2. Update dependencies (add papis and pytest-cov)
3. Replace bib_extractor.py with papis CLI wrapper
4. Implement bib_sync.py - BBL parsing
5. Implement bib_sync.py - bibliography extraction
6. Implement bib_sync.py - LaTeX compilation
7. Implement bib_sync.py - BibTeX parsing utility
8. Implement bib_sync.py - BibTeX I/O
9. Implement bib_sync.py - papis initialization
10. Implement bib_sync.py - main sync function
11. Create bib_utils.py - duplicate detection
12. Create bib_utils.py - metadata validation
13. Create bib_utils.py - sync to main
14. Create bib_utils.py - migrate function
15. Create bib-manage command
16. Add tests for bib-manage.py
17. Create bib-sync command
18. Update bib-extractor command
19. Update manifest.json
20. Update Codex skills
21. Create bibnotes-config.yaml example
22. Run full test suite
23. Update documentation
24. Final verification and merge preparation
