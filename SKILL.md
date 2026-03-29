---
name: bib-extractor
description: Extract bibliography from DOIs/URLs and append to local .bib files. Like Zotero - provide a DOI or URL, fetch metadata, extract BibTeX, and append to your local bibliography file.
allowed-tools: [Read, Write, Edit, Bash, Skill, mcp__web-search-prime__web_search_prime, mcp__web-reader__webReader]
---

# Bibliography Extractor

## Overview

A Zotero-like tool for extracting bibliography entries from DOIs and URLs. Given a paper identifier (DOI, URL, PMID, arXiv ID), this skill fetches complete metadata, formats it as BibTeX, and appends it to your local `.bib` file.

**Use when** you need to add new references to your bibliography file without manually typing BibTeX entries.

---

## When to Use This Skill

Use this skill when:
- You have a DOI for a paper and need to add it to your bibliography
- You have a journal article URL and need BibTeX format
- You found a paper on arXiv and want to add it
- You need to add multiple papers from a list of DOIs/URLs
- You want to verify and clean up existing BibTeX entries

---

## Core Workflow

### Single Paper Extraction

**Input**: DOI or URL

**Process**:
1. Clean the identifier (extract DOI if URL provided)
2. Query metadata from appropriate source (CrossRef, PubMed, arXiv, or web page)
3. Format as standard BibTeX
4. Generate appropriate citation key
5. Append to specified .bib file

**Usage**:
```
"Add this paper to my bibliography: 10.1038/s41586-021-03926-0"
"Extract bibliography from: https://www.nature.com/articles/s41586-021-03926-0"
"Add to references.bib: DOI 10.1126/science.abf5641"
```

### Batch Extraction

**Input**: Multiple DOIs/URLs (from file or list)

**Process**:
1. Read all identifiers
2. Process each in sequence with rate limiting
3. Format all entries
4. Append to .bib file
5. Report successes and failures

**Usage**:
```
"Add these DOIs to my bibliography:
- 10.1038/s41586-021-03926-0
- 10.1126/science.abf5641
- 10.1016/j.cell.2024.01.001"

"Extract all papers from dois.txt and append to references.bib"
```

---

## Metadata Sources

### 1. CrossRef API (Primary)

**Best for**: Journal articles with DOIs

**Endpoint**: `https://api.crossref.org/works/{doi}`

**Accept header**: `application/x-bibtex` for direct BibTeX

**Coverage**: Most academic publishers

```bash
# Direct BibTeX from CrossRef
curl -LH "Accept: application/x-bibtex" https://doi.org/10.1038/s41586-021-03926-0
```

**Fields extracted**: author, title, journal, volume, issue, pages, year, DOI, URL

### 2. PubMed E-utilities

**Best for**: Biomedical literature (PMID)

**Endpoint**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`

**Process**: ESearch → EFetch

```bash
# Search PubMed
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=QUERY

# Fetch metadata
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=PMID&retmode=xml
```

### 3. arXiv API

**Best for**: Preprints (physics, math, CS, q-bio)

**Endpoint**: `http://export.arxiv.org/api/query`

```bash
# Query arXiv
http://export.arxiv.org/api/query?id_list=2103.14030
```

### 4. Web Page Extraction (Fallback)

**Best for**: Publisher pages without DOI, conference websites

**Process**: Use web-reader MCP to extract citation metadata from HTML

**Look for**: Schema.org JSON-LD, citation meta tags, or visible citation info

---

## Citation Key Generation

Generate citation keys consistently:

**Format**: `{FirstAuthor}{Year}{Keyword}`

**Examples**:
- `Zhou2021Superconductivity` - from "Superconductivity in rhombohedral trilayer graphene"
- `Walsh2021Josephson` - from "Josephson junction infrared single-photon detector"
- `DiBattista2024Infrared` - from "Infrared single-photon detection..."

**Rules**:
- Use first author's last name
- Use 4-digit year
- Use 1-2 key words from title (capitalize first letter)
- Avoid special characters
- Ensure uniqueness (add a, b, c if duplicate)

---

## BibTeX Entry Types

### @article (Journal Articles)

```bibtex
@article{CitationKey,
  author    = {Last, First and Last2, First2 and Last3, First3},
  title     = {Article Title},
  journal   = {Journal Name},
  volume    = {10},
  number    = {3},
  pages     = {123--145},
  year      = {2024},
  doi       = {10.1234/example.2024.123},
  url       = {https://doi.org/10.1234/example.2024.123}
}
```

