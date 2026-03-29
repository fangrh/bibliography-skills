# /bib-searcher - Sentence-Aware Citation Search and Update

Read a LaTeX, Markdown, or plain-text document sentence by sentence, decide which statements need citations, reuse existing references first, and search for new citations only when necessary.

Final references must be materialized through `bib-extractor`. `bib-searcher` may rank candidates, but it must not output a citation ready for insertion into a draft unless that citation has first been reused from or written into the target `.bib` file by `bib-extractor`.

## Usage

```
/bib-searcher [document] [options]
```
