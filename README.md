# Bibliography Skills for Claude Code

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

A Zotero-like bibliography extraction and management suite for Claude Code. Extract bibliography entries from DOIs, URLs, PMIDs, and arXiv IDs, fetch abstracts, generate LLM-based notes, track citation usage, and sync your library with online sources.

## Installation

### Marketplace (Recommended)

```bash
/plugin marketplace add fangrh/bibliography-skills-marketplace
/plugin install bibliography-skills@fangrh-bibliography-skills
```

### Manual Installation

```bash
git clone https://github.com/yourusername/bibliography-skills.git
cd bibliography-skills
pip install -r requirements.txt
```

See [INSTALL.md](INSTALL.md) for detailed manual installation instructions.

## Claude Code Commands

After installation, you can use these commands:

| Command | Description |
|---------|-------------|
| `/bib-extractor` | Extract BibTeX from DOIs, URLs, PMIDs, arXiv IDs with abstracts |
| `/bib-note` | Generate LLM-based notes for bibliography entries |
| `/bib-preview` | Generate LaTeX preview from BibTeX files |
| `/bib-search` | Search and extract bibliography from web |
| `/bib-sync` | Sync library with online sources, validate citations |
| `/bib-track` | Track citation usage in documents, find uncited entries |

### Quick Examples

```bash
# Extract a paper by DOI with abstract
/bib-extractor 10.1038/s41586-021-03926-0 --abstract

# Extract from URL
/bib-extractor https://doi.org/10.1126/science.abf5641

# Batch extract from file
/bib-extractor --input dois.txt --output references.bib

# Generate notes for entries with abstracts
/bib-note references.bib

# Track citation usage in documents
/bib-track references.bib --documents paper.tex

# Generate LaTeX preview
/bib-preview references.bib -o preview.tex

# Search for papers
/bib-search "quantum computing" --limit 5

# Sync library with citation validation
/bib-sync references.bib --update-citations --validate-citations
```

## Python Script Usage

You can also use the Python script directly:

### Single DOI

```bash
./bib_extractor.py 10.1038/s41586-021-03926-0
```

### URL (extracts DOI automatically)

```bash
./bib_extractor.py https://doi.org/10.1126/science.abf5641
./bib_extractor.py https://www.nature.com/articles/s41586-021-03926-0
```

### arXiv ID

```bash
./bib_extractor.py 2103.14030
./bib_extractor.py https://arxiv.org/abs/2103.14030
```

### PMID

```bash
./bib_extractor.py 345678901
./bib_extractor.py https://pubmed.ncbi.nlm.nih.gov/345678901/
```

### Multiple Papers

```bash
./bib_extractor.py 10.1038/s41586-021-03926-0 \
  10.1126/science.abf5641 \
  2103.14030
```

### From File

```bash
# Create a file with one identifier per line
cat > dois.txt << EOF
10.1038/s41586-021-03926-0
https://doi.org/10.1126/science.abf5641
2103.14030
EOF

# Process the file
./bib_extractor.py --input dois.txt --output references.bib
```

### Specify Output File

```bash
./bib_extractor.py -o my_paper_refs.bib 10.1038/s41586-021-03926-0
```

### Print Only (No File Modification)

```bash
./bib_extractor.py --print-only 10.1038/s41586-021-03926-0
```

### Rate Limiting

```bash
# Add delay between requests (seconds)
./bib_extractor.py --delay 2 --input dois.txt
```

## Command Options

```
usage: bib_extractor.py [-h] [-i INPUT] [-o OUTPUT] [--delay DELAY]
                     [--timeout TIMEOUT] [--print-only]
                     [identifiers ...]

positional arguments:
  identifiers           DOI(s), URL(s), PMID(s), or arXiv ID(s)

optional arguments:
  -h, --help            show help message and exit
  -i, --input INPUT     Input file with identifiers (one per line)
  -o, --output OUTPUT   Output BibTeX file (default: references.bib)
  --delay DELAY         Delay between requests in seconds (default: 1.0)
  --timeout TIMEOUT     Request timeout in seconds (default: 15)
  --print-only          Print BibTeX to stdout without appending to file
  --full-journal-name   Use full journal names instead of abbreviations
  --inline              Output inline citation format instead of BibTeX
  --inline-style STYLE  Citation style: journal, author, nature, apa (default: journal)
  --latex-href          Output LaTeX \href command with DOI link
```

## Citation Key Format

Citation keys are generated as: `{FirstAuthor}{Year}{Keyword}`

Examples:
- `Zhou2021Superconductivity`
- `Walsh2021Josephson`
- `DiBattista2024Infrared`

Duplicate keys get letter suffixes: `Smith2024Quantuma`, `Smith2024Quantumb`, etc.

## Journal Abbreviations

By default, journal names are abbreviated following standard academic conventions:

