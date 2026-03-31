#!/usr/bin/env python3
"""
Bibliography Extractor - Papis CLI wrapper for extracting BibTeX entries
Supports DOIs, URLs, PMIDs, and arXiv IDs via papis CLI
"""

import sys
import re
import argparse
from typing import Optional, List
from pathlib import Path
import subprocess

# Optional papis import - only required at runtime, not for import
# This allows testing and module import without papis installed
try:
    import papis
    import papis.api
    PAPIS_AVAILABLE = True
except ImportError:
    PAPIS_AVAILABLE = False


def normalize_to_doi(identifier: str) -> str:
    """Normalize various identifier formats to DOI.

    Args:
        identifier: DOI, URL, PMID, or arXiv ID

    Returns:
        Normalized DOI or identifier in a format suitable for papis
    """
    identifier = identifier.strip()

    # If already a DOI (starts with 10.)
    if identifier.startswith('10.'):
        return identifier

    # Remove common DOI prefixes
    prefixes = [
        'https://doi.org/',
        'http://doi.org/',
        'doi:',
        'doi: ',
    ]
    for prefix in prefixes:
        if identifier.lower().startswith(prefix.lower()):
            identifier = identifier[len(prefix):]
            break

    # If remaining starts with 10., it's a DOI
    if identifier.startswith('10.'):
        identifier = identifier.rstrip('/')
        return identifier

    # For URLs, extract DOI if present
    doi_match = re.search(r'10\.\d{4,9}/[^\s\?"<>#]+', identifier)
    if doi_match:
        return doi_match.group(0)

    # For arXiv IDs
    arxiv_match = re.match(r'^(\d{4}\.\d{4,5})', identifier)
    if arxiv_match:
        return arxiv_match.group(1)

    # For arXiv URLs
    arxiv_url_match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d+\.\d+)', identifier)
    if arxiv_url_match:
        return arxiv_url_match.group(1)

    # For PMID (numeric only)
    if identifier.isdigit():
        # papis can handle PMID directly
        return identifier

    # Return as-is for papis to handle
    return identifier


def add_reference(identifier: str, no_pdf: bool = False, no_note: bool = False, timeout: int = 15) -> str:
    """Add reference using papis CLI.

    Args:
        identifier: DOI, URL, PMID, or arXiv ID
        no_pdf: Skip PDF download
        no_note: Skip subagent note parsing (legacy flag, for compatibility)
        timeout: Request timeout in seconds (not used in papis mode)

    Returns:
        BibTeX entry as string

    Raises:
        subprocess.CalledProcessError: If papis command fails
        RuntimeError: If papis is not available (only during actual execution)
    """
    if not PAPIS_AVAILABLE:
        raise RuntimeError("papis module not found. Install with: pip install papis")
    # Normalize identifier to DOI format if needed
    doi = normalize_to_doi(identifier)

    # Build papis command
    # Use -l . to set library to current directory
    cmd = ['papis', '-l', '.', 'add', '--from', 'doi', doi]

    # Add tags and set empty note
    cmd.extend(['--set', 'tags=extracted'])
    if not no_note:
        cmd.extend(['--set', 'note=""'])

    if no_pdf:
        cmd.append('--no-document')

    # Run papis add command
    subprocess.run(cmd, check=True, capture_output=True)

    # Export to papis.bib
    export_bibtex('papis.bib')

    # Read and return the BibTeX entry
    try:
        bib_content = Path('papis.bib').read_text(encoding='utf-8')
        # Return the last entry (the one we just added)
        entries = split_bib_entries(bib_content)
        if entries:
            return entries[-1]
    except Exception as e:
        print(f'  Warning: Could not read papis.bib: {e}', file=sys.stderr)

    return ''


def split_bib_entries(content: str) -> List[str]:
    """Split BibTeX file content into individual entries.

    Args:
        content: BibTeX file content

    Returns:
        List of BibTeX entries
    """
    return re.findall(r'(@\w+\s*\{[^}]+,.*?(?=@\w+\s*\{|$))', content, re.DOTALL)


