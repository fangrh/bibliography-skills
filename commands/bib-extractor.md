# /bib-extractor - Extract Bibliography from DOIs/URLs

Extract bibliography entries from DOIs, URLs, PMIDs, and arXiv IDs. Automatically fetches metadata, formats as BibTeX, and appends to your local `.bib` file.

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

## Examples

```
# Extract single DOI
/bib-extractor 10.1038/s41586-021-03926-0

# Extract from URL
/bib-extractor https://doi.org/10.1126/science.abf5641

# Extract from arXiv
/bib-extractor 2103.14030

# Batch extract from file
/bib-extractor --input dois.txt --output references.bib

# Print without saving
/bib-extractor 10.1038/s41586-021-03926-0 --print-only
```

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
2. Query appropriate metadata source (CrossRef, PubMed, arXiv)
3. Extract all metadata fields
4. Generate unique citation key
5. Format as BibTeX entry
6. Append to specified `.bib` file

## Notes

- Requires `requests` package: `pip install requests`
- Rate limiting applies between batch requests
- Checks for duplicate citation keys before writing
