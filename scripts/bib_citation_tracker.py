#!/usr/bin/env python3
"""
Bibliography Citation Tracker - Track citation usage in documents

Scans LaTeX/Markdown files for citation patterns and updates BibTeX entries
with usage tracking in the annotation field.
"""

import sys
import re
import argparse
from typing import Optional, Dict, List, Tuple, Set
from pathlib import Path


class BibCitationTracker:
    """Track citation usage in documents and update BibTeX annotations."""

    # Citation patterns for LaTeX
    LATEX_CITATION_PATTERNS = [
        # \cite{key}, \citep{key}, \citet{key}, \citealp{key}, etc.
        r'\\cite[a-z]*\*?\s*\{([^}]+)\}',
        # \bibentry{key}
        r'\\bibentry\{([^}]+)\}',
        # \fullcite{key}
        r'\\fullcite\{([^}]+)\}',
        # \parencite{key}, \textcite{key}
        r'\\(?:paren|text)cite\{([^}]+)\}',
        # \autocite{key}
        r'\\autocite\{([^}]+)\}',
    ]

    # Citation patterns for Markdown
    MARKDOWN_CITATION_PATTERNS = [
        # [@key] or [@key, p. 123]
        r'\[@([^\],]+)',
        # [Author Year] - less precise, needs special handling
        # @key at word boundary
        r'(?<!\w)@([a-zA-Z][a-zA-Z0-9_:]+)(?!\w)',
    ]

    def __init__(self, verbose: bool = False):
        """Initialize the citation tracker.

        Args:
            verbose: Show detailed progress
        """
        self.verbose = verbose

    def parse_bib_file(self, bib_file: str) -> Tuple[List[Dict], str]:
        """Parse BibTeX file into entries and preserve header/comments.

        Returns:
            Tuple of (entries list, header content)
        """
        try:
            with open(bib_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f'Error: File not found: {bib_file}', file=sys.stderr)
            return [], ''

        # Extract header (comments, string macros before first entry)
        header_match = re.match(r'^((?:(?<!@).*?)*?)(?=@\w+\{)', content, re.DOTALL)
        header = header_match.group(1) if header_match else ''

        # Parse entries
        entry_pattern = r'(@(\w+)\s*\{([^,]+),\s*(.*?)(?=@\w+\s*\{|$))'
        entries = []

        for match in re.finditer(entry_pattern, content, re.DOTALL):
            full_entry = match.group(1)
            entry_type = match.group(2)
            cite_key = match.group(3)
            fields_str = match.group(4)

            # Parse fields
            fields = self._parse_fields(fields_str)

            entries.append({
                'type': entry_type,
                'key': cite_key,
                'fields': fields,
                'raw': full_entry
            })

        return entries, header

    def _parse_fields(self, fields_str: str) -> Dict[str, str]:
        """Parse BibTeX fields from string."""
        fields = {}

        # Handle both {value} and "value" formats
        field_pattern = r'(\w+)\s*=\s*(?:\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}|"([^"]*)")'

        for match in re.finditer(field_pattern, fields_str):
            field_name = match.group(1).lower()
            # Get value from either {} or "" group
            field_value = match.group(2) if match.group(2) is not None else match.group(3)
            fields[field_name] = field_value.strip()

        return fields

    def extract_citations_from_latex(self, content: str) -> Dict[str, List[str]]:
        """Extract citations from LaTeX content.

        Returns:
            Dict mapping citation keys to list of contexts (sentences)
        """
        citations = {}

        for pattern in self.LATEX_CITATION_PATTERNS:
            for match in re.finditer(pattern, content):
                keys_str = match.group(1)
                # Split multiple keys (e.g., \cite{key1, key2})
                keys = [k.strip() for k in keys_str.split(',')]

                for key in keys:
                    if key:
                        # Extract surrounding context
                        context = self._extract_context(content, match.start(), match.end())
                        if key not in citations:
                            citations[key] = []
                        if context and context not in citations[key]:
                            citations[key].append(context)

        return citations

    def extract_citations_from_markdown(self, content: str) -> Dict[str, List[str]]:
        """Extract citations from Markdown content.

        Returns:
            Dict mapping citation keys to list of contexts (sentences)
        """
        citations = {}

        for pattern in self.MARKDOWN_CITATION_PATTERNS:
            for match in re.finditer(pattern, content):
                key = match.group(1).strip()
                if key and not key.startswith('http'):  # Skip email-like patterns
                    # Extract surrounding context
                    context = self._extract_context(content, match.start(), match.end())
                    if key not in citations:
                        citations[key] = []
                    if context and context not in citations[key]:
                        citations[key].append(context)

        return citations

    def _extract_context(self, content: str, start: int, end: int,
                         context_chars: int = 150) -> str:
        """Extract context around a citation.

        Args:
            content: Full document content
            start: Start position of citation
            end: End position of citation
            context_chars: Number of characters to extract on each side

        Returns:
            Context string with citation highlighted
        """
        # Find sentence boundaries
        # Look backwards for sentence start
        sentence_start = max(0, start - context_chars)

        # Try to find actual sentence boundary
        for i in range(start - 1, max(0, start - context_chars), -1):
            if content[i] in '.!?':
                sentence_start = i + 1
                break

        # Look forward for sentence end
        sentence_end = min(len(content), end + context_chars)
        for i in range(end, min(len(content), end + context_chars)):
            if content[i] in '.!?':
                sentence_end = i + 1
                break

        context = content[sentence_start:sentence_end].strip()

        # Clean up whitespace
        context = re.sub(r'\s+', ' ', context)

        return context

    def scan_documents(self, documents: List[str]) -> Dict[str, List[Tuple[str, str]]]:
        """Scan multiple documents for citations.

        Args:
            documents: List of document file paths

        Returns:
            Dict mapping citation keys to list of (filename, context) tuples
        """
        all_citations = {}

        for doc_path in documents:
            try:
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f'Warning: Could not read {doc_path}: {e}', file=sys.stderr)
                continue

            filename = Path(doc_path).name

            # Detect file type and extract citations
            if doc_path.endswith('.tex'):
                citations = self.extract_citations_from_latex(content)
            elif doc_path.endswith('.md'):
                citations = self.extract_citations_from_markdown(content)
            else:
                # Try both
                citations = self.extract_citations_from_latex(content)
                citations.update(self.extract_citations_from_markdown(content))

            # Merge with all_citations
            for key, contexts in citations.items():
                if key not in all_citations:
                    all_citations[key] = []
                for context in contexts:
                    all_citations[key].append((filename, context))

            if self.verbose:
                print(f'  {filename}: Found {len(citations)} unique citations', file=sys.stderr)

        return all_citations

    def format_annotation(self, citations: List[Tuple[str, str]]) -> str:
        """Format citation contexts for BibTeX annotation field.

        Args:
            citations: List of (filename, context) tuples

        Returns:
            Formatted annotation string
        """
        lines = []

        # Group by filename
        by_file = {}
        for filename, context in citations:
            if filename not in by_file:
                by_file[filename] = []
            by_file[filename].append(context)

        for filename, contexts in by_file.items():
            for i, context in enumerate(contexts, 1):
                # Truncate long contexts
                if len(context) > 200:
                    context = context[:197] + '...'
                lines.append(f'{filename} ({i}): "{context}"')

        return ' | '.join(lines)

    def update_bibtex_with_annotations(self, bib_file: str, citations: Dict[str, List[Tuple[str, str]]],
                                       output_file: Optional[str] = None) -> Dict:
        """Update BibTeX file with citation annotations.

        Args:
            bib_file: Path to BibTeX file
            citations: Dict of citation keys to contexts
            output_file: Output file (default: overwrite input)

        Returns:
            Statistics dict
        """
        if output_file is None:
            output_file = bib_file

        entries, header = self.parse_bib_file(bib_file)

        stats = {
            'total_entries': len(entries),
            'cited_entries': 0,
            'uncited_entries': 0,
            'updated_annotations': 0,
            'citations_found': sum(len(v) for v in citations.values())
        }

        # Build citation key set
        cited_keys = set(citations.keys())

        print(f'\nProcessing {len(entries)} entries...', file=sys.stderr)

        updated_entries = []

        for entry in entries:
            key = entry.get('key', '')
            fields = entry.get('fields', {}).copy()

            if key in cited_keys:
                stats['cited_entries'] += 1

                # Format and add annotation
                annotation = self.format_annotation(citations[key])
                fields['annotation'] = annotation

                if self.verbose:
                    print(f'  {key}: Found {len(citations[key])} citations', file=sys.stderr)

                stats['updated_annotations'] += 1
            else:
                stats['uncited_entries'] += 1

            updated_entries.append({
                'type': entry['type'],
                'key': key,
                'fields': fields
            })

        # Write output
        with open(output_file, 'w', encoding='utf-8') as f:
            if header:
                f.write(header)

            for entry in updated_entries:
                f.write('\n\n')
                f.write(self._entry_to_bibtex(entry))

            f.write('\n')

        print(f'Updated: {output_file}', file=sys.stderr)

        return stats

    def _entry_to_bibtex(self, entry: Dict) -> str:
        """Convert entry dict to BibTeX string."""
        entry_type = entry.get('type', 'article')
        key = entry.get('key', 'unknown')
        fields = entry.get('fields', {})

        # Field order for consistent output
        field_order = [
            'author', 'title', 'journal', 'booktitle', 'volume', 'number', 'pages',
            'year', 'month', 'citations', 'doi', 'url', 'issn', 'isbn', 'publisher',
            'eprint', 'archive', 'pmid', 'abstract', 'note', 'annotation'
        ]

        bibtex = f"@{entry_type}{{{key},\n"

        # Add ordered fields
        for field in field_order:
            if field in fields:
                value = fields[field]
                bibtex += f"  {field:<10} = {{{value}}},\n"

        # Add remaining fields
        for field, value in fields.items():
            if field not in field_order:
                bibtex += f"  {field:<10} = {{{value}}},\n"

        # Remove trailing comma
        bibtex = bibtex.rstrip(',\n')
        bibtex += "\n}"

        return bibtex

    def find_uncited_entries(self, bib_file: str, documents: List[str]) -> List[str]:
        """Find entries that are never cited in the documents.

        Args:
            bib_file: Path to BibTeX file
            documents: List of document paths

        Returns:
            List of uncited entry keys
        """
        entries, _ = self.parse_bib_file(bib_file)
        citations = self.scan_documents(documents)

        cited_keys = set(citations.keys())
        uncited = []

        for entry in entries:
            key = entry.get('key', '')
            if key and key not in cited_keys:
                uncited.append(key)

        return uncited

    def print_report(self, stats: Dict, uncited: Optional[List[str]] = None):
        """Print tracking report."""
        print('\n' + '=' * 50, file=sys.stderr)
        print('Citation Tracking Report', file=sys.stderr)
        print('=' * 50, file=sys.stderr)
        print(f'Total entries: {stats["total_entries"]}', file=sys.stderr)
        print(f'Cited entries: {stats["cited_entries"]}', file=sys.stderr)
        print(f'Uncited entries: {stats["uncited_entries"]}', file=sys.stderr)
        print(f'Total citations found: {stats["citations_found"]}', file=sys.stderr)
        print(f'Annotations updated: {stats["updated_annotations"]}', file=sys.stderr)

        if uncited:
            print(f'\nUncited entry keys ({len(uncited)}):', file=sys.stderr)
            for key in uncited[:20]:  # Show first 20
                print(f'  - {key}', file=sys.stderr)
            if len(uncited) > 20:
                print(f'  ... and {len(uncited) - 20} more', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='Track citation usage in documents and update BibTeX annotations.',
        epilog='Examples:\n'
                '  %(prog)s references.bib --documents paper.tex\n'
                '  %(prog)s references.bib --documents "*.tex"\n'
                '  %(prog)s references.bib --documents . --dry-run'
    )
    parser.formatter_class = argparse.RawDescriptionHelpFormatter

    parser.add_argument(
        'bib_file',
        nargs='?',
        default='references.bib',
        help='BibTeX file to process (default: references.bib)'
    )

    parser.add_argument(
        '-d', '--documents',
        nargs='+',
        required=True,
        help='Document files to scan for citations (.tex, .md, or directory)'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output BibTeX file (default: overwrite input)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without modifying files'
    )

    parser.add_argument(
        '--find-uncited',
        action='store_true',
        help='Only list entries that are never cited'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed progress'
    )

    args = parser.parse_args()

    # Create tracker
    tracker = BibCitationTracker(verbose=args.verbose)

    # Expand document paths
    documents = []
    for doc in args.documents:
        path = Path(doc)
        if path.is_dir():
            # Find all .tex and .md files in directory
            documents.extend(str(p) for p in path.glob('**/*.tex'))
            documents.extend(str(p) for p in path.glob('**/*.md'))
        elif path.exists():
            documents.append(doc)
        else:
            # Try glob pattern
            import glob
            matches = glob.glob(doc)
            if matches:
                documents.extend(matches)
            else:
                print(f'Warning: No files found for: {doc}', file=sys.stderr)

    if not documents:
        print('Error: No document files found', file=sys.stderr)
        sys.exit(1)

    print(f'\nScanning {len(documents)} document(s)...', file=sys.stderr)

    # Scan documents
    citations = tracker.scan_documents(documents)

    print(f'Found {len(citations)} unique citation keys', file=sys.stderr)

    # Find uncited entries
    uncited = tracker.find_uncited_entries(args.bib_file, documents)

    if args.find_uncited:
        # Only show uncited entries
        print(f'\nUncited entries ({len(uncited)}):', file=sys.stderr)
        for key in uncited:
            print(f'  {key}', file=sys.stderr)
        return

    if args.dry_run:
        # Show what would be done
        entries, _ = tracker.parse_bib_file(args.bib_file)

        cited_count = 0
        for entry in entries:
            key = entry.get('key', '')
            if key in citations:
                cited_count += 1
                print(f'\n{key}:', file=sys.stderr)
                for filename, context in citations[key][:3]:
                    print(f'  {filename}: "{context[:80]}..."', file=sys.stderr)

        stats = {
            'total_entries': len(entries),
            'cited_entries': cited_count,
            'uncited_entries': len(entries) - cited_count,
            'citations_found': sum(len(v) for v in citations.values()),
            'updated_annotations': 0
        }

        tracker.print_report(stats, uncited)
        print('\nDry run - no changes made', file=sys.stderr)
    else:
        # Update BibTeX file
        stats = tracker.update_bibtex_with_annotations(
            args.bib_file,
            citations,
            output_file=args.output
        )

        tracker.print_report(stats, uncited)


if __name__ == '__main__':
    main()
