#!/usr/bin/env python3
"""
Bibliography Preview Generator
Generates formatted LaTeX output from BibTeX with notes, abstracts, and AI reference suggestions.
"""

import sys
import os
import re
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    print("Error: requests module not found. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


def parse_bibtex_file(bib_file: str) -> List[Dict]:
    """Parse BibTeX file into list of entries."""
    entries = []

    try:
        with open(bib_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {bib_file}", file=sys.stderr)
        return entries

    # Pattern to match BibTeX entries
    entry_pattern = r'@(\w+)\s*\{\s*([^,]+),\s*(.*?)\n\s*\}'
    entries_data = re.findall(entry_pattern, content, re.DOTALL)

    for entry_type, entry_key, entry_content in entries_data:
        entry = {
            'type': entry_type,
            'key': entry_key.strip(),
            'type': entry_type,
            'fields': {}
        }

        # Extract fields
        field_pattern = r'(\w+)\s*=\s*\{(.*?)\},?'
        for field_name, field_value in re.findall(field_pattern, entry_content, re.DOTALL):
            entry['fields'][field_name] = field_value.strip()

        entries.append(entry)

    return entries


def generate_suggestions(citation_key: str, abstract: str, tex_file: Optional[str] = None,
                      model: str = "claude-sonnet-4-6") -> Optional[str]:
    """Generate AI reference suggestions for this citation."""
    if not tex_file or not Path(tex_file).exists():
        return None

    # Read TeX file to understand context
    try:
        with open(tex_file, 'r', encoding='utf-8') as f:
            tex_content = f.read()
    except Exception:
        return None

    # Check if citation key is already used
    if f'\\cite{{{citation_key}}}' in tex_content or f'\\citep{{{citation_key}}}' in tex_content:
        return None

    # Build prompt for AI
    prompt = f"""Given the following reference, suggest 1-2 sentences that could cite this paper in a LaTeX document.

Reference Key: {citation_key}
Abstract: {abstract}

Format your response as a Python list of strings, e.g.:
["Recent work by Author et al. demonstrated...", "Building on these findings..."]

Only suggest if the content seems relevant to general academic writing. Keep sentences concise and neutral."""

    # Call AI API (placeholder - integrate with your LLM of choice)
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": model,
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            content = result.get('content', [{}])[0].get('text', '')
            # Try to parse as Python list
            try:
                suggestions = eval(content)
                if isinstance(suggestions, list):
                    return '\\n'.join(suggestions)
            except:
                return content

    except Exception as e:
        pass

    return None


def format_latex_entry(entry: Dict, index: int, suggestions: Optional[str] = None) -> str:
    """Format a single BibTeX entry as LaTeX itemize."""
    fields = entry['fields']
    key = entry['key']
    entry_type = entry['type']
    title = fields.get('title', '')

    # Build citation line with title as section
    citation = f"\\item[\\textbf{{{index}}}] \\textbf{{{key}}}"

    # Format basic info (author, year)
    author = fields.get('author', 'Unknown')
    year = fields.get('year', '')

    info_parts = []
    if author and author != 'Unknown':
        info_parts.append(f"{author}")
    if year:
        info_parts.append(f"({year})")

    info_line = ' '.join(info_parts)

    # Add journal/venue
    if 'journal' in fields:
        info_line += f" \\textit{{{fields['journal']}}}"
    if 'booktitle' in fields:
        info_line += f" \\textit{{{fields['booktitle']}}}"

    # Add volume/pages
    if 'volume' in fields:
        info_line += f", {fields['volume']}"
    if 'pages' in fields:
        pages = fields['pages']
        # Ensure en-dash, but don't double existing en-dashes
        if '--' not in pages:
            pages = pages.replace('-', '--')
        info_line += f", {pages}"

    entry_lines = [citation, info_line]

    # Add title as a section header
    if title:
        entry_lines.insert(1, f"\\vspace{{0.3em}}")
        entry_lines.insert(2, f"\\textbf{{{title}}}")

    # Add DOI with hyperlink
    if 'doi' in fields:
        doi = fields['doi']
        entry_lines.append(f"\\vspace{{0.3em}}")
        entry_lines.append(f"DOI: \\href{{https://doi.org/{doi}}}{{{doi}}}")

    # Add citation count
    if 'citations' in fields:
        citations = fields['citations']
        entry_lines.append(f"\\vspace{{0.3em}}")
        entry_lines.append(f"\\textbf{{Citations:}} {citations}")

    # Add URL with hyperlink
    if 'url' in fields and 'doi' not in fields:
        url = fields['url']
        entry_lines.append(f"\\vspace{{0.3em}}")
        entry_lines.append(f"URL: \\href{{{url}}}{{{url}}}")

    # Add note
    if 'note' in fields:
        note = fields['note']
        entry_lines.append(f"\\vspace{{0.3em}}")
        entry_lines.append(f"\\textit{{Note:}} {note}")

    # Add abstract
    if 'abstract' in fields:
        abstract = fields['abstract']
        entry_lines.append(f"\\vspace{{0.3em}}")
        entry_lines.append(f"\\textbf{{Abstract:}} \\\\")
        entry_lines.append(f"\\footnotesize{{{abstract}}}")

    # Add AI suggestions
    if suggestions:
        entry_lines.append(f"\\vspace{{0.3em}}")
        entry_lines.append(f"\\textbf{{Suggested Citations:}} \\\\")
        entry_lines.append(f"\\footnotesize{{{suggestions}}}")

    # Combine with proper LaTeX formatting
    result = '\n'.join(entry_lines)
    result += '\n\n'  # Extra spacing between items

    return result


def generate_latex_output(entries: List[Dict], tex_file: Optional[str] = None,
                         bibliography_only: bool = False,
                         template_file: Optional[str] = None) -> str:
    """Generate complete LaTeX output."""

    # Generate entries content
    entries_content = ""
    for i, entry in enumerate(entries, 1):
        suggestions = None
        if tex_file:
            abstract = entry['fields'].get('abstract', '')
            suggestions = generate_suggestions(entry['key'], abstract, tex_file)

        entries_content += format_latex_entry(entry, i, suggestions)

    # Apply template or use default
    if template_file and Path(template_file).exists():
        with open(template_file, 'r', encoding='utf-8') as f:
            template = f.read()
        output = template.replace('%ENTRIES%', entries_content)
    elif bibliography_only:
        output = entries_content
    else:
        # Default LaTeX document
        output = f"""\\documentclass[12pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{hyperref}}
\\hypersetup{{
    colorlinks=true,
    linkcolor=blue,
    urlcolor=blue,
    citecolor=blue
}}
\\usepackage[style=authoryear,backend=biber]{{biblatex}}

\\begin{{document}}

\\section*{{Bibliography Preview}}

\\begin{{itemize}}
{entries_content}\\end{{itemize}}

\\end{{document}}
"""

    return output


def main():
    parser = argparse.ArgumentParser(
        description='Generate LaTeX preview from BibTeX with notes, abstracts, and AI suggestions.',
        epilog='Examples:\n'
                '  %(prog)s references.bib\n'
                '  %(prog)s references.bib --output preview.tex\n'
                '  %(prog)s references.bib --tex document.tex\n'
                '  %(prog)s references.bib --bibliography-only'
    )
    parser.formatter_class = argparse.RawDescriptionHelpFormatter

    parser.add_argument(
        'bib_file',
        help='BibTeX file to process'
    )

    parser.add_argument(
        '-o', '--output',
        default='preview.tex',
        help='Output LaTeX file (default: preview.tex)'
    )

    parser.add_argument(
        '--bibliography-only',
        action='store_true',
        help='Generate bibliography section only (for inclusion in other documents)'
    )

    parser.add_argument(
        '--template', '-t',
        help='Custom LaTeX template file with %%ENTRIES%% marker'
    )

    parser.add_argument(
        '--tex',
        help='TeX file to check for existing citations (for AI suggestions)'
    )

    parser.add_argument(
        '--no-suggestions',
        action='store_true',
        help='Disable AI-generated citation suggestions'
    )

    args = parser.parse_args()

    # Parse BibTeX file
    entries = parse_bibtex_file(args.bib_file)

    if not entries:
        print(f"Error: No entries found in {args.bib_file}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(entries)} entries", file=sys.stderr)

    # Determine tex file for suggestions
    tex_file = None
    if not args.no_suggestions and args.tex:
        tex_file = args.tex
    elif not args.no_suggestions:
        # Try to find .tex files in current directory
        for pattern in ['main.tex', 'document.tex', 'paper.tex']:
            if Path(pattern).exists():
                tex_file = pattern
                print(f"Using {tex_file} for citation context", file=sys.stderr)
                break

    # Generate LaTeX output
    output = generate_latex_output(
        entries,
        tex_file=tex_file,
        bibliography_only=args.bibliography_only,
        template_file=args.template
    )

    # Write output
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f"Output written to {args.output}", file=sys.stderr)


if __name__ == '__main__':
    main()
