---
name: bibliography-skills
description: Use when managing local BibTeX libraries in Codex through two maintained workflows: extracting normalized entries from paper identifiers and searching documents sentence-by-sentence to suggest or update citations.
---

# Bibliography Skills

## Overview

This repository now exposes two maintained bibliography workflows:

- `bib-extractor`: fetch and normalize BibTeX entries from DOIs, URLs, PMIDs, and arXiv IDs
- `bib-searcher`: read a document sentence by sentence, decide which statements need support, reuse existing references first, and search for new citations only when necessary

Use this skill when you want Codex to help maintain `.bib` files and citation-heavy drafts without manually formatting BibTeX entries.

## Natural-Language Routing

Route user requests to one of the two maintained workflows:

- "Add DOI 10.1038/... to references.bib" -> `bib-extractor`
- "Clean up this URL into BibTeX" -> `bib-extractor`
- "Search this draft for unsupported claims" -> `bib-searcher`
- "Reuse references.bib to update citations in paper.tex" -> `bib-searcher`
- "Find better citations for quantitative claims" -> `bib-searcher`

## Workflow 1: `bib-extractor`

Use `bib-extractor` when the user already knows the identifier for a paper and needs a normalized BibTeX entry.

Core behavior:

1. Clean the identifier
2. Query the appropriate metadata source
3. Normalize journal, volume, issue, pages or article number, year, DOI, and URL
4. Generate or preserve a usable citation key
5. Append or print the BibTeX entry

Examples:

```text
Add DOI 10.1038/s41586-021-03926-0 to references.bib
Extract bibliography from https://doi.org/10.1126/science.abf5641
Print BibTeX for PMID 345678901 without writing the file
```

## Workflow 2: `bib-searcher`

Use `bib-searcher` when the user wants help deciding where citations are needed or which references best support a sentence.

Core behavior:

1. Split the document into sentences
2. Ignore obvious common-knowledge sentences
3. Flag factual or quantitative claims that need support
4. Reuse the current `.bib` file first when possible
5. Search external sources only for unsupported claims
6. Hand any newly selected DOI back to `bib-extractor` for normalization
7. Return inline citation suggestions in `Journal, volume, page, (year)` format

Examples:

```text
Search draft.tex and update citations using references.bib first
Audit already cited quantitative claims in paper.tex
Find the best published references for unsupported claims in this report
```

## Scope

This repository no longer maintains separate note, preview, sync, lint, track, or analyze skills. Those behaviors should be implemented, when needed, as subflows under `bib-searcher` rather than as standalone skills or commands.
