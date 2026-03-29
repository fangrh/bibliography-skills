# /bib-sync - Synchronize Bibliography Library

Synchronize your BibTeX library with online sources to update metadata, citation counts, and remove invalid entries. Works like Zotero's "Update Metadata" feature.

## Usage

```
/bib-sync [bib-file] [options]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|-----------|
| `bib-file` | Path to BibTeX file (default: references.bib) | Optional |
| `--dry-run` | Preview changes without modifying file | Optional |
| `--remove-invalid` | Remove entries that cannot be matched | Optional |
| `--update-citations` | Update citation counts from CrossRef/OpenAlex | Optional |
| `--validate-citations` | Validate if citations support their usage context | Optional |
| `--search-replacements` | Search for replacements for unsupported citations | Optional |
| `--full-journal-name` | Use full journal names instead of abbreviations | Optional |
| `--delay` | Delay between requests in seconds (default: 1.0) | Optional |
| `--verbose, -v` | Show detailed progress | Optional |

## Semantic Matching Algorithm

The system uses **TF-IDF + Cosine Similarity** for fast and accurate citation validation:

### Matching Metrics (Combined Score)

| Metric | Weight | Description |
|--------|--------|-------------|
| TF-IDF Similarity | 40% | Term frequency-inverse document frequency |
| Keyword Overlap | 40% | Direct keyword matching ratio |
| Bigram Overlap | 20% | 2-word phrase matching for context |

### Score Thresholds

| Combined Score | Status | Action |
|----------------|--------|--------|
| ≥ 0.25 | ✓ Supported | Keep citation |
| 0.12 - 0.25 | ? Unclear | Review manually |
| < 0.12 | ✗ Unsupported | Remove/replace |

### Example

```python
# Sentence with citation
"Quantum sensing enables precise measurements [Zhang2020]."

# Paper abstract
"This paper demonstrates quantum sensing using NV centers..."

# Matching result:
{
  "tfidf_similarity": 0.35,
  "keyword_overlap": 0.56,
  "bigram_overlap": 0.25,
  "combined_score": 0.42,
  "status": "supported",
  "matched_keywords": ["quantum", "sensing", "precise", "measurements"]
}
```

## Multi-Citation Validation (Priority Logic)

When a sentence contains **multiple citations** like `[1,2,3]`, the system follows this priority:

```
┌─────────────────────────────────────────────────────────────┐
│ Example: "Quantum sensing enables precise measurements [1,2,3]." │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Step 1: Check each citation individually                    │
│  ───────────────────────────────────────────                 │
│  [1] → 85% match ✓ SUPPORTED                                 │
│  [2] → 10% match ✗ UNSUPPORTED                               │
│  [3] → 72% match ✓ SUPPORTED                                 │
│                                                              │
│  Step 2: Decide action based on results                      │
│  ────────────────────────────────────────                    │
│                                                              │
│  ┌─ SOME citations supported?                                │
│  │  ├─ YES → REMOVE unsupported, KEEP supported              │
│  │  │        Result: "Quantum sensing enables precise        │
│  │  │                measurements [1,3]."                     │
│  │  │        (Citation [2] removed)                          │
│  │  │                                                        │
│  │  └─ NO (ALL unsupported) → Try sentence revision          │
│  │                            ↓                               │
│  │                    Can revise?                             │
│  │                    ├─ YES → Suggest revision               │
│  │                    │        based on best-matching paper   │
│  │                    │                                        │
│  │                    └─ NO → Search for replacement          │
│  │                            citations (exclude originals)   │
│  │                            ↓                                │
│  │                    Found replacements?                     │
│  │                    ├─ YES → Suggest replacements           │
│  │                    └─ NO → Flag for manual review          │
│  │                                                          │
│  └──────────────────────────────────────────────────────────┘
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Cross-Sentence Citation Tracking

A citation may be used in **multiple sentences**. The system tracks:

```
Citation [Zhang2020]:
├─ Sentence 1 (intro.tex): 85% match ✓ → KEEP here
├─ Sentence 2 (methods.tex): 10% match ✗ → REMOVE from this sentence
└─ Sentence 3 (results.tex): 72% match ✓ → KEEP here

Overall: PARTIAL SUPPORT
Action: Remove citation from Sentence 2, keep elsewhere
```

## Validation Priority Summary

| Priority | Condition | Action |
|----------|-----------|--------|
| **1** | All citations supported | ✓ Keep all |
| **2** | Some supported, some not | → Remove unsupported only |
| **3** | All unsupported + can revise | → Revise sentence |
| **4** | All unsupported + cannot revise | → Search replacements |
| **5** | No replacements found | ⚠ Manual review |

## Anti-Loop Protection

When searching for replacements, the system:
1. Tracks the original DOI
2. Tracks all rejected replacement DOIs
3. Excludes all tracked DOIs from future searches
4. Limits to 3 replacement attempts per citation

## Example Output