### @misc (Preprints, Online Resources)

```bibtex
@misc{CitationKey,
  author  = {Last, First},
  title   = {Preprint Title},
  year    = {2024},
  eprint  = {arXiv:2401.12345},
  archive = {arXiv},
  doi     = {10.1234/example},
  url     = {https://arxiv.org/abs/2401.12345}
}
```

### @inproceedings (Conference Papers)

```bibtex
@inproceedings{CitationKey,
  author    = {Last, First},
  title     = {Paper Title},
  booktitle = {Conference Name},
  year      = {2024},
  pages     = {1--10},
  doi       = {10.1234/example}
}
```

---

## Required Fields

| Entry Type | Required Fields | Recommended Fields |
|------------|----------------|-------------------|
| @article | author, title, journal, year | volume, number, pages, doi, url |
| @book | author, title, publisher, year | isbn, edition, url |
| @inproceedings | author, title, booktitle, year | pages, organization, address, doi |
| @misc | author, title, year | doi, url, eprint, howpublished |

---

## Extraction Procedure

### Step 1: Parse Input

**DOI formats to accept**:
- `10.1038/s41586-021-03926-0`
- `https://doi.org/10.1038/s41586-021-03926-0`
- `http://doi.org/10.1038/s41586-021-03926-0`
- `doi:10.1038/s41586-021-03926-0`

**URL formats to accept**:
- `https://www.nature.com/articles/s41586-021-03926-0`
- `https://science.org/doi/10.1126/science.abf5641`
- `https://arxiv.org/abs/2103.14030`
- `https://pubmed.ncbi.nlm.nih.gov/345678901/`

**Extract DOI from URL**:
- Look for `/doi/10.` pattern
- Look for `doi.org/` pattern
- Check meta tags for DOI
- Check JSON-LD schema for DOI

### Step 2: Determine Metadata Source

```
IF input is DOI:
    Try CrossRef API first (accept: application/x-bibtex)
    IF fails, try web page extraction

ELIF input is PMID:
    Use PubMed E-utilities

ELIF input is arXiv ID:
    Use arXiv API

ELIF input is URL:
    IF URL contains DOI:
        Use DOI extraction
    ELIF URL is arXiv:
        Use arXiv API
    ELIF URL is PubMed:
        Extract PMID and use E-utilities
    ELSE:
        Use web page extraction (web-reader MCP)
```

### Step 3: Extract Metadata

**Via CrossRef** (direct BibTeX):
```bash
curl -sLH "Accept: application/x-bibtex; charset=utf-8" \
  "https://doi.org/$DOI"
```

**Via PubMed** (JSON):
```bash
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=$PMID&retmode=json"
```

**Via arXiv** (XML/JSON):
```bash
curl -s "http://export.arxiv.org/api/query?id_list=$ARXIV_ID"
```

**Via Web Page**:
```bash
# Use web-reader MCP
# Extract JSON-LD, meta tags, or visible citation info
```

### Step 4: Validate and Clean

**Check**:
- [ ] Author names properly formatted (Last, First)
- [ ] Title present and correctly capitalized
- [ ] Year is valid (4 digits)
- [ ] Required fields for entry type present
- [ ] DOI resolves correctly (if present)
- [ ] URL is accessible (if present)
- [ ] Special characters escaped (use braces {} around titles with capitalization)

**Clean**:
- Convert `@data{` to `@misc{` (CrossRef sometimes uses this)
- Standardize page ranges (use `--` not `-`)
- Remove excessive whitespace
- Ensure consistent indentation

### Step 5: Generate Citation Key

1. Extract first author's last name
2. Extract year
3. Extract 1-2 keywords from title
4. Format: `{LastAuthor}{Year}{Keyword}`
5. Check against existing keys for duplicates
6. Add letter suffix if needed: `{LastAuthor}{Year}{Keyword}b`

### Step 6: Append to .bib File

**Procedure**:
1. Read existing .bib file
2. Parse existing citation keys
3. Generate new key (avoiding duplicates)
4. Format entry with consistent indentation
5. Add blank line between entries
6. Append to file

**Example append**:
```python
# Ensure blank line between entries
with open('references.bib', 'a') as f:
    f.write('\n\n')
    f.write(bibtex_entry)
```

---

## Batch Processing

For multiple papers:

1. Read input file (one identifier per line)
2. Process each identifier
3. Track successes and failures
4. Report summary
5. Write successful entries to .bib file

