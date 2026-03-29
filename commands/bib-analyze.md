# /bib-analyze - Analyze Text for Missing Citations

Analyze documents to find sentences that need citations but don't have them, then automatically search for relevant references.

## Usage

```
/bib-analyze [document] [options]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|-----------|
| `document` | Input file to analyze (.tex, .md, .txt) | Yes |
| `--no-search` | Analyze only, do not search for citations | Optional |
| `--max-results` | Max search results per sentence (default: 3) | Optional |
| `--timeout` | Search timeout in seconds (default: 15) | Optional |
| `--show-ok` | Show sentences that don't need citations | Optional |
| `--format` | Output format: `text` or `json` (default: text) | Optional |

## How It Works

### Step 1: Sentence Analysis

For each sentence, the system checks:

```
┌────────────────────────────────────────────────────────────┐
│ Does this sentence need a citation?                         │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  HIGH NEED indicators:                                      │
│  ───────────────────────────────────────────────            │
│  • Numerical claims: "achieves 99%", "2x faster"           │
│  • Named methods: "BERT", "ResNet", "Transformer"          │
│  • Factual claims: "shown that", "demonstrates"            │
│  • Comparative: "outperforms", "better than"               │
│  • Findings: "discovered", "revealed", "observed"          │
│  • Statistical: "p-value", "significant", "confidence"     │
│                                                             │
│  LOW NEED indicators:                                       │
│  ───────────────────────────────────────────────            │
│  • Common knowledge: "is a standard technique"             │
│  • General references: "many studies have shown"           │
│  • Opinions: "we believe", "it seems"                      │
│                                                             │
│  Score: 0.0 (no need) → 1.0 (definitely needs citation)    │
│  Threshold: ≥ 0.3 and no existing citation → NEEDS CITE    │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### Step 2: Citation Detection

Recognizes existing citations:
- LaTeX: `\cite{...}`, `\citep{...}`, `\citet{...}`
- Pandoc: `@citation`
- Author-Year: `[Author, 2020]`, `(Smith et al., 2021)`

### Step 3: Auto-Search

If citation needed but missing:
1. Extract keywords from sentence
2. Search CrossRef for matching papers
3. Return top suggestions with DOI, title, authors, year

## Example Output

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

• "Quantum sensing achieves nanoscale temperature resolution..."
  Confidence: 75%
  Reason: Citation recommended: percentage_claim, achievement_claim
  Search: quantum sensing nanoscale temperature resolution
  Suggestions:
    - Nanometre-scale thermometry in a living cell...
      Kucsko, G. and Maurer, P. C. (2013)
      DOI: 10.1038/nature12373

• "Our method outperforms existing approaches by 15%..."
  Confidence: 85%
  Reason: Citation recommended: comparative_numerical, comparative_claim
  Search: method outperforms approaches existing
  Suggestions:
    - Comparative analysis of machine learning methods...
      Zhang, L. (2022)
      DOI: 10.1234/example
```

## Pattern Recognition

### Statements That Need Citations

| Pattern | Example |
|---------|---------|
| Numerical claim | "accuracy of 95%" |
| Comparative claim | "outperforms by 2x" |
| Named method | "using BERT" |
| Factual claim | "has been shown that" |
| Research finding | "we discovered that" |
| Statistical | "p < 0.05" |
| Measurement | "at 4.2 Kelvin" |

### Statements That Don't Need Citations

| Pattern | Example |
|---------|---------|
| Common knowledge | "is a well-known technique" |
| General reference | "many studies have" |
| Opinion | "we believe that" |
| Definitions | "is defined as" |
| Introduction | "In this paper, we..." |

## Examples

```bash
# Analyze a LaTeX document
/bib-analyze paper.tex

# Analyze without auto-searching
/bib-analyze paper.tex --no-search

# Get JSON output for further processing
/bib-analyze paper.tex --format json > analysis.json

# Show all sentences, including OK ones
/bib-analyze paper.tex --show-ok

# More search results per sentence
/bib-analyze paper.tex --max-results 5
```

## Integration with Other Commands

```bash
# 1. Analyze document for missing citations
/bib-analyze paper.tex

# 2. Extract suggested citations
/bib-extractor 10.1038/nature12373 --abstract

# 3. Add to document
/bib-track references.bib --documents paper.tex

# 4. Validate citations
/bib-sync references.bib --validate-citations
```

## JSON Output Format

```json
{
  "total_sentences": 45,
  "sentences_needing_citation": 8,
  "sentences_with_citations": 12,
  "sentences_ok": 25,
  "analyses": [
    {
      "sentence": "Quantum sensing achieves...",
      "needs_citation": true,
      "confidence": 0.75,
      "reason": "Citation recommended: percentage_claim",
      "has_citation": false,
      "search_terms": ["quantum", "sensing", "achieves"],
      "suggestions": [
        {
          "doi": "10.1038/nature12373",
          "title": "Nanometre-scale thermometry...",
          "authors": "Kucsko, G.",
          "year": 2013
        }
      ]
    }
  ]
}
```
