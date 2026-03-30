---
name: bib-searcher
description: "Use when auditing a draft sentence by sentence for citation needs, reusing an existing bibliography first, and searching for supporting papers only when needed."
---

# Bib Searcher

Use this skill when the user wants help deciding which sentences need citations or which references best support a sentence in a draft.

Hard rule: any citation that ends up in a draft must be finalized through `bib-extractor`. This skill can analyze, search, and rank candidates, but it must not treat a citation as ready for insertion until the paper has been reused from or normalized into the target `.bib` file.

## Core Workflow

1. Split the draft into sentences.
2. Ignore obvious common-knowledge statements.
3. Flag factual or quantitative claims that need support.
4. Reuse the current `.bib` file first when possible.
5. Search external sources only for unsupported claims.
6. Hand any newly selected identifier back to `bib-extractor`.
7. Return citation suggestions only after normalization succeeds.

## Examples

```text
Search draft.tex and update citations using references.bib first
Audit already cited quantitative claims in paper.tex
Find better published references for unsupported claims in this report
```

## Notes

- Shared implementation lives in `scripts/bib_smart_search.py`.
- Prefer local bibliography matches before external search.
- Keep extractor finalization as the last gate before editing the draft or presenting a final citation string.
