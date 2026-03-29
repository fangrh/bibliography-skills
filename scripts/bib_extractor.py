#!/usr/bin/env python3
"""
Bibliography Extractor - Zotero-like tool for extracting BibTeX entries
Supports DOIs, URLs, PMIDs, and arXiv IDs
"""

import sys
import re
import argparse
import json
from typing import Optional, Dict, List
from urllib.parse import urlparse
from pathlib import Path
import time

try:
    import requests
except ImportError:
    print("Error: requests module not found. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


class BibExtractor:
    """Extract BibTeX entries from DOIs, URLs, PMIDs, and arXiv IDs."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BibExtractor/1.0 (Citation Management Tool)'
        })

    def extract_doi_from_url(self, url: str) -> Optional[str]:
        """Extract DOI from URL if present."""
        # Pattern for DOI in URL
        doi_patterns = [
            r'/doi/10\.\d{4,9}/[^\s\?"<>#]+',
            r'doi\.org/10\.\d{4,9}/[^\s\?"<>#]+',
        ]

        for pattern in doi_patterns:
            match = re.search(pattern, url)
            if match:
                doi = match.group(0)
                # Clean up DOI
                doi = re.sub(r'^/doi/', '', doi)
                doi = re.sub(r'^doi\.org/', '', doi)
                # Remove query parameters and fragments
                doi = re.sub(r'[?#].*$', '', doi)
                return doi

        return None

    def extract_arxiv_id_from_url(self, url: str) -> Optional[str]:
        """Extract arXiv ID from URL."""
        match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d+\.\d+)', url)
        return match.group(1) if match else None

    def extract_pmid_from_url(self, url: str) -> Optional[str]:
        """Extract PMID from PubMed URL."""
        match = re.search(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)', url)
        return match.group(1) if match else None

    def clean_doi(self, doi: str) -> str:
        """Clean and normalize DOI."""
        doi = doi.strip()

        # Remove common prefixes
        prefixes = ['https://doi.org/', 'http://doi.org/', 'doi:', 'doi: ']
        for prefix in prefixes:
            if doi.lower().startswith(prefix.lower()):
                doi = doi[len(prefix):]
                break

        # Remove trailing slash
        doi = doi.rstrip('/')

        return doi

    def fetch_from_crossref(self, doi: str) -> Optional[str]:
        """Fetch BibTeX from CrossRef API."""
        url = f'https://doi.org/{doi}'
        headers = {
            'Accept': 'application/x-bibtex; charset=utf-8',
            'User-Agent': 'BibExtractor/1.0'
        }

        try:
            response = self.session.get(url, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                bibtex = response.text.strip()
                # Fix @data{ to @misc{
                if bibtex.startswith('@data{'):
                    bibtex = bibtex.replace('@data{', '@misc{', 1)
                return bibtex
            elif response.status_code == 404:
                print(f'  Warning: DOI not found in CrossRef: {doi}', file=sys.stderr)
                return None
            else:
                print(f'  Warning: CrossRef returned status {response.status_code} for {doi}', file=sys.stderr)
                return None

        except requests.exceptions.Timeout:
            print(f'  Warning: Timeout fetching from CrossRef: {doi}', file=sys.stderr)
            return None
        except requests.exceptions.RequestException as e:
            print(f'  Warning: Request failed: {e}', file=sys.stderr)
            return None

    def fetch_from_pubmed(self, pmid: str) -> Optional[str]:
        """Fetch metadata from PubMed and convert to BibTeX."""
        # First fetch JSON metadata
        url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
        params = {
            'db': 'pubmed',
            'id': pmid,
            'retmode': 'json',
            'rettype': 'full'
        }

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                return self._pubmed_to_bibtex(data, pmid)
            else:
                return None

        except Exception as e:
            print(f'  Warning: PubMed fetch failed: {e}', file=sys.stderr)
            return None

    def fetch_from_arxiv(self, arxiv_id: str) -> Optional[str]:
        """Fetch metadata from arXiv and convert to BibTeX."""
        # Use arXiv API with JSON format
        url = f'http://export.arxiv.org/api/query?id_list={arxiv_id}'

        try:
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == 200:
                return self._arxiv_to_bibtex(response.text, arxiv_id)
            else:
                print(f'  Warning: arXiv returned status {response.status_code}', file=sys.stderr)
                return None

        except Exception as e:
            print(f'  Warning: arXiv fetch failed: {e}', file=sys.stderr)
            return None

    def _pubmed_to_bibtex(self, data: Dict, pmid: str) -> Optional[str]:
        """Convert PubMed JSON to BibTeX."""
        try:
            article = data.get('PubmedArticleSet', {}).get('PubmedArticle', {})
            medline = article.get('MedlineCitation', {}).get('Article', {})

            # Extract authors
            authors = []
            author_list = medline.get('AuthorList', {}).get('Author', [])
            if not isinstance(author_list, list):
                author_list = [author_list]

            for a in author_list:
                last = a.get('LastName', '')
                first = a.get('ForeName', '') or a.get('Initials', '')
                if last and first:
                    authors.append(f'{last}, {first}')
                elif last:
                    authors.append(last)

            authors_str = ' and '.join(authors) if authors else 'Unknown'

            # Extract other fields
            title = medline.get('ArticleTitle', {}).get('value', '') or ''
            journal_info = medline.get('Journal', {}).get('JournalIssue', {})
            journal = medline.get('Journal', {}).get('Title', '')

            volume = journal_info.get('Volume', '')
            issue = journal_info.get('Issue', '')
            pages = medline.get('Pagination', {}).get('MedlinePgn', '')

            pub_date = journal_info.get('PubDate', {})
            year = str(pub_date.get('Year', ''))

            # Build BibTeX
            bibtex = f'@article{{{pmid},\n'
            bibtex += f'  author    = {{{authors_str}}},\n'
            bibtex += f'  title     = {{{title}}},\n'
            bibtex += f'  journal   = {{{journal}}},\n'
            if volume:
                bibtex += f'  volume    = {{{volume}}},\n'
            if issue:
                bibtex += f'  number    = {{{issue}}},\n'
            if pages:
                bibtex += f'  pages     = {{{pages}}},\n'
            if year:
                bibtex += f'  year      = {{{year}}},\n'
            bibtex += f'  pmid     = {{{pmid}}}\n'
            bibtex += '}'

            return bibtex

        except Exception as e:
            print(f'  Warning: Failed to parse PubMed data: {e}', file=sys.stderr)
            return None

    def _arxiv_to_bibtex(self, xml: str, arxiv_id: str) -> Optional[str]:
        """Convert arXiv XML to BibTeX."""
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml)

            # arXiv uses Atom format
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            entry = root.find('.//atom:entry', ns)
            if entry is None:
                return None

            # Extract title
            title_elem = entry.find('atom:title', ns)
            title = title_elem.text if title_elem is not None else ''

            # Extract authors
            authors = []
            for author in entry.findall('atom:author', ns):
                name_elem = author.find('atom:name', ns)
                if name_elem is not None:
                    # Convert "First Last" to "Last, First"
                    parts = name_elem.text.split(' ', 1)
                    if len(parts) == 2:
                        authors.append(f'{parts[1]}, {parts[0]}')
                    else:
                        authors.append(name_elem.text)

            authors_str = ' and '.join(authors) if authors else 'Unknown'

            # Extract year from published date
            pub_elem = entry.find('atom:published', ns)
            year = ''
            if pub_elem is not None and pub_elem.text:
                year = pub_elem.text[:4]

            # Build BibTeX (use @misc for preprints)
            bibtex = f'@misc{{{arxiv_id.replace(".", "")},\n'
            bibtex += f'  author    = {{{authors_str}}},\n'
            bibtex += f'  title     = {{{title}}},\n'
            if year:
                bibtex += f'  year      = {{{year}}},\n'
            bibtex += f'  eprint    = {{{arxiv_id}}},\n'
            bibtex += f'  archive   = {{arXiv}},\n'
            bibtex += f'  url       = {{https://arxiv.org/abs/{arxiv_id}}}\n'
            bibtex += '}'

            return bibtex

        except Exception as e:
            print(f'  Warning: Failed to parse arXiv data: {e}', file=sys.stderr)
            return None

    def generate_citation_key(self, bibtex: str, existing_keys: set) -> str:
        """Generate a citation key from BibTeX entry."""
        # Parse entry for author and year
        author_match = re.search(r'author\s*=\s*\{([^}]+)\}', bibtex)
        year_match = re.search(r'year\s*=\s*\{([^}]+)\}', bibtex)
        title_match = re.search(r'title\s*=\s*\{([^}]+)\}', bibtex)

        # Get first author's last name
        first_author = 'Unknown'
        if author_match:
            authors = author_match.group(1).split(' and ')
            first_author = authors[0].strip()
            if ',' in first_author:
                first_author = first_author.split(',')[0].strip()

        # Get year
        year = '2024'
        if year_match:
            year = year_match.group(1)[:4] if year_match.group(1) else '2024'

        # Get keywords from title
        keywords = 'Paper'
        if title_match:
            title = title_match.group(1)
            # Remove braces and special chars, get first 2 words
            title_clean = re.sub(r'[{}\'".,;:]', '', title)
            words = title_clean.split()
            if len(words) >= 2:
                keywords = words[0] + words[1][:3]
            elif len(words) == 1:
                keywords = words[0][:7]

        # Build base key
        base_key = f'{first_author}{year}{keywords}'
        # Remove special characters
        base_key = re.sub(r'[^a-zA-Z0-9]', '', base_key)

        # Handle duplicates
        if base_key not in existing_keys:
            return base_key

        # Add suffix
        for suffix in ['', 'a', 'b', 'c', 'd', 'e']:
            test_key = base_key + suffix
            if test_key not in existing_keys:
                return test_key

        # Fallback: use number
        i = 1
        while f'{base_key}{i}' in existing_keys:
            i += 1
        return f'{base_key}{i}'

    def extract_bibtex(self, identifier: str) -> Optional[str]:
        """Extract BibTeX entry from identifier (DOI, URL, PMID, arXiv ID)."""
        identifier = identifier.strip()

        # Check if it's a URL
        if identifier.startswith(('http://', 'https://')):
            # Try to extract DOI from URL
            doi = self.extract_doi_from_url(identifier)
            if doi:
                print(f'  Extracted DOI: {doi}', file=sys.stderr)
                return self.fetch_from_crossref(doi)

            # Try arXiv
            arxiv_id = self.extract_arxiv_id_from_url(identifier)
            if arxiv_id:
                print(f'  Extracted arXiv ID: {arxiv_id}', file=sys.stderr)
                return self.fetch_from_arxiv(arxiv_id)

            # Try PubMed
            pmid = self.extract_pmid_from_url(identifier)
            if pmid:
                print(f'  Extracted PMID: {pmid}', file=sys.stderr)
                return self.fetch_from_pubmed(pmid)

            # Fallback: try treating URL as DOI
            if 'doi' in identifier.lower():
                doi = self.clean_doi(identifier)
                return self.fetch_from_crossref(doi)

            print(f'  Warning: Could not extract identifier from URL: {identifier}', file=sys.stderr)
            return None

        # Check if it's a PMID (numeric)
        if identifier.isdigit():
            return self.fetch_from_pubmed(identifier)

        # Check if it's an arXiv ID
        arxiv_match = re.match(r'^\d{4}\.\d{4,5}$', identifier)
        if arxiv_match:
            return self.fetch_from_arxiv(identifier)

        # Treat as DOI
        doi = self.clean_doi(identifier)
        return self.fetch_from_crossref(doi)

    def read_existing_keys(self, bib_file: str) -> set:
        """Read existing citation keys from BibTeX file."""
        keys = set()

        try:
            with open(bib_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract citation keys using regex
                matches = re.find(r'@(\w+)\{([^,]+),', content)
                for match in matches:
                    keys.add(match[1])
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f'  Warning: Could not read existing keys: {e}', file=sys.stderr)

        return keys

    def append_to_file(self, bibtex: str, bib_file: str, existing_keys: set) -> str:
        """Append BibTeX entry to file with generated citation key."""
        # Generate citation key
        key = self.generate_citation_key(bibtex, existing_keys)

        # Replace placeholder key with generated key
        bibtex = re.sub(r'@(\w+)\{[^,]+,', f'@\\1{{{key},', bibtex, count=1)

        # Write to file
        with open(bib_file, 'a', encoding='utf-8') as f:
            # Add blank lines for separation
            content = f.read()
            if content and not content.endswith('\n\n'):
                f.write('\n\n')
            elif not content:
                # New file, no blank lines needed
                pass
            else:
                f.write('\n\n')

            f.write(bibtex)

        return key

    def process_batch(self, identifiers: List[str], bib_file: str,
                    delay: float = 1.0) -> tuple[int, int]:
        """Process multiple identifiers and append to BibTeX file."""
        # Create file if it doesn't exist
        Path(bib_file).touch(exist_ok=True)

        # Read existing keys
        existing_keys = self.read_existing_keys(bib_file)

        successful = 0
        failed = 0

        print(f'\nProcessing {len(identifiers)} identifier(s)...', file=sys.stderr)
        print(f'Output file: {bib_file}\n', file=sys.stderr)

        for i, identifier in enumerate(identifiers, 1):
            print(f'[{i}/{len(identifiers)}] Processing: {identifier}', file=sys.stderr)

            bibtex = self.extract_bibtex(identifier)

            if bibtex:
                key = self.append_to_file(bibtex, bib_file, existing_keys)
                existing_keys.add(key)
                successful += 1
                print(f'  -> SUCCESS: Added {key}\n', file=sys.stderr)
            else:
                failed += 1
                print(f'  -> FAILED\n', file=sys.stderr)

            # Rate limiting
            if i < len(identifiers):
                time.sleep(delay)

        # Summary
        print(f'\nSummary: {successful}/{len(identifiers)} successful, {failed} failed', file=sys.stderr)

        return successful, failed


def main():
    parser = argparse.ArgumentParser(
        description='Extract bibliography from DOIs, URLs, PMIDs, and arXiv IDs and append to BibTeX file.',
        epilog='Examples:\n'
                '  %(prog)s 10.1038/s41586-021-03926-0\n'
                '  %(prog)s https://doi.org/10.1126/science.abf5641\n'
                '  %(prog)s --input dois.txt --output references.bib'
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
        default='references.bib',
        help='Output BibTeX file (default: references.bib)'
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

    # Create extractor
    extractor = BibExtractor(timeout=args.timeout)

    # Process
    if args.print_only:
        # Print to stdout only
        print(f'# Extracting {len(identifiers)} bibliography entry(ies)', file=sys.stderr)
        for i, identifier in enumerate(identifiers, 1):
            print(f'[{i}/{len(identifiers)}] {identifier}', file=sys.stderr)
            bibtex = extractor.extract_bibtex(identifier)
            if bibtex:
                print()
                print(bibtex)
            else:
                print(f'  Failed to extract: {identifier}', file=sys.stderr)
            if i < len(identifiers):
                time.sleep(args.delay)
    else:
        # Append to file
        extractor.process_batch(identifiers, args.output, delay=args.delay)


if __name__ == '__main__':
    main()
