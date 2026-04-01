#!/usr/bin/env python3
"""
Bibliography Extractor - Papis CLI wrapper for extracting BibTeX entries
Supports DOIs, URLs, PMIDs, and arXiv IDs via papis CLI
"""

import sys
import re
import json
import argparse
from typing import Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from pathlib import Path
import subprocess
import html as html_lib

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from title_normalizer import normalize_title_for_bibtex

# Optional papis import - only required at runtime, not for import
# This allows testing and module import without papis installed
try:
    import papis
    import papis.api
    PAPIS_AVAILABLE = True
except ImportError:
    PAPIS_AVAILABLE = False

try:
    import requests
except ImportError:
    requests = None


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


class BibExtractor:
    """Legacy-compatible extractor API used by bib_smart_search."""

    JOURNAL_ABBREVIATIONS = {
        'Nature Communications': 'Nat. Commun.',
        'Physical Review B': 'Phys. Rev. B',
        'Physical Review D': 'Phys. Rev. D',
        'Physical Review Letters': 'Phys. Rev. Lett.',
        'Nature': 'Nature',
        'Science': 'Science',
        'Nano Letters': 'Nano Lett.',
    }

    FIELD_PATTERN = re.compile(r'(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}', re.DOTALL)

    def __init__(self, timeout: int = 15, use_full_journal_name: bool = False):
        self.timeout = timeout
        self.use_full_journal_name = use_full_journal_name
        self.session = requests.Session() if requests is not None else None
        if self.session is not None:
            self.session.headers.update({
                'User-Agent': 'BibExtractor/1.0 (Citation Management Tool)',
            })

    def abbreviate_journal(self, journal_name: str) -> str:
        if self.use_full_journal_name or not journal_name:
            return journal_name
        return self.JOURNAL_ABBREVIATIONS.get(journal_name, journal_name)

    def extract_doi_from_url(self, url: str) -> Optional[str]:
        match = re.search(r'10\.\d{4,9}/[^\s\?"<>#]+', url)
        return self.clean_doi(match.group(0)) if match else None

    def extract_arxiv_id_from_url(self, url: str) -> Optional[str]:
        match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d+\.\d+)', url)
        return match.group(1) if match else None

    def extract_pmid_from_url(self, url: str) -> Optional[str]:
        match = re.search(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)', url)
        return match.group(1) if match else None

    def clean_doi(self, doi: str) -> str:
        return normalize_to_doi(doi).rstrip('/')

    def normalize_url(self, url: str) -> str:
        url = url.strip()
        if not url:
            return ''

        parsed = urlparse(url)
        query = urlencode([
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=False)
            if not key.lower().startswith(('utm_', 'fbclid', 'gclid'))
        ])
        path = parsed.path.rstrip('/')
        scheme = parsed.scheme.lower() or 'https'
        netloc = parsed.netloc.lower()
        return urlunparse((scheme, netloc, path, '', query, ''))

    def _split_bib_entries(self, content: str) -> List[str]:
        return split_bib_entries(content)

    def _parse_bibtex_fields(self, bibtex: str) -> Dict[str, str]:
        fields = {}
        for name, value in self.FIELD_PATTERN.findall(bibtex):
            fields[name.lower()] = re.sub(r'\s+', ' ', value.strip())
        return fields

    def _find_entry_field(self, entry: str, field_name: str) -> str:
        return self._parse_bibtex_fields(entry).get(field_name.lower(), '')

    def find_existing_entry(self, identifier: str, bib_file: Optional[str]) -> Optional[str]:
        if not bib_file or not Path(bib_file).exists():
            return None

        raw_identifier = identifier.strip()
        target_doi = ''
        target_url = ''
        target_eprint = ''

        if raw_identifier.startswith(('http://', 'https://')):
            extracted_doi = self.extract_doi_from_url(raw_identifier)
            if extracted_doi:
                target_doi = self.clean_doi(extracted_doi).lower()
            else:
                target_url = self.normalize_url(raw_identifier)
            extracted_arxiv = self.extract_arxiv_id_from_url(raw_identifier)
            if extracted_arxiv:
                target_eprint = extracted_arxiv
        elif re.match(r'^\d{4}\.\d{4,5}$', raw_identifier):
            target_eprint = raw_identifier
        elif not raw_identifier.isdigit():
            target_doi = self.clean_doi(raw_identifier).lower()

        try:
            content = Path(bib_file).read_text(encoding='utf-8')
        except OSError:
            return None

        for entry in self._split_bib_entries(content):
            entry_doi = self.clean_doi(self._find_entry_field(entry, 'doi')).lower() if self._find_entry_field(entry, 'doi') else ''
            entry_url = self.normalize_url(self._find_entry_field(entry, 'url')) if self._find_entry_field(entry, 'url') else ''
            entry_eprint = self._find_entry_field(entry, 'eprint')

            if target_doi and entry_doi == target_doi:
                return entry.strip()
            if target_url and entry_url == target_url:
                return entry.strip()
            if target_eprint and entry_eprint == target_eprint:
                return entry.strip()

        return None

    def _extract_year(self, message: Dict) -> str:
        for key in ('published-print', 'published-online', 'created', 'issued'):
            parts = message.get(key, {}).get('date-parts', [])
            if parts and parts[0]:
                return str(parts[0][0])
        return ''

    def _format_authors(self, authors: List[Dict]) -> str:
        formatted = []
        for author in authors or []:
            family = author.get('family', '').strip()
            given = author.get('given', '').strip()
            if family and given:
                formatted.append(f'{family}, {given}')
            elif family:
                formatted.append(family)
        return ' and '.join(formatted)

    def _build_bibtex(self, entry_type: str, key: str, fields: Dict[str, str]) -> str:
        lines = [f'@{entry_type}{{{key},']
        ordered_names = [
            'author', 'title', 'journal', 'volume', 'number', 'pages', 'year',
            'doi', 'url', 'eprint', 'archiveprefix', 'abstract',
        ]
        field_widths = {
            'eprint': 9,
        }
        for name in ordered_names:
            value = fields.get(name)
            if value:
                width = field_widths.get(name, 10)
                lines.append(f'  {name.ljust(width)} = {{{value}}},')
        if lines[-1].endswith(','):
            lines[-1] = lines[-1][:-1]
        lines.append('}')
        return '\n'.join(lines)

    def _fix_bibtex_fields(
        self,
        bibtex: str,
        doi: str = '',
        crossref_metadata: Optional[Dict] = None,
    ) -> str:
        header, _, rest = bibtex.partition('\n')
        fields = self._parse_bibtex_fields(rest)

        raw_title = fields.get('title', '')
        if raw_title:
            fields['title'] = normalize_title_for_bibtex(raw_title)

        journal = fields.get('journal', '')
        if journal:
            fields['journal'] = self.abbreviate_journal(journal)

        metadata = crossref_metadata or {}
        issue = metadata.get('issue') or metadata.get('number')
        article_number = metadata.get('article-number')
        page = metadata.get('page')
        if issue and not fields.get('number'):
            fields['number'] = str(issue)
        if not fields.get('pages'):
            if article_number:
                fields['pages'] = str(article_number)
            elif page:
                fields['pages'] = str(page)

        ordered = {}
        ordered['author'] = fields.get('author', '')
        ordered['title'] = fields.get('title', '')
        ordered['journal'] = fields.get('journal', '')
        ordered['volume'] = fields.get('volume', '')
        ordered['number'] = fields.get('number', '')
        ordered['pages'] = fields.get('pages', '')
        ordered['year'] = fields.get('year', '')
        ordered['doi'] = fields.get('doi', doi)
        ordered['url'] = fields.get('url', '')
        ordered['eprint'] = fields.get('eprint', '')
        ordered['archiveprefix'] = fields.get('archiveprefix', '')
        ordered['abstract'] = fields.get('abstract', '')

        entry_type = 'misc' if ordered['eprint'] and not ordered['journal'] else 'article'
        key_match = re.match(r'@\w+\{([^,]+),', bibtex)
        key = key_match.group(1) if key_match else (ordered['eprint'] or doi or 'tmp')
        return self._build_bibtex(entry_type, key, ordered)

    def fetch_from_crossref(self, doi: str, fetch_abstract: bool = False) -> Optional[str]:
        if self.session is None:
            return None

        try:
            response = self.session.get(
                f'https://api.crossref.org/works/{doi}',
                timeout=self.timeout,
            )
            response.raise_for_status()
            message = response.json().get('message', {})
        except Exception:
            return None

        title_list = message.get('title') or []
        journal_list = message.get('container-title') or []
        fields = {
            'author': self._format_authors(message.get('author') or []),
            'title': title_list[0] if title_list else '',
            'journal': journal_list[0] if journal_list else '',
            'volume': str(message.get('volume', '') or ''),
            'number': str(message.get('issue', '') or ''),
            'pages': str(message.get('page', '') or message.get('article-number', '') or ''),
            'year': self._extract_year(message),
            'doi': self.clean_doi(message.get('DOI', doi) or doi),
            'url': message.get('URL', '') or '',
        }
        if fetch_abstract and message.get('abstract'):
            fields['abstract'] = message['abstract']

        key = re.sub(r'[^A-Za-z0-9]+', '', fields['doi']) or 'tmp'
        bibtex = self._build_bibtex('article', key, fields)
        return self._fix_bibtex_fields(bibtex, doi=fields['doi'], crossref_metadata=message)

    def _arxiv_html_to_bibtex(self, html: str, arxiv_id: str) -> Optional[str]:
        def meta_values(name: str) -> List[str]:
            pattern = rf'<meta\s+name="{re.escape(name)}"\s+content="([^"]*)"'
            return [html_lib.unescape(value).strip() for value in re.findall(pattern, html, flags=re.I)]

        title_values = meta_values('citation_title')
        author_values = meta_values('citation_author')
        date_values = meta_values('citation_date')
        abstract_values = meta_values('citation_abstract')

        title = title_values[0] if title_values else ''
        authors = ' and '.join(author_values)
        year = date_values[0][:4] if date_values else ''
        fields = {
            'author': authors,
            'title': title,
            'year': year,
            'eprint': arxiv_id,
            'archiveprefix': 'arXiv',
            'url': f'https://arxiv.org/abs/{arxiv_id}',
            'abstract': abstract_values[0] if abstract_values else '',
        }
        bibtex = self._build_bibtex('misc', arxiv_id, fields)
        return self._fix_bibtex_fields(bibtex)

    def fetch_from_arxiv(self, arxiv_id: str, fetch_abstract: bool = False) -> Optional[str]:
        if self.session is None:
            return None

        try:
            response = self.session.get(
                f'https://arxiv.org/abs/{arxiv_id}',
                timeout=self.timeout,
            )
            response.raise_for_status()
            return self._arxiv_html_to_bibtex(response.text, arxiv_id)
        except Exception:
            return None

    def fetch_from_pubmed(self, pmid: str, fetch_abstract: bool = False) -> Optional[str]:
        return None

    def extract_bibtex(
        self,
        identifier: str,
        fetch_abstract: bool = False,
        bib_file: Optional[str] = None,
    ) -> Optional[str]:
        identifier = identifier.strip()

        existing_entry = self.find_existing_entry(identifier, bib_file)
        if existing_entry:
            return existing_entry

        if identifier.startswith(('http://', 'https://')):
            doi = self.extract_doi_from_url(identifier)
            if doi:
                return self.fetch_from_crossref(doi, fetch_abstract=fetch_abstract)

            arxiv_id = self.extract_arxiv_id_from_url(identifier)
            if arxiv_id:
                return self.fetch_from_arxiv(arxiv_id, fetch_abstract=fetch_abstract)

            pmid = self.extract_pmid_from_url(identifier)
            if pmid:
                return self.fetch_from_pubmed(pmid, fetch_abstract=fetch_abstract)
            return None

        if identifier.isdigit():
            return self.fetch_from_pubmed(identifier, fetch_abstract=fetch_abstract)

        if re.match(r'^\d{4}\.\d{4,5}$', identifier):
            return self.fetch_from_arxiv(identifier, fetch_abstract=fetch_abstract)

        return self.fetch_from_crossref(self.clean_doi(identifier), fetch_abstract=fetch_abstract)

    def generate_inline_citation(self, bibtex: str, style: str = 'journal') -> str:
        fields = self._parse_bibtex_fields(bibtex)
        eprint = fields.get('eprint', '')
        if eprint and not fields.get('journal'):
            year = fields.get('year', '')
            suffix = f', ({year})' if year else ''
            return f'arXiv:{eprint}{suffix}'

        journal = fields.get('journal', '')
        volume = fields.get('volume', '')
        pages = fields.get('pages', '')
        year = fields.get('year', '')

        body = journal
        if volume:
            body = f'{body} {volume}'.strip()
        if pages:
            body = f'{body}, {pages}'.strip(', ')
        if year:
            body = f'{body} ({year})'.strip()
        return body.strip()


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
