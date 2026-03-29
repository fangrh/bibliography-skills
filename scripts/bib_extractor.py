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

    # Journal-specific handlers registry
    # Add new journal handlers here as they are discovered
    JOURNAL_HANDLERS = {
        'science': {
            'patterns': ['science.org', 'sciencemag.org', 'science.'],
            'description': 'Science Magazine (AAAS)',
            'notes': 'Uses volume, number (issue), pages format'
        },
        'nature': {
            'patterns': ['nature.com', 'nature.'],
            'description': 'Nature Publishing Group',
            'notes': 'Standard format'
        },
        'cell': {
            'patterns': ['cell.com', 'cell.'],
            'description': 'Cell Press',
            'notes': 'May include article number in pages (e.g., 914--930.e20)'
        },
        'pnas': {
            'patterns': ['pnas.org', 'pnas.'],
            'description': 'Proceedings of the National Academy of Sciences',
            'notes': 'Standard format'
        },
        'ieee': {
            'patterns': ['ieee.org', 'ieeexplore.ieee.org', 'ieee.'],
            'description': 'IEEE Publications',
            'notes': 'Standard format with DOI'
        },
        'aps': {
            'patterns': ['aps.org', 'physrev', 'prl.', 'prb.', 'prc.', 'prd.', 'pre.'],
            'description': 'American Physical Society journals',
            'notes': 'Physical Review series'
        },
        'springer': {
            'patterns': ['springer.com', 'link.springer.com'],
            'description': 'Springer Nature',
            'notes': 'Standard format'
        },
        'elsevier': {
            'patterns': ['elsevier.com', 'sciencedirect.com', 'cell.'],
            'description': 'Elsevier',
            'notes': 'Various formats depending on journal'
        },
        'wiley': {
            'patterns': ['wiley.com', 'onlinelibrary.wiley.com'],
            'description': 'Wiley',
            'notes': 'Standard format'
        },
        'arxiv': {
            'patterns': ['arxiv.org'],
            'description': 'arXiv preprints',
            'notes': 'Uses @misc with eprint field'
        },
        'pubmed': {
            'patterns': ['pubmed.ncbi.nlm.nih.gov', 'ncbi.nlm.nih.gov/pubmed'],
            'description': 'PubMed/NCBI',
            'notes': 'Uses PMID identifier'
        }
    }

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BibExtractor/1.0 (Citation Management Tool)'
        })
        self.detected_journal = None

    def detect_journal(self, identifier: str, bibtex: str = '') -> Optional[str]:
        """Detect the journal from identifier or BibTeX content."""
        identifier_lower = identifier.lower()
        bibtex_lower = bibtex.lower()

        for journal_key, handler in self.JOURNAL_HANDLERS.items():
            for pattern in handler['patterns']:
                if pattern in identifier_lower or pattern in bibtex_lower:
                    return journal_key

        return None

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

    def fetch_citation_count(self, doi: str) -> Optional[int]:
        """Fetch citation count for a DOI from multiple sources.

        Tries in order:
        1. CrossRef API
        2. OpenAlex API
        3. Semantic Scholar API

        Returns:
            Citation count or None if unavailable
        """
        # Try CrossRef first
        try:
            url = f'https://api.crossref.org/works/{doi}'
            headers = {'User-Agent': 'BibExtractor/1.0'}
            response = self.session.get(url, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                count = data.get('message', {}).get('is-referenced-by-count')
                if count is not None:
                    print(f'  Citations (CrossRef): {count}', file=sys.stderr)
                    return count
        except Exception as e:
            pass

        # Try OpenAlex
        try:
            url = f'https://api.openalex.org/works/doi:{doi}'
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                count = data.get('cited_by_count')
                if count is not None:
                    print(f'  Citations (OpenAlex): {count}', file=sys.stderr)
                    return count
        except Exception as e:
            pass

        # Try Semantic Scholar
        try:
            url = f'https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=citationCount'
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                count = data.get('citationCount')
                if count is not None:
                    print(f'  Citations (Semantic Scholar): {count}', file=sys.stderr)
                    return count
        except Exception as e:
            pass

        print(f'  Citations: Not available', file=sys.stderr)
        return None

    def fetch_from_crossref(self, doi: str) -> Optional[str]:
        """Fetch BibTeX from CrossRef API.

        Returns:
            BibTeX string on success, None on failure (with structured error message)
        """
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

                # Fetch citation count
                citation_count = self.fetch_citation_count(doi)

                # Post-process to fix common issues and add citations
                bibtex = self._fix_bibtex_fields(bibtex, doi, citation_count)
                return bibtex
            elif response.status_code == 404:
                print(f'  ERROR_INVALID: DOI not found in CrossRef: {doi}', file=sys.stderr)
                print(f'  LLM_ACTION: This DOI is invalid or not indexed. Please remove it from the bibliography if it exists.', file=sys.stderr)
                return None
            else:
                print(f'  ERROR: CrossRef returned status {response.status_code} for {doi}', file=sys.stderr)
                return None

        except requests.exceptions.Timeout:
            print(f'  ERROR: Timeout fetching from CrossRef: {doi}', file=sys.stderr)
            return None
        except requests.exceptions.RequestException as e:
            print(f'  ERROR: Request failed: {e}', file=sys.stderr)
            return None

    def _fix_bibtex_fields(self, bibtex: str, doi: str, citation_count: Optional[int] = None) -> str:
        """Fix and clean up BibTeX fields for consistent formatting.

        This method:
        1. Detects the journal type
        2. Applies journal-specific fixes if needed
        3. Adds citation count if available
        4. Formats output consistently
        """
        # Detect journal from DOI and BibTeX content
        self.detected_journal = self.detect_journal(doi, bibtex)

        # Parse the BibTeX entry
        entry_type_match = re.match(r'@(\w+)\s*\{([^,]+),\s*', bibtex)
        if not entry_type_match:
            return bibtex

        entry_type = entry_type_match.group(1)
        original_key = entry_type_match.group(2)

        # Extract all fields
        fields = {}
        field_pattern = r'(\w+)\s*=\s*\{([^}]+)\}'
        for match in re.finditer(field_pattern, bibtex):
            field_name = match.group(1).lower()
            field_value = match.group(2).strip()
            fields[field_name] = field_value

        # Apply journal-specific fixes
        fields = self._apply_journal_specific_fixes(fields, self.detected_journal)

        # Add citation count if available
        if citation_count is not None:
            fields['citations'] = str(citation_count)

        # Build clean BibTeX entry with consistent field order
        field_order = [
            'author', 'title', 'journal', 'booktitle', 'volume', 'number', 'pages',
            'year', 'month', 'citations', 'doi', 'url', 'issn', 'isbn', 'publisher', 'eprint', 'archive', 'pmid'
        ]

        # Build the new entry
        new_bibtex = f"@{entry_type}{{{original_key},\n"

        for field in field_order:
            if field in fields:
                value = fields[field]
                # Fix pages: use en-dash
                if field == 'pages':
                    value = self._fix_pages_format(value)
                # Format field with consistent spacing
                new_bibtex += f"  {field:<10} = {{{value}}},\n"

        # Add any remaining fields not in the order list
        for field, value in fields.items():
            if field not in field_order:
                new_bibtex += f"  {field:<10} = {{{value}}},\n"

        # Remove trailing comma and close
        new_bibtex = new_bibtex.rstrip(',\n')
        new_bibtex += "\n}"

        return new_bibtex

    def _fix_pages_format(self, pages: str) -> str:
        """Fix page format to use en-dash consistently."""
        # Convert single dash to en-dash, but preserve article numbers with suffixes
        # like "914--930.e20" which are already correct or have special suffixes
        if '.e' in pages or '.E' in pages:
            # Cell-style article numbers with supplemental info
            pages = re.sub(r'(?<!-)-(?!-)', '--', pages)
            pages = pages.replace('----', '--')
            return pages
        else:
            # Standard page ranges
            pages = re.sub(r'(?<!-)-(?!-)', '--', pages)
            pages = pages.replace('----', '--')
            return pages

    def _apply_journal_specific_fixes(self, fields: Dict, journal: Optional[str]) -> Dict:
        """Apply journal-specific metadata corrections.

        This is where you can add fixes for specific journals.
        If a journal is not recognized, the normal format is used.

        Args:
            fields: Dictionary of BibTeX fields
            journal: Detected journal key (e.g., 'science', 'nature')

        Returns:
            Corrected fields dictionary
        """
        if not journal:
            # Unknown journal - use normal format
            return fields

        # Journal-specific corrections
        if journal == 'science':
            # Science magazine:
            # - volume is correct
            # - number is the issue number (e.g., 6464)
            # - pages should be actual page range (e.g., 499--504)
            # CrossRef usually gets this right, but we ensure consistency
            pass

        elif journal == 'cell':
            # Cell:
            # - Sometimes includes article suffix in pages (e.g., 914--930.e20)
            # - This is valid, keep as-is
            pass

        elif journal == 'nature':
            # Nature:
            # - Standard format, usually correct from CrossRef
            pass

        elif journal == 'aps':
            # APS journals (PRL, PRB, etc.):
            # - Standard format
            # - Sometimes missing page numbers
            pass

        elif journal == 'ieee':
            # IEEE:
            # - Standard format
            # - Always include DOI
            pass

        # Add more journal-specific handlers here as needed
        # Example:
        # elif journal == 'some_journal':
        #     # Fix specific issues
        #     if 'pages' in fields and fields['pages'].isdigit():
        #         # Move short number from pages to number
        #         fields['number'] = fields['pages']
        #         del fields['pages']

        return fields

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

    def clean_invalid_entries(self, bib_file: str, output_file: Optional[str] = None) -> tuple[int, int]:
        """Remove invalid entries from BibTeX file.

        Validates each DOI in the file and removes entries with invalid DOIs.

        Args:
            bib_file: Path to BibTeX file
            output_file: Output file (default: overwrite input)

        Returns:
            Tuple of (valid_count, removed_count)
        """
        if output_file is None:
            output_file = bib_file

        try:
            with open(bib_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f'Error: File not found: {bib_file}', file=sys.stderr)
            return 0, 0

        # Parse entries
        entry_pattern = r'(@\w+\s*\{[^}]+,.*?(?=@\w+\s*\{|$))'
        entries = re.findall(entry_pattern, content, re.DOTALL)

        valid_entries = []
        removed_count = 0

        print(f'Validating {len(entries)} entries...', file=sys.stderr)

        for i, entry in enumerate(entries, 1):
            # Extract DOI
            doi_match = re.search(r'doi\s*=\s*\{([^}]+)\}', entry, re.IGNORECASE)

            if doi_match:
                doi = self.clean_doi(doi_match.group(1))
                print(f'[{i}/{len(entries)}] Validating DOI: {doi}', file=sys.stderr)

                # Check if DOI is valid
                try:
                    response = self.session.head(
                        f'https://doi.org/{doi}',
                        timeout=10,
                        allow_redirects=True
                    )

                    if response.status_code == 200:
                        valid_entries.append(entry)
                        print(f'  -> VALID', file=sys.stderr)
                    else:
                        removed_count += 1
                        print(f'  -> INVALID (status {response.status_code}) - REMOVING', file=sys.stderr)
                except Exception as e:
                    # Keep entries on network errors
                    valid_entries.append(entry)
                    print(f'  -> KEEP (network error: {e})', file=sys.stderr)

                time.sleep(0.5)  # Rate limiting
            else:
                # No DOI - keep the entry
                valid_entries.append(entry)
                print(f'[{i}/{len(entries)}] No DOI - keeping entry', file=sys.stderr)

        # Write valid entries back
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(valid_entries))

        print(f'\nSummary: {len(valid_entries)} valid, {removed_count} removed', file=sys.stderr)
        return len(valid_entries), removed_count

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

    parser.add_argument(
        '--clean-invalid',
        action='store_true',
        help='Remove entries with invalid DOIs from the BibTeX file'
    )

    args = parser.parse_args()

    # Create extractor
    extractor = BibExtractor(timeout=args.timeout)

    # Clean invalid entries mode
    if args.clean_invalid:
        extractor.clean_invalid_entries(args.output)
        return

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