| Full Name | Abbreviation |
|-----------|--------------|
| Physical Review Letters | Phys. Rev. Lett. |
| Physical Review B | Phys. Rev. B |
| Nature Communications | Nat. Commun. |
| Nature Physics | Nat. Phys. |
| Science | Science |
| Nano Letters | Nano Lett. |
| Applied Physics Letters | Appl. Phys. Lett. |

To use full journal names instead:

```bash
./bib_extractor.py 10.1038/s41586-021-03926-0 --full-journal-name
```

Inline citations follow format: `[Journal, Volume, Pages, (Year)]`

## Inline Citations

Generate inline citations for use in LaTeX documents:

```bash
# Basic inline citation (journal style)
./bib_extractor.py --inline --print-only 10.1038/s41586-021-03926-0
# Output: \textit{Nature}, 598, 434–438, (2021)

# LaTeX href with DOI link
./bib_extractor.py --inline --latex-href --print-only 10.1038/s41586-021-03926-0
# Output: \href{https://doi.org/10.1038/s41586-021-03926-0}{\textit{Nature}, 598, 434–438, (2021)}

# Author-style citation
./bib_extractor.py --inline --inline-style author --print-only 10.1038/s41586-021-03926-0
# Output: Zhou et al. (2021) \textit{Nature} 598 434–438
```

### Citation Styles

| Style | Format | Example |
|-------|--------|---------|
| `journal` (default) | *Journal*, Volume, Pages, (Year) | `\textit{Nature}, 598, 434–438, (2021)` |
| `author` | Author et al. (Year) *Journal* Volume Pages | `Zhou et al. (2021) \textit{Nature} 598 434–438` |
| `nature` | Author, F et al. *Journal* Volume, Pages (Year) | `Zhou, H et al. \textit{Nature} 598, 434–438 (2021)` |
| `apa` | Author, F. et al. (Year). Title. *Journal*, Volume(Issue). | Full APA format |

## Output Format

### Journal Article

```bibtex
@article{Zhou2021Superconductivity,
  author        = {Zhou, H. and others},
  title         = {Superconductivity in rhombohedral trilayer graphene},
  journal       = {Nature},
  volume        = {598},
  number        = {7881},
  pages         = {434--438},
  year          = {2021},
  citations     = {1744},
  impact_factor = {h-index: 1830 | i10: 119675 | papers: 447,855 | citations: 26,662,860},
  doi           = {10.1038/s41586-021-03926-0},
  url           = {https://doi.org/10.1038/s41586-021-03926-0},
  abstract      = {...}  # with --abstract flag
}
```

### Impact Factor Field

The `impact_factor` field contains journal-level metrics from OpenAlex:
- **h-index**: Journal's h-index (productivity and citation impact)
- **i10-index**: Number of papers cited 10+ times
- **papers**: Total number of papers published in the journal
- **citations**: Total citations received by the journal

### Preprint (arXiv)

```bibtex
@misc{210314030,
  author    = {Author, First and Author2, Second},
  title     = {Paper Title},
  year      = {2021},
  eprint    = {2103.14030},
  archive   = {arXiv},
  url       = {https://arxiv.org/abs/2103.14030}
}
```

## Integration with Claude Code

The `SKILL.md` file defines a Claude Code skill for bibliography extraction.

To use with Claude Code:
1. The skill is automatically detected when you're in this directory
2. Ask Claude to extract bibliography: "Add DOI 10.1038/s41586-021-03926-0 to my references.bib"
3. Claude will invoke the skill to handle the extraction

## Example Workflow

```bash
# 1. Extract papers from a list of DOIs
./bib_extractor.py --input my_dois.txt --output my_paper_refs.bib

# 2. Check the output
cat my_paper_refs.bib

# 3. Use in LaTeX document
# Add to your .tex file:
# \addbibresource{my_paper_refs.bib}

# 4. Compile
pdflatex document.tex
biber document
pdflatex document.tex
pdflatex document.tex
```

## Metadata Sources

| Source      | Identifiers      | Coverage                          |
|-------------|-----------------|-----------------------------------|
| CrossRef    | DOIs           | Most academic publishers            |
| PubMed      | PMIDs          | Biomedical literature               |
| arXiv       | arXiv IDs      | Physics, math, CS, q-bio preprints |
| Web scraping | Publisher URLs | Fallback for other sources         |

## Limitations

- Some publishers don't provide complete metadata via their APIs
- Old papers may have incomplete records
- Conference papers sometimes lack volume/pages information
- Rate limiting required for batch operations

## Troubleshooting

**DOI not found**: The DOI may be invalid or not yet indexed. Try searching for the paper title.

**Timeout error**: Increase timeout with `--timeout` option or check network connection.

**Missing fields**: Some entries may lack volume/pages. Consider adding manually or searching the publisher website.

**Duplicate keys**: The tool automatically handles duplicates by adding letter suffixes.

## License

MIT License
