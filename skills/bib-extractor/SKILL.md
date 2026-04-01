---
name: bib-extractor
description: "Use when adding a DOI, URL, PMID, or arXiv identifier to a BibTeX file and you need a normalized bibliography entry."
---

# Bib Extractor

Use this skill when the user already knows which paper they want and needs a normalized BibTeX entry in a local `.bib` file.

## Core Workflow

1. Clean the identifier.
2. Run the extractor against the shared script in `scripts/bib_extractor.py`, which uses papis CLI for metadata fetching.
3. Normalize metadata, citation key, DOI, URL, and journal fields.
4. Append to the target `.bib` file, or print only if requested.

## Examples

```text
Add DOI 10.1038/s41586-021-03926-0 to references.bib
Extract BibTeX from https://doi.org/10.1126/science.abf5641
Print BibTeX for PMID 345678901 without writing the file
```

## Notes

- Shared implementation lives in `scripts/bib_extractor.py`.
- Prefer reusing an existing entry in the target `.bib` file when the user asks to avoid duplicates.
- If the user asks for inline citation text, generate it from the normalized result rather than improvising metadata by hand.
