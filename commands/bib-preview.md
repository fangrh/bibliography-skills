# /bib-preview - Generate LaTeX Preview from BibTeX

Generate formatted LaTeX preview from BibTeX with numbered references, hyperlinks, notes, abstracts, and AI-suggested citation sentences.

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
| `--template, -t` | Custom LaTeX template file with `%%ENTRIES%%` marker | Optional |
| `--tex` | TeX file to check for existing citations (for AI suggestions) | Optional |
| `--no-suggestions` | Disable AI-generated citation suggestions | Optional |

## Examples

```bash
# Generate LaTeX preview
/bib-preview references.bib

# Specify output file
/bib-preview references.bib -o preview.tex

# Generate bibliography section only
/bib-preview references.bib --bibliography-only -o bibliography.tex

# Use custom template
/bib-preview references.bib --template mytemplate.tex -o output.tex

# Check existing TeX file for AI suggestions
/bib-preview references.bib --tex document.tex

# Disable AI suggestions
/bib-preview references.bib --no-suggestions
```

## Output Format

Each entry includes:

1. **Numbered item** with bold citation key
2. **Author and year** with title in quotes
3. **Journal/venue** in italics
4. **DOI** as clickable hyperlink (`\href{https://doi.org/...}{DOI}`)
5. **URL** as clickable hyperlink (if no DOI)
6. **Note** field displayed as "Note: {content}"
7. **Abstract** field displayed as "Abstract: {content}" in footnotesize
8. **AI suggestions** for citing this reference (if TeX file provided and citation not used)

### Sample Output

```latex
\item[\textbf{1}] \textbf{Smith2024Quantum}
\vspace{0.3em}
\textbf{Quantum Coherence in Photonic Systems}
Smith, John and Doe, Jane (2024) \textit{Nature}, 598, 123--145
\vspace{0.3em}
DOI: \href{https://doi.org/10.1038/xxx}{10.1038/xxx}
\vspace{0.3em}
\textit{Note:} Important for understanding quantum optics
\vspace{0.3em}
\textbf{Abstract:} \\
\footnotesize{We demonstrate...}
```

**Format:**
- Citation key (numbered and bold)
- Title as bold section (with spacing)
- Author, year, journal, pages
- DOI/URL as clickable hyperlink
- Note and abstract fields

## Full Preview Mode (default)

Generates a complete LaTeX document with:
- `\documentclass[12pt]{article}`
- `hyperref` package for clickable links
- `geometry` package for margins
- Numbered itemize list
- Formatted entries with all fields

## Bibliography-Only Mode

Generates just the itemize entries formatted for inclusion in other documents.

## Custom Templates

Create a template with `%%ENTRIES%%` marker:

```latex
\documentclass[12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[margin=1in]{geometry}
\usepackage{hyperref}

\begin{document}

\section*{Bibliography}

\begin{itemize}
%%ENTRIES%%
\end{itemize}

\end{document}
```

## Compilation

After generating LaTeX file, compile with:

```bash
pdflatex preview.tex
```

Note: This script generates plain LaTeX without BibTeX/biblatex dependency for the preview.

## Process

1. Parse BibTeX file for all entries
2. Extract all fields including note and abstract
3. Format with proper LaTeX styling (itemize, itemize)
4. Add hyperlinks for DOI/URL
5. Check TeX file for existing citations
6. Call AI to generate suggested citation sentences (if needed)
7. Generate compilation-ready `.tex` file

## AI Citation Suggestions

When a TeX file is provided (`--tex`), the script:
1. Checks if citation key is already used in the TeX file
2. If NOT used, calls AI to suggest 1-2 sentences
3. Includes suggestions in the output

Requires `ANTHROPIC_API_KEY` environment variable for AI suggestions.

## Notes

- Supports UTF-8 encoding for international characters
- Handles multiple entry types (article, misc, book, inproceedings)
- Page ranges formatted with en-dashes (`--`)
- Blank lines between entries for readability
- AI suggestions optional and require API key
