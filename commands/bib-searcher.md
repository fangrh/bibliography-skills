# /bib-searcher - Sentence-Aware Citation Search and Update

Read a LaTeX, Markdown, or plain-text document sentence by sentence, decide which statements need citations, reuse existing references first, and search for new citations only when necessary.

**CRITICAL**: Final references must be materialized through `bib-extractor`. `bib-searcher` may rank candidates, but it must not output a citation ready for insertion into a draft unless that citation has first been reused from or written into the target `.bib` file by `bib-extractor`.

## Usage

```
/bib-searcher [document] [options]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `document` | Input file to analyze (.tex, .md, or .txt) | Yes |
| `--bib-file, -b` | Target bibliography file to search first and write to | Recommended |
| `--no-search` | Analyze only, do not search for citations | Optional |
| `--max-results` | Max search results per sentence (default: 3) | Optional |
| `--timeout` | Search timeout in seconds (default: 15) | Optional |
| `--show-ok` | Show sentences that don't need citations | Optional |
| `--audit-cited` | Also audit sentences with existing citations | Optional |
| `--allow-arxiv` | Include arXiv/preprint results | Optional |
| `--full-journal-name` | Use full journal names in inline citations | Optional |
| `--format` | Output format: `text` or `json` (default: text) | Optional |

## Process

1. **Read document** - Split into sentences, identify citation patterns
2. **Analyze each sentence** - Determine if citation needed based on:
   - Numerical/quantitative claims
   - Method/technique references
   - Factual claims requiring evidence
   - Comparative claims against prior work
3. **Check existing citations** - Skip sentences already properly cited
4. **Search local bibliography first** - When `--bib-file` is provided:
   - Parse existing `.bib` entries
   - Match candidates using term overlap + quantitative matching
   - Reuse existing entries when possible
5. **Search external sources** - Only when local search fails:
   - CrossRef API (primary)
   - OpenAlex API (fallback)
6. **Rerank candidates** - Score by:
   - Term overlap with sentence
   - Quantitative value matching
   - Domain anchor term matching
7. **Finalize through bib-extractor** - Before inserting any citation:
   - DOI must be normalized into target `.bib` file
   - Generate inline citation format

## Workflow Integration

### Step 1: Analyze Document

```bash
python scripts/bib_smart_search.py document.tex --bib-file references.bib
```

### Step 2: For Each Needed Citation

If local match found:
```
/bib-extractor --reuse <cite_key> --output references.bib
```

If external search needed:
```
/bib-extractor <DOI> --output references.bib
```

### Step 3: Insert Citations

Only after bib-extractor confirms the entry exists in the target `.bib` file:
- Insert `\cite{cite_key}` into the document
- Or use inline format: `Journal, Volume, Pages, (Year)`

## Examples

### Basic Analysis

```bash
# Analyze document and find missing citations
/bib-searcher paper.tex --bib-file references.bib

# Analyze with JSON output for programmatic processing
/bib-searcher paper.tex --bib-file references.bib --format json
```

### Analysis Only (No Search)

```bash
# Identify which sentences need citations without searching
/bib-searcher paper.tex --no-search
```

### Comprehensive Audit

```bash
# Audit all sentences including those with existing citations
/bib-searcher paper.tex --bib-file references.bib --audit-cited --show-ok
```

### Include Preprints

```bash
# Include arXiv results (useful for cutting-edge research)
/bib-searcher paper.tex --bib-file references.bib --allow-arxiv
```

## Citation Need Detection

The script identifies sentences needing citations based on patterns:

| Pattern Type | Examples |
|--------------|----------|
| **Numerical claims** | "achieves 95% accuracy", "increased by 2.5x" |
| **Method references** | "using BERT", "via ResNet" |
| **Factual claims** | "shown that...", "demonstrated to..." |
| **Comparative** | "outperforms SOTA", "better than" |
| **Statistical** | "p-value < 0.05", "statistically significant" |

## Local Bibliography Priority

When `--bib-file` is provided, the script:

1. Parses existing BibTeX entries
2. Extracts title, authors, abstract, journal fields
3. Scores each entry against the sentence:
   - Term overlap score
   - Quantitative value matching
   - Domain anchor matching (e.g., "superconducting qubit", "phonon")
4. Returns top matches with `source: local-bib`
5. Only searches external APIs if no local matches found

## Output Format

### Text Output

```
============================================================
Citation Need Analysis Report
============================================================
Total sentences: 45
Sentences with citations: 12
Sentences needing citation: 8
Sentences OK (no citation needed): 25

------------------------------------------------------------
Sentences Needing Citations:
------------------------------------------------------------

• "Strain modulation of critical temperature by up to 0.92 K..."
  Confidence: 65%
  Reason: Citation recommended: percentage_claim, comparative_numerical
  Search: strain modulation critical temperature nbse2
  Suggestions:
    - Controllable Superconductivity in Suspended van der Waals...
      Fang et al. (2025)
      DOI: 10.1038/s41467-0xx-xxxxx-x
      Inline: Nat. Commun., 15, 2314, (2025)
```

### JSON Output

```json
{
  "total_sentences": 45,
  "sentences_needing_citation": 8,
  "sentences_with_citations": 12,
  "analyses": [
    {
      "sentence": "Strain modulation...",
      "needs_citation": true,
      "confidence": 0.65,
      "reason": "Citation recommended...",
      "has_citation": false,
      "search_terms": ["strain", "modulation", "critical", "temperature"],
      "suggestions": [
        {
          "doi": "10.1038/s41467-0xx-xxxxx-x",
          "title": "Controllable Superconductivity...",
          "authors": "Fang et al.",
          "year": 2025,
          "inline_citation": "Nat. Commun., 15, 2314, (2025)",
          "score": 2.45
        }
      ]
    }
  ]
}
```

## Integration with bib-extractor

**HARD RULE**: No citation may be inserted into a draft unless:

1. The DOI/identifier has been processed by `bib-extractor`
2. The BibTeX entry exists in the target `.bib` file
3. `bib-extractor` has confirmed successful normalization

This ensures:
- Consistent citation key format
- Proper metadata normalization
- Journal name abbreviation compliance
- No duplicate entries

## Notes

- Requires `requests` package: `pip install requests`
- Rate limiting applies between external API requests
- Local bibliography search is instant (no rate limits)
- Supports LaTeX, Markdown, and plain text documents
- Citation patterns detected: `\cite{}`, `\citep{}`, `\citet{}`, `@citation`, `[Author, Year]`