**Example input file (`dois.txt`)**:
```
10.1038/s41586-021-03926-0
https://doi.org/10.1126/science.abf5641
2103.14030
https://www.nature.com/articles/s41586-023-06312-0
```

**Processing output**:
```
[1/4] Processing: 10.1038/s41586-021-03926-0
       -> SUCCESS: Zhou2021Superconductivity

[2/4] Processing: https://doi.org/10.1126/science.abf5641
       -> SUCCESS: Walsh2021Josephson

[3/4] Processing: 2103.14030
       -> SUCCESS: Author2021Keyword

[4/4] Processing: https://www.nature.com/articles/s41586-023-06312-0
       -> SUCCESS: Ruby2023Proximity

Summary: 4/4 successful, 0 failed
Output: references.bib (updated)
```

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|--------|--------|----------|
| DOI not found (404) | Invalid DOI or not indexed | Verify DOI, try web search |
| Timeout | Network issue | Retry with longer timeout |
| Missing required fields | Incomplete metadata | Use web page extraction as fallback |
| Duplicate citation key | Key already exists | Add letter suffix (a, b, c) |
| Invalid BibTeX syntax | API returned malformed data | Manually fix or use web extraction |

### Fallback Strategy

If primary source fails:
1. Try alternative API (e.g., if CrossRef fails, try web page)
2. Use web-search-prime to find the paper
3. Extract from search result page
4. Ask user for manual input if all fails

---

## Best Practices

### Citation Keys
- Be consistent: FirstAuthorYearKeyword
- Use meaningful keywords from title
- Avoid special characters
- Handle duplicates with letter suffixes

### BibTeX Quality
- Use `--` for page ranges
- Protect title capitalization with `{}`: `{Quantum} {Coherence}`
- Include DOI for all modern papers
- Use full journal names, not abbreviations

### Validation
- Always verify DOIs resolve
- Check author names against publication
- Confirm volume/pages/year match
- Test BibTeX compiles with LaTeX

### Organization
- Use one .bib file per project
- Keep backups before modifications
- Sort entries (by year, author, or citation key)
- Remove duplicates regularly

---

## Integration with LaTeX

After appending to .bib file:

```latex
\documentclass{article}
\usepackage[style=authoryear]{biblatex}

\addbibresource{references.bib}

\begin{document}
... your content ...

\printbibliography
\end{document}
```

Compile with:
```bash
pdflatex document.tex
biber document
pdflatex document.tex
pdflatex document.tex
```

---

## Example Session

**User**: Add this DOI to my bibliography: 10.1038/s41586-021-03926-0

**Process**:
1. Parse input: DOI = 10.1038/s41586-021-03926-0
2. Query CrossRef with `Accept: application/x-bibtex`
3. Receive BibTeX entry
4. Generate citation key: `Zhou2021Superconductivity`
5. Read existing `references.bib`
6. Append new entry with blank line separator
7. Confirm success

**Output**:
```
✓ Added Zhou2021Superconductivity to references.bib

Entry:
@article{Zhou2021Superconductivity,
  author    = {Zhou, H. and others},
  title     = {Superconductivity in rhombohedral trilayer graphene},
  journal   = {Nature},
  volume    = {598},
  number    = {7881},
  pages     = {434--438},
  year      = {2021},
  doi       = {10.1038/s41586-021-03926-0},
  url       = {https://doi.org/10.1038/s41586-021-03926-0}
}
```

---

## Quick Reference Commands

**Single DOI**:
```
"Add DOI 10.1038/s41586-021-03926-0 to references.bib"
```

**URL**:
```
"Extract bibliography from https://www.nature.com/articles/s41586-021-03926-0"
```

**Multiple DOIs**:
```
"Add these to my bibliography.bib:
10.1038/s41586-021-03926-0
10.1126/science.abf5641
10.1016/j.cell.2024.01.001"
```

**From file**:
```
"Extract all DOIs from dois.txt and append to bibliography.bib"
```

**Specify output file**:
```
"Add DOI 10.1038/s41586-021-03926-0 to mypaper_refs.bib"
```

---

## Summary

The bib-extractor skill provides:
1. **Quick extraction** from DOIs, URLs, PMIDs, arXiv IDs
2. **Multiple metadata sources** (CrossRef, PubMed, arXiv, web)
3. **BibTeX formatting** with proper entry types
4. **Citation key generation** with duplicate handling
5. **File appending** to local .bib files
6. **Batch processing** for multiple papers

Use this skill to quickly build and maintain your bibliography without manual BibTeX entry.
