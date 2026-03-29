# /bib-search - Search and Extract Bibliography

Search for academic papers on the web (Google Scholar, PubMed, arXiv) and automatically extract BibTeX entries for found references.

## Usage

```
/bib-search [query] [options]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|-----------|
| `query` | Search query for finding papers | Yes |
| `--type, -t` | Paper type/category (journal, arxiv, book, thesis, all) | Optional (default: all) |
| `--limit, -n` | Number of results to process (default: 3) | Optional |
| `--source, -s` | Search source: `scholar`, `pubmed`, `arxiv`, `all` | Optional (default: all) |
| `--output, -o` | Output BibTeX file | Optional (default: references.bib) |
| `--no-extract` | Search only, don't extract BibTeX | Optional |
| `--interactive` | Ask user which results to include | Optional |

## Workflow

1. **Ask for search criteria** (if not provided)
   - What topic/keywords?
   - What type of paper? (journal, preprint, book, thesis)
   - How many results?

2. **Search web for papers** using available MCP/skills:
   - `citation-management` skill (Google Scholar, PubMed)
   - `research-lookup` skill (academic paper searches)
   - `web-search-prime` MCP (general web search)
   - `web-reader` MCP (extract content from URLs)

3. **Extract DOIs/URLs** from search results

4. **Use `/bib-extractor`** to fetch and format BibTeX

5. **Append to output file** with proper citation keys

## Examples

```
# Basic search
/bib-search "quantum coherence error correction"

# Search arXiv only
/bib-search "deep learning attention" --type arxiv --source arxiv

# Interactive search with custom output
/bib-search "machine learning interpretability" --interactive -o ml_papers.bib

# Search and get 5 results, don't extract
/bib-search "neuromorphic computing" --limit 5 --no-extract

# Search for specific journal papers
/bib-search "quantum supremacy" --type journal --source scholar
```

## Search Types

| Type | Description | Typical Sources |
|-------|-------------|----------------|
| `journal` | Peer-reviewed journal articles | Google Scholar, PubMed |
| `arxiv` | Preprints on arXiv | arXiv.org |
| `book` | Books, book chapters | Google Books, WorldCat |
| `thesis` | PhD/master's theses | ProQuest, ETH Zurich |
| `all` | All types | Combined search |

## Search Sources

| Source | Coverage |
|---------|----------|
| `scholar` | Google Scholar (broad academic coverage) |
| `pubmed` | PubMed/NCBI (biomedical) |
| `arxiv` | arXiv (physics, math, CS preprints) |
| `all` | All available sources |

## Output

For each found paper, the command will:

1. **Display** search results with:
   - Title
   - Authors
   - Year
   - DOI/URL
   - Abstract preview

2. **Extract** BibTeX (unless `--no-extract`):
   - Uses `/bib-extractor` internally
   - Generates proper citation keys
   - Includes all fields (note, abstract)
   - Appends to specified `.bib` file

3. **Summary** report:
   - Papers found
   - Successfully extracted
   - Failed extractions

## Interactive Mode

With `--interactive`, the workflow becomes:

```
Search query: [your query]
Found 5 results:

[1] Author A, Author B et al. "Paper Title" (2024)
    DOI: 10.xxx/yyyy
    Abstract: Preview...

[2] Author C, Author D et al. "Another Paper" (2023)
    URL: https://arxiv.org/abs/xxxx.xxxxx
    Abstract: Preview...

Select papers to include (e.g., 1,3,5 or 'all'): _
```

## Notes

- Requires `requests` package: `pip install requests`
- Uses web search MCP servers when available
- Falls back to skill-based search if MCP unavailable
- Rate limiting applies between extractions
- Duplicate citation keys are handled automatically

## Integration

This command works seamlessly with:
- `/bib-extractor` - for BibTeX extraction
- `/bib-preview` - for LaTeX preview generation

---

**Full workflow example:**
```bash
/bib-search "neural network pruning" --interactive -o neural_papers.bib
# ... review results ...
/bib-preview neural_papers.bib
```