def export_bibtex(output_file: str = 'papis.bib') -> None:
    """Export all references from papis library to BibTeX file.

    Args:
        output_file: Output BibTeX file path

    Raises:
        subprocess.CalledProcessError: If papis export fails
        RuntimeError: If papis is not available (only during actual execution)
    """
    if not PAPIS_AVAILABLE:
        raise RuntimeError("papis module not found. Install with: pip install papis")
    # Use shell=True for the redirect
    export_cmd = 'papis -l . export --format bibtex > ' + output_file
    subprocess.run(export_cmd, shell=True, check=True, capture_output=True)


def ensure_pdf_gitignored() -> None:
    """Ensure *.pdf pattern is in .gitignore.

    Creates .gitignore if it doesn't exist.
    Appends *.pdf if not already present.
    """
    gitignore_path = Path('.gitignore')
    pattern = '*.pdf'

    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if pattern not in content:
            with open(gitignore_path, 'a') as f:
                f.write(f'\n{pattern}\n')
    else:
        with open(gitignore_path, 'w') as f:
            f.write(f'{pattern}\n')


def extract_bibtex(
    identifier: str,
    fetch_abstract: bool = False,
    bib_file: Optional[str] = None,
    no_pdf: bool = False,
    no_note: bool = False,
    timeout: int = 15,
) -> Optional[str]:
    """Extract BibTeX entry for a given identifier.

    Args:
        identifier: DOI, URL, PMID, or arXiv ID
        fetch_abstract: Fetch abstract (not used in papis mode, for compatibility)
        bib_file: Check for existing entries in this file (not used in papis mode)
        no_pdf: Skip PDF download
        no_note: Skip subagent note parsing
        timeout: Request timeout (not used in papis mode)

    Returns:
        BibTeX entry as string, or None if extraction fails
    """
    try:
        ensure_pdf_gitignored()
        bibtex = add_reference(identifier, no_pdf=no_pdf, no_note=no_note, timeout=timeout)
        return bibtex if bibtex else None
    except subprocess.CalledProcessError as e:
        print(f'  Error: Failed to extract {identifier}: {e}', file=sys.stderr)
        if e.stderr:
            print(f'  Stderr: {e.stderr.decode()}', file=sys.stderr)
        return None
    except Exception as e:
        print(f'  Error: Unexpected error extracting {identifier}: {e}', file=sys.stderr)
        return None


def process_batch(
    identifiers: List[str],
    output_file: str = 'papis.bib',
    delay: float = 1.0,
    fetch_abstract: bool = False,
    no_pdf: bool = False,
    no_note: bool = False,
    timeout: int = 15,
    parallel: int = 1,
) -> None:
    """Process multiple identifiers and append to output file.

    Args:
        identifiers: List of DOIs, URLs, PMIDs, or arXiv IDs
        output_file: Output BibTeX file
        delay: Delay between requests
        fetch_abstract: Fetch abstract (not used in papis mode)
        no_pdf: Skip PDF download
        no_note: Skip subagent note parsing
        timeout: Request timeout (not used in papis mode)
        parallel: Number of parallel workers (not used in papis mode)
    """
    import time

    ensure_pdf_gitignored()

    for i, identifier in enumerate(identifiers, 1):
        print(f'[{i}/{len(identifiers)}] {identifier}', file=sys.stderr)
        result = extract_bibtex(
            identifier,
            fetch_abstract=fetch_abstract,
            bib_file=output_file,
            no_pdf=no_pdf,
            no_note=no_note,
            timeout=timeout,
        )
        if result:
            print(f'  Success: {identifier}', file=sys.stderr)
        else:
            print(f'  Failed: {identifier}', file=sys.stderr)

        if i < len(identifiers):
            time.sleep(delay)

    # Final export to ensure all entries are in output file
    export_bibtex(output_file)


