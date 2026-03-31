# /bib-extractor - Extract Bibliography from DOIs/URLs

Extract bibliography entries from DOIs, URLs, PMIDs, and arXiv IDs. Uses papis to fetch metadata, formats as BibTeX, and appends to your local `.bib` file. PDFs are automatically downloaded to the current directory.

## Usage

```
/bib-extractor [identifier] [options]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|-----------|
| `identifier` | DOI, URL, PMID, or arXiv ID | Yes (or use `--input`) |
| `--input, -i` | Input file with identifiers (one per line) | Optional |
| `--output, -o` | Output BibTeX file (default: references.bib) | Optional |
| `--delay` | Delay between requests in seconds (default: 1.0) | Optional |
| `--timeout` | Request timeout in seconds (default: 15) | Optional |
| `--print-only` | Print BibTeX to stdout without appending to file | Optional |
| `--abstract` | Fetch and include abstract in BibTeX entry | Optional |
| `--impact-factor` | Fetch and include journal impact factor/metrics | Optional |
| `--full-journal-name` | Use full journal names instead of abbreviations | Optional |
| `--inline` | Output inline citation format instead of BibTeX | Optional |
| `--inline-style` | Citation style: `journal`, `author`, `nature`, `apa` (default: journal) | Optional |
| `--latex-href` | Output LaTeX \href command with DOI link | Optional |
| `--clean-invalid` | Remove entries with invalid DOIs from the BibTeX file | Optional |

## Output Fields

Generated BibTeX entries include:
- Standard fields: author, title, journal, volume, pages, year, doi, url
- `citations`: Citation count from CrossRef/OpenAlex/Semantic Scholar
- `impact_factor`: Journal metrics (h-index, i10-index, paper count, citation count)
- `abstract`: Paper abstract (when using `--abstract` flag)

## Impact Factor Metrics

The `--impact-factor` flag adds journal-level metrics from OpenAlex:
- **h-index**: Journal's h-index
- **i10-index**: Number of papers cited 10+ times
- **papers**: Total papers in journal
- **citations**: Total citations to journal

## Journal Abbreviations

By default, journal names are abbreviated following standard conventions. Examples:

| Full Name | Abbreviation |
|-----------|--------------|
| Physical Review Letters | Phys. Rev. Lett. |
| Physical Review B | Phys. Rev. B |
| Nature Communications | Nat. Commun. |
| Nature Physics | Nat. Phys. |
| Science | Science |
| Nano Letters | Nano Lett. |
| Applied Physics Letters | Appl. Phys. Lett. |

Use `--full-journal-name` to keep the complete journal name instead.

## Examples

```
# Extract single DOI (journal abbreviated by default)
/bib-extractor 10.1038/s41586-021-03926-0
# Output: journal = {Nat. Commun.}

# Extract with full journal name
/bib-extractor 10.1038/s41586-021-03926-0 --full-journal-name
# Output: journal = {Nature Communications}

# Extract with abstract
/bib-extractor 10.1038/s41586-021-03926-0 --abstract
# Output includes: abstract = {Full abstract text...}

# Extract from URL
/bib-extractor https://doi.org/10.1126/science.abf5641

# Extract from arXiv
/bib-extractor 2103.14030

# Batch extract from file
/bib-extractor --input dois.txt --output references.bib

# Print without saving
/bib-extractor 10.1038/s41586-021-03926-0 --print-only

# Generate inline citation (journal style)
/bib-extractor 10.1038/s41586-021-03926-0 --inline
# Output: \textit{Nature}, 598, 434–438, (2021)

# Generate LaTeX href with inline citation
/bib-extractor 10.1038/s41586-021-03926-0 --inline --latex-href
# Output: \href{https://doi.org/10.1038/s41586-021-03926-0}{\textit{Nature}, 598, 434–438, (2021)}

# Generate author-style citation
/bib-extractor 10.1038/s41586-021-03926-0 --inline --inline-style author
# Output: Zhou et al. (2021) \textit{Nature} 598 434–438

# Generate Nature-style citation
/bib-extractor 10.1038/s41586-021-03926-0 --inline --inline-style nature
# Output: Zhou, H et al. \textit{Nature} 598, 434–438 (2021)
```

## Inline Citation Styles

| Style | Format | Example |
|-------|--------|---------|
| `journal` (default) | *Journal*, Volume, Pages, (Year) | `\textit{Nature}, 598, 434–438, (2021)` |
| `author` | Author et al. (Year) *Journal* Volume Pages | `Zhou et al. (2021) \textit{Nature} 598 434–438` |
| `nature` | Author, F et al. *Journal* Volume, Pages (Year) | `Zhou, H et al. \textit{Nature} 598, 434–438 (2021)` |
| `apa` | Author, F. et al. (Year). Title. *Journal*, Volume(Issue). | `Zhou, H. et al. (2021) Superconductivity... \textit{Nature}, 598(7881).` |

## Input Formats

| Type | Example |
|-------|----------|
| DOI | `10.1038/s41586-021-03926-0` |
| DOI URL | `https://doi.org/10.1038/s41586-021-03926-0` |
| Publisher URL | `https://www.nature.com/articles/s41586-021-03926-0` |
| arXiv ID | `2103.14030` |
| arXiv URL | `https://arxiv.org/abs/2103.14030` |
| PMID | `345678901` |
| PubMed URL | `https://pubmed.ncbi.nlm.nih.gov/345678901/` |

## Output

Generates properly formatted BibTeX entries with:
- Auto-generated citation keys (FirstAuthorYearKeyword format)
- Full field support (author, title, journal, volume, pages, year, doi, url)
- Duplicate handling with letter suffixes (a, b, c)
- Appends to existing `.bib` file without overwriting

## Process

1. Identify paper identifier type (DOI, PMID, arXiv ID, or URL)
2. Delegate to papis CLI to query metadata sources (CrossRef, PubMed, arXiv)
3. Extract all metadata fields from papis output
4. Generate unique citation key
5. Format as BibTeX entry
6. Append to specified `.bib` file
7. papis automatically downloads PDF to current directory

## Notes

- Requires `papis` package: `pip install papis` (and papis dependencies)
- Uses papis CLI for metadata fetching and PDF download
- PDFs are automatically downloaded to the current directory (not a centralized library)
- Consider adding `*.pdf` to `.gitignore` if PDF downloads are not meant to be tracked
- Rate limiting applies between batch requests (configured via `--delay`)
- Checks for duplicate citation keys before writing
