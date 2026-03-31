# /bib-sync - Synchronize Bibliography with LaTeX Citations

Sync your papis bibliography with citations in your LaTeX document. Scans `.tex` files, extracts cited references, and updates the `cite_order` field to reflect actual citation order in your document.

## Usage

```
/bib-sync [options]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `--tex-file, -t` | Specify the main LaTeX file | Optional |
| `--bib-file, -b` | Bibliography file to update (default: papis.bib) | Optional |
| `--dry-run` | Show what would change without modifying files | Optional |
| `--no-fetch` | Skip auto-fetching missing references | Optional |

## Process

1. **Scan directory** - Find all `.tex` files in current directory
2. **Identify main document** - Ask user which is the main file if multiple found
3. **Extract bibliography filename** - Parse `\bibliography{}` or `\addbibresource{}` commands
4. **Compile LaTeX** - Run LaTeX compilation to generate `.bbl` file with cited references
5. **Parse `.bbl`** - Extract citation keys in the order they appear in the document
6. **Compare with papis.bib** - Check which entries are cited vs unused
7. **Update cite_order** - Add `cite_order = N` field to cited entries in order
8. **Remove unused cite_order** - Clean `cite_order` field from entries not in the document
9. **Auto-fetch missing** - Use papis to fetch any cited references not in papis.bib (unless `--no-fetch`)
10. **Export papis.bib** - Write updated bibliography with proper citation ordering

## Examples

### Basic Sync

```bash
# Auto-detect main.tex and sync
/bib-sync

# Specify specific LaTeX file
/bib-sync --tex-file chapter1.tex

# Use custom bibliography file
/bib-sync --bib-file references.bib
```

### Dry Run

```bash
# Preview changes without modifying files
/bib-sync --dry-run

# Output shows what would be updated:
# Cited entries to add cite_order: 12
# Unused entries to remove cite_order: 3
# Missing references to fetch: 2
```

### Skip Auto-Fetch

```bash
# Sync without automatically fetching missing references
/bib-sync --no-fetch
```

## Output

The command provides status updates for each step:

```
Found 3 .tex files in directory:
  - main.tex
  - chapter1.tex
  - chapter2.tex

Main document [main.tex]? main

Extracted bibliography: references.bib
Compiling LaTeX...
Generated .bbl file

Found 15 cited references:
  - smith2023quantum
  - jones2024coherence
  - ...

Updating cite_order field for 15 entries...
Removing cite_order from 3 unused entries...

1 missing reference(s) detected:
  - williams2025breakthrough
Fetching with papis...

Exporting updated papis.bib... Done
```

## cite_order Field

The `cite_order` field is a custom field added to BibTeX entries:

```bibtex
@article{smith2023quantum,
  author = {Smith, John},
  title = {Quantum Coherence},
  journal = {Phys. Rev. Lett.},
  year = {2023},
  cite_order = 1,  % Added by bib-sync
  ...
}
```

This field enables:
- Reference notes ranked by paper contribution
- Sorting references by their citation order in the document
- Identifying which entries are actively used vs unused

## Notes

- Requires LaTeX (pdflatex, xelatex, or lualatex) installed and available in PATH
- Requires papis installed for auto-fetching missing references
- The `.bbl` file is generated during LaTeX compilation and contains the bibliography data
- Existing `cite_order` values on unused entries are removed
- New entries fetched via papis will be assigned appropriate `cite_order` values
- The command handles standard bibliography commands: `\bibliography{}` (BibTeX/BibLaTeX) and `\addbibresource{}` (BibLaTeX)