def main():
    parser = argparse.ArgumentParser(
        description='Extract bibliography from DOIs, URLs, PMIDs, and arXiv IDs using papis.',
        epilog='Examples:\n'
                '  %(prog)s 10.1038/s41586-021-03926-0\n'
                '  %(prog)s https://doi.org/10.1126/science.abf5641\n'
                '  %(prog)s --input dois.txt --output papis.bib'
    )
    parser.formatter_class = argparse.RawDescriptionHelpFormatter

    parser.add_argument(
        'identifiers',
        nargs='*',
        help='DOI(s), URL(s), PMID(s), or arXiv ID(s) to extract'
    )

    parser.add_argument(
        '-i', '--input',
        help='Input file with identifiers (one per line)'
    )

    parser.add_argument(
        '-o', '--output',
        default='papis.bib',
        help='Output BibTeX file (default: papis.bib)'
    )

    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between requests in seconds (default: 1.0)'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=15,
        help='Request timeout in seconds (default: 15)'
    )

    parser.add_argument(
        '--print-only',
        action='store_true',
        help='Print BibTeX to stdout without appending to file'
    )

    parser.add_argument(
        '--no-pdf',
        action='store_true',
        help='Skip PDF download'
    )

    parser.add_argument(
        '--no-note',
        action='store_true',
        help='Skip subagent note parsing'
    )

    parser.add_argument(
        '--clean-invalid',
        action='store_true',
        help='Remove entries with invalid DOIs from the BibTeX file (not implemented in papis mode)'
    )

    parser.add_argument(
        '--full-journal-name',
        action='store_true',
        help='Use full journal names instead of abbreviations (not implemented in papis mode)'
    )

    parser.add_argument(
        '--abstract',
        action='store_true',
        help='Fetch and include abstract in BibTeX entry (not implemented in papis mode)'
    )

    parser.add_argument(
        '--inline',
        action='store_true',
        help='Output inline citation format instead of BibTeX (not implemented in papis mode)'
    )

    parser.add_argument(
        '--inline-style',
        choices=['journal', 'author', 'nature', 'apa'],
        default='journal',
        help='Citation style for inline output: journal (default), author, nature, apa'
    )

    parser.add_argument(
        '--latex-href',
        action='store_true',
        help='Output LaTeX \\href command with DOI link for inline citations (not implemented in papis mode)'
    )

    parser.add_argument(
        '--parallel',
        type=int,
        default=1,
        help='Number of parallel workers for batch processing (default: 1, not implemented in papis mode)'
    )

    args = parser.parse_args()

    # Collect identifiers
    identifiers = []

    if args.identifiers:
        identifiers.extend(args.identifiers)

    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                file_ids = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                identifiers.extend(file_ids)
        except FileNotFoundError:
            print(f'Error: Input file not found: {args.input}', file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f'Error reading input file: {e}', file=sys.stderr)
            sys.exit(1)

    if not identifiers:
        parser.print_help()
        sys.exit(1)

    # Warn about unsupported options
    if args.clean_invalid:
        print('Warning: --clean-invalid is not implemented in papis mode', file=sys.stderr)
    if args.full_journal_name:
        print('Warning: --full-journal-name is not implemented in papis mode', file=sys.stderr)
    if args.abstract:
        print('Warning: --abstract is not implemented in papis mode', file=sys.stderr)
    if args.inline or args.latex_href:
        print('Warning: --inline and --latex-href are not implemented in papis mode', file=sys.stderr)
    if args.parallel > 1:
        print('Warning: --parallel is not implemented in papis mode', file=sys.stderr)

    # Process
    if args.print_only or args.inline:
        # Print to stdout only
        print(f'# Extracting {len(identifiers)} bibliography entry(ies)', file=sys.stderr)
        for i, identifier in enumerate(identifiers, 1):
            print(f'[{i}/{len(identifiers)}] {identifier}', file=sys.stderr)
            bibtex = extract_bibtex(
                identifier,
                fetch_abstract=args.abstract,
                bib_file=args.output,
                no_pdf=args.no_pdf,
                no_note=args.no_note,
                timeout=args.timeout,
            )
            if bibtex:
                print()
                print(bibtex)
            else:
                print(f'  Failed to extract: {identifier}', file=sys.stderr)
            if i < len(identifiers):
                import time
                time.sleep(args.delay)
    else:
        # Append to file
        process_batch(
            identifiers, args.output,
            delay=args.delay,
            fetch_abstract=args.abstract,
            no_pdf=args.no_pdf,
            no_note=args.no_note,
            timeout=args.timeout,
            parallel=args.parallel
        )


if __name__ == '__main__':
    main()
