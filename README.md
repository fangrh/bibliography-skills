# Bibliography Skills for Claude Code

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

A Zotero-like bibliography extraction and management suite for Claude Code. Extract bibliography entries from DOIs, URLs, PMIDs, and arXiv IDs, generate LaTeX previews, and search for academic papers.

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
| `/bib-extractor` | Extract BibTeX from DOIs, URLs, PMIDs, arXiv IDs |
| `/bib-preview` | Generate LaTeX preview from BibTeX files |
| `/bib-search` | Search and extract bibliography from web |

### Quick Examples

```bash
# Extract a paper by DOI
/bib-extractor 10.1038/s41586-021-03926-0

# Extract from URL
/bib-extractor https://doi.org/10.1126/science.abf5641

# Batch extract from file
/bib-extractor --input dois.txt --output references.bib

# Generate LaTeX preview
/bib-preview references.bib -o preview.tex

# Search for papers
/bib-search "quantum computing" --limit 5
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
  -h, --help           show help message and exit
  -i, --input INPUT    Input file with identifiers (one per line)
  -o, --output OUTPUT  Output BibTeX file (default: references.bib)
  --delay DELAY        Delay between requests in seconds (default: 1.0)
  --timeout TIMEOUT     Request timeout in seconds (default: 15)
  --print-only         Print BibTeX to stdout without appending to file
```

## Citation Key Format

Citation keys are generated as: `{FirstAuthor}{Year}{Keyword}`

Examples:
- `Zhou2021Superconductivity`
- `Walsh2021Josephson`
- `DiBattista2024Infrared`

Duplicate keys get letter suffixes: `Smith2024Quantuma`, `Smith2024Quantumb`, etc.

## Output Format

### Journal Article

```bibtex
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
