# /bib-preview - Generate LaTeX Preview from BibTeX

Convert BibTeX file to formatted LaTeX preview with full support for note, abstract, and refkey fields.

## Usage

```
/bib-preview [bib_file] [options]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|-----------|
| `bib_file` | BibTeX file to convert | Yes |
| `--output, -o` | Output LaTeX file (default: preview.tex) | Optional |
| `--bibliography-only` | Generate bibliography section only (for inclusion in other docs) | Optional |
| `--template, -t` | Custom LaTeX template file with `%ENTRIES%` marker | Optional |

## Examples

```
# Generate LaTeX preview
/bib-preview references.bib

# Specify output file
/bib-preview references.bib -o preview.tex

# Generate bibliography section only
/bib-preview references.bib --bibliography-only -o bibliography.tex

# Use custom template
/bib-preview references.bib --template mytemplate.tex -o output.tex
```

## Output Format

### Full Preview Mode (default)

Generates a complete LaTeX document with:
- `\documentclass[12pt]{article}`
- `biblatex` package with authoryear style
- Formatted entries with bold authors, italic journals
- Note field displayed as "Note: {content}"
- Abstract field displayed as "Abstract: {content}" in small font
- DOI/URL as clickable links
- Citations ready for compilation

### Bibliography-Only Mode

Generates just the bibliography entries formatted for inclusion in other documents.

## Custom Templates

Create a template with `%ENTRIES%` marker:

```latex
\documentclass[12pt]{article}
\usepackage[style=authoryear,backend=biber]{biblatex}
\usepackage[margin=1in]{geometry}
\usepackage[utf8]{inputenc}

\begin{document}

\section*{Bibliography}

%ENTRIES%
[ Entries will be inserted here ]

\printbibliography[heading=none]

\end{document}
```

## Compilation

After generating the LaTeX file, compile with:

```bash
pdflatex preview.tex && biber preview.tex && pdflatex preview.tex
```

## Process

1. Parse BibTeX file for all entries
2. Extract all fields including note and abstract
3. Format with proper LaTeX styling
4. Insert into template (or use built-in format)
5. Generate compilation-ready `.tex` file

## Notes

- Supports UTF-8 encoding for international characters
- Removes underscores from citation keys for display
- Properly formats page ranges with en-dashes
- Handles multiple entry types (article, misc, book, etc.)