```
[paper.tex] Multi-citation sentence (3 citations):
  Sentence: "Quantum sensing enables precise measurements [1,2,3]..."
  ✓ Supported: 2, ✗ Unsupported: 1
  Citations to KEEP: Zhang2020Quantum, Wang2021Sensing
  Citations to REMOVE: Smith2019Temperature
  → Action: Remove unsupported citations, keep others

[paper.tex] Multi-citation sentence (2 citations):
  Sentence: "High-temperature superconductivity [4,5]..."
  ✓ Supported: 0, ✗ Unsupported: 2
  → Action: Revise sentence (all citations unsupported)
    Paper [Lee2021Cuprate]: This paper demonstrates superconductivity in cuprate...
```

## Performance Tips

- **With scikit-learn**: TF-IDF calculations are optimized (~10x faster)
- **Without scikit-learn**: Uses manual cosine similarity (slower but works)
- **Fast mode**: Add `--fast` to use simpler keyword matching

## Workflow

1. **Parse BibTeX file** - Read all entries from the library

2. **For each entry with DOI or URL**:
   - Fetch fresh metadata from CrossRef/arXiv/PubMed
   - Update fields (authors, title, journal, volume, pages, etc.)
   - Update citation count if `--update-citations` is set
   - Keep original citation key

3. **For entries without DOI or URL**:
   - Search by title using web search
   - Match results with author names and year
   - If match found: add DOI/URL and update metadata
   - If no match and `--remove-invalid`: mark for removal

4. **Validate entries**:
   - Check DOI validity
   - Verify required fields exist
   - Flag incomplete entries

5. **Write updated library**:
   - Preserve formatting and comments
   - Remove invalid entries (if `--remove-invalid`)
   - Generate sync report

## Examples

```
# Basic sync
/bib-sync references.bib

# Preview changes without modifying
/bib-sync references.bib --dry-run

# Sync and remove entries that can't be matched
/bib-sync my_papers.bib --remove-invalid

# Full sync with citation counts
/bib-sync references.bib --update-citations --verbose

# Sync all .bib files in current directory
/bib-sync *.bib
```

## Matching Algorithm

For entries without DOI/URL, the sync process:

1. **Search** using title keywords via Google Scholar/CrossRef
2. **Score** each result based on:
   - Title similarity (Levenshtein distance)
   - Author name matching (first author last name)
   - Year matching
3. **Accept** if score exceeds threshold (0.8)
4. **Reject** if no good match found

## Sync Report

After completion, displays:

```
Sync Report for references.bib
===============================
Total entries: 45
Updated: 32
  - DOI updated: 5
  - Metadata refreshed: 27
  - Citation counts updated: 18
Matched (no DOI): 8
Unmatched: 3
  - Entry1 (title: "Unknown Paper")
  - Entry2 (title: "Another Paper")
Removed: 2
Errors: 0
```

## Entry States

| State | Description | Action |
|-------|-------------|--------|
| Updated | Successfully synced with source | Keep |
| Matched | Found DOI via title search | Keep, add DOI |
| Unmatched | Could not find match | Keep (or remove with `--remove-invalid`) |
| Invalid | DOI returns 404 | Remove |
| Error | Network/API error | Keep, retry later |

## Notes

- Requires `requests` package: `pip install requests`
- Rate limiting applies between requests
- Original citation keys are preserved
- Comments and string macros are preserved
- Backup file created before modification (`.bak`)

## LLM-Based Validation

Use `--llm-validate` to generate prompts for the agent (Claude) to evaluate citation-sentence matching. The system outputs structured JSON that the agent can evaluate.

```
# Generate LLM validation prompts
/bib-sync references.bib --llm-validate

# Example output (pass to agent for evaluation):
{
  "task": "validate_citation",
  "citation_key": "Zhang2020Quantum",
  "paper_metadata": {
    "title": "Quantum sensing with NV centers",
    "abstract": "This paper demonstrates...",
    "note": "Used for quantum measurement techniques"
  },
  "context_sentences": [
    "Quantum sensing enables precise measurements [Zhang2020Quantum]."
  ],
  "evaluation_criteria": {
    "match_score": "1-100",
    "relevance": "Is the citation appropriate?",
    "confidence": "How confident are you?"
  }
}
```

## Smart Sync Workflow

Use `--smart-sync` for intelligent citation management with LLM validation:
```
# Smart sync with documents
/bib-sync references.bib --smart-sync --documents paper.tex

# Workflow:
# 1. Parse documents to find citation contexts
# 2. For each citation:
#    a. Check if already exists in library
#    b. If exists: Update note with new usage context
#    c. If not exists: Add new entry from DOI
# 3. Validate citations with LLM (if --llm-validate)
# 4. Handle inappropriate citations (revise/replace/remove)
```

## Integration
This command works with:
- `/bib-extractor` - Used internally for metadata fetching
- `/bib-preview` - Preview synced library
- `/bib-search` - For title-based searching
- `/bib-track` - For citation context tracking

---

**Full workflow example:**
```bash
# Preview what would change
/bib-sync references.bib --dry-run

# Perform smart sync with LLM validation
/bib-sync references.bib --smart-sync --documents paper.tex --llm-validate

# Preview the result
/bib-preview references.bib
```
