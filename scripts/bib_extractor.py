#!/usr/bin/env python3
"""
Bibliography Extractor - Zotero-like tool for extracting BibTeX entries
Supports DOIs, URLs, PMIDs, and arXiv IDs
"""

import sys
import re
import argparse
import json
from typing import Optional, Dict, List, Tuple
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

    # Journal abbreviation database
    # Maps full journal names to their standard abbreviations
    JOURNAL_ABBREVIATIONS = {
        # American Physical Society journals
        'Physical Review Letters': 'Phys. Rev. Lett.',
        'Physical Review A': 'Phys. Rev. A',
        'Physical Review B': 'Phys. Rev. B',
        'Physical Review C': 'Phys. Rev. C',
        'Physical Review D': 'Phys. Rev. D',
        'Physical Review E': 'Phys. Rev. E',
        'Physical Review Applied': 'Phys. Rev. Appl.',
        'Physical Review Materials': 'Phys. Rev. Mater.',
        'Physical Review X': 'Phys. Rev. X',
        'Reviews of Modern Physics': 'Rev. Mod. Phys.',
        'Physical Review': 'Phys. Rev.',

        # Nature family
        'Nature': 'Nature',
        'Nature Communications': 'Nat. Commun.',
        'Nature Physics': 'Nat. Phys.',
        'Nature Materials': 'Nat. Mater.',
        'Nature Nanotechnology': 'Nat. Nanotechnol.',
        'Nature Photonics': 'Nat. Photonics',
        'Nature Electronics': 'Nat. Electron.',
        'Nature Chemistry': 'Nat. Chem.',
        'Nature Biology': 'Nat. Biol.',
        'Nature Medicine': 'Nat. Med.',
        'Nature Neuroscience': 'Nat. Neurosci.',
        'Nature Methods': 'Nat. Methods',
        'Nature Biotechnology': 'Nat. Biotechnol.',
        'Nature Climate Change': 'Nat. Clim. Change',
        'Nature Energy': 'Nat. Energy',
        'Nature Computational Science': 'Nat. Comput. Sci.',
        'Nature Machine Intelligence': 'Nat. Mach. Intell.',
        'Scientific Reports': 'Sci. Rep.',

        # Science family
        'Science': 'Science',
        'Science Advances': 'Sci. Adv.',
        'Science Immunology': 'Sci. Immunol.',
        'Science Robotics': 'Sci. Robot.',
        'Science Translational Medicine': 'Sci. Transl. Med.',
        'Science Signaling': 'Sci. Signal.',

        # Cell Press
        'Cell': 'Cell',
        'Molecular Cell': 'Mol. Cell',
        'Cancer Cell': 'Cancer Cell',
        'Neuron': 'Neuron',
        'Immunity': 'Immunity',
        'Developmental Cell': 'Dev. Cell',

        # PNAS
        'Proceedings of the National Academy of Sciences': 'Proc. Natl. Acad. Sci. U.S.A.',
        'Proceedings of the National Academy of Sciences of the United States of America': 'Proc. Natl. Acad. Sci. U.S.A.',

        # IEEE
        'IEEE Transactions on Electron Devices': 'IEEE Trans. Electron Devices',
        'IEEE Transactions on Applied Superconductivity': 'IEEE Trans. Appl. Supercond.',
        'IEEE Transactions on Magnetics': 'IEEE Trans. Magn.',
        'IEEE Transactions on Microwave Theory and Techniques': 'IEEE Trans. Microw. Theory Tech.',
        'IEEE Journal of Quantum Electronics': 'IEEE J. Quantum Electron.',
        'IEEE Electron Device Letters': 'IEEE Electron Device Lett.',
        'IEEE Microwave and Wireless Components Letters': 'IEEE Microw. Wirel. Compon. Lett.',
        'Proceedings of the IEEE': 'Proc. IEEE',

        # Other major journals
        'Journal of Applied Physics': 'J. Appl. Phys.',
        'Applied Physics Letters': 'Appl. Phys. Lett.',
        'Applied Physics Reviews': 'Appl. Phys. Rev.',
        'Review of Scientific Instruments': 'Rev. Sci. Instrum.',
        'Journal of Chemical Physics': 'J. Chem. Phys.',
        'The Journal of Chemical Physics': 'J. Chem. Phys.',

        # Nano letters / ACS
        'Nano Letters': 'Nano Lett.',
        'ACS Nano': 'ACS Nano',
        'Journal of the American Chemical Society': 'J. Am. Chem. Soc.',
        'ACS Applied Materials & Interfaces': 'ACS Appl. Mater. Interfaces',
        'ACS Photonics': 'ACS Photonics',
        'Chemical Reviews': 'Chem. Rev.',
        'Journal of Physical Chemistry': 'J. Phys. Chem.',
        'The Journal of Physical Chemistry': 'J. Phys. Chem.',
        'Journal of Physical Chemistry C': 'J. Phys. Chem. C',
        'Journal of Physical Chemistry B': 'J. Phys. Chem. B',
        'Journal of Physical Chemistry Letters': 'J. Phys. Chem. Lett.',

        # Springer journals
        'Applied Physics A': 'Appl. Phys. A',
        'Applied Physics B': 'Appl. Phys. B',
        'The European Physical Journal B': 'Eur. Phys. J. B',
        'The European Physical Journal C': 'Eur. Phys. J. C',
        'European Physical Journal Plus': 'Eur. Phys. J. Plus',
        'Zeitschrift für Physik': 'Z. Phys.',
        'Annalen der Physik': 'Ann. Phys.',

        # AIP journals
        'Physics of Fluids': 'Phys. Fluids',
        'Physics of Plasmas': 'Phys. Plasmas',
        'Chaos': 'Chaos',
        'Journal of Mathematical Physics': 'J. Math. Phys.',
        'Low Temperature Physics': 'Low Temp. Phys.',
        'Review of Scientific Instruments': 'Rev. Sci. Instrum.',

        # Optics
        'Optics Express': 'Opt. Express',
        'Optics Letters': 'Opt. Lett.',
        'Optics Communications': 'Opt. Commun.',
        'Optical Materials Express': 'Opt. Mater. Express',
        'Journal of the Optical Society of America B': 'J. Opt. Soc. Am. B',
        'Applied Optics': 'Appl. Opt.',

        # Elsevier journals
        'Solid State Communications': 'Solid State Commun.',
        'Physica C: Superconductivity and its Applications': 'Physica C',
        'Physica B: Condensed Matter': 'Physica B',
        'Physica A: Statistical Mechanics and its Applications': 'Physica A',
        'Physica E: Low-dimensional Systems and Nanostructures': 'Physica E',
        'Nuclear Instruments and Methods in Physics Research A': 'Nucl. Instrum. Methods Phys. Res. A',
        'Nuclear Instruments and Methods in Physics Research B': 'Nucl. Instrum. Methods Phys. Res. B',
        'Surface Science': 'Surf. Sci.',
        'Superlattices and Microstructures': 'Superlattices Microstruct.',
        'Journal of Alloys and Compounds': 'J. Alloys Compd.',
        'Materials Letters': 'Mater. Lett.',
        'Scripta Materialia': 'Scr. Mater.',
        'Acta Materialia': 'Acta Mater.',

        # IOP journals
        'Journal of Physics: Condensed Matter': 'J. Phys.: Condens. Matter',
        'Journal of Physics: Conference Series': 'J. Phys.: Conf. Ser.',
        'Superconductor Science and Technology': 'Supercond. Sci. Technol.',
        'Nanotechnology': 'Nanotechnology',
        '2D Materials': '2D Mater.',
        'Journal of Physics D: Applied Physics': 'J. Phys. D: Appl. Phys.',
        'Semiconductor Science and Technology': 'Semicond. Sci. Technol.',
        'Quantum Science and Technology': 'Quantum Sci. Technol.',
        'Machine Learning: Science and Technology': 'Mach. Learn.: Sci. Technol.',
        'New Journal of Physics': 'New J. Phys.',
        'EPL (Europhysics Letters)': 'EPL',
        'Europhysics Letters': 'EPL',

        # Wiley journals
        'Advanced Materials': 'Adv. Mater.',
        'Advanced Functional Materials': 'Adv. Funct. Mater.',
        'Advanced Electronic Materials': 'Adv. Electron. Mater.',
        'Advanced Quantum Technologies': 'Adv. Quantum Technol.',
        'Small': 'Small',
        'Physica Status Solidi A': 'Phys. Status Solidi A',
        'Physica Status Solidi B': 'Phys. Status Solidi B',
        'Physica Status Solidi C': 'Phys. Status Solidi C',
        'Physica Status Solidi RRL': 'Phys. Status Solidi RRL',
        'Angewandte Chemie International Edition': 'Angew. Chem. Int. Ed.',
        'Angewandte Chemie': 'Angew. Chem.',

        # arXiv categories (for completeness)
        'arXiv preprint': 'arXiv',

        # More specialized journals
        'Superconductor Science and Technology': 'Supercond. Sci. Technol.',
        'IEEE Transactions on Quantum Engineering': 'IEEE Trans. Quantum Eng.',
        'Quantum': 'Quantum',
        'npj Quantum Information': 'npj Quantum Inf.',
        'PRX Quantum': 'PRX Quantum',
        'Communications Physics': 'Commun. Phys.',
        'Scientific Reports': 'Sci. Rep.',
        'PLOS ONE': 'PLOS ONE',
        'eLife': 'eLife',

        # Additional common journals
        'New England Journal of Medicine': 'N. Engl. J. Med.',
        'The Lancet': 'Lancet',
        'British Medical Journal': 'BMJ',
        'Journal of Clinical Investigation': 'J. Clin. Invest.',
        'Proceedings of the Royal Society A': 'Proc. R. Soc. A',
        'Philosophical Transactions of the Royal Society A': 'Philos. Trans. R. Soc. A',
    }

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

    def __init__(self, timeout: int = 15, use_full_journal_name: bool = False):
        self.timeout = timeout
        self.use_full_journal_name = use_full_journal_name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BibExtractor/1.0 (Citation Management Tool)'
        })
        self.detected_journal = None

    def abbreviate_journal(self, journal_name: str) -> str:
        """Convert journal name to abbreviated form.

        Args:
            journal_name: Full journal name

        Returns:
            Abbreviated journal name if found in database, otherwise original name
        """
        if self.use_full_journal_name:
            return journal_name

        if not journal_name:
            return journal_name

        # Direct lookup
        if journal_name in self.JOURNAL_ABBREVIATIONS:
            return self.JOURNAL_ABBREVIATIONS[journal_name]

        # Case-insensitive lookup
        journal_lower = journal_name.lower()
        for full_name, abbrev in self.JOURNAL_ABBREVIATIONS.items():
            if full_name.lower() == journal_lower:
                return abbrev

        # Try partial match for common variations
        # Remove common suffixes like " (Edinburgh, Scotland)" or extra whitespace
        clean_name = journal_name.strip()
        clean_name = re.sub(r'\s*\([^)]+\)\s*$', '', clean_name)

        if clean_name in self.JOURNAL_ABBREVIATIONS:
            return self.JOURNAL_ABBREVIATIONS[clean_name]

        # If still no match, return original
        return journal_name

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

    def fetch_journal_impact_factor(self, issn: str, journal_name: str = '') -> Optional[Dict]:
        """Fetch journal impact metrics from multiple sources.

        Tries to get impact factor or alternative metrics:
        1. CiteScore (from Scopus/OpenAlex)
        2. SJR (SCImago Journal Rank)
        3. SNIP (Source Normalized Impact per Paper)
        4. h5-index (from Google Scholar, if available)

        Args:
            issn: Journal ISSN
            journal_name: Journal name for fallback search

        Returns:
            Dict with impact metrics or None if unavailable
        """
        metrics = {}

        # Try OpenAlex for journal metrics
        try:
            if issn:
                # OpenAlex uses ISSN format with hyphen
                url = f'https://api.openalex.org/sources/issn:{issn}'
                headers = {'User-Agent': 'BibExtractor/1.0 (mailto:research@example.com)'}
                response = self.session.get(url, headers=headers, timeout=self.timeout)

                if response.status_code == 200:
                    data = response.json()
                    # Get available metrics
                    if 'works_count' in data:
                        metrics['works_count'] = data['works_count']
                    if 'cited_by_count' in data:
                        metrics['cited_by_count'] = data['cited_by_count']
                    if 'summary_stats' in data:
                        stats = data['summary_stats']
                        if 'h_index' in stats:
                            metrics['h_index'] = stats['h_index']
                        if 'i10_index' in stats:
                            metrics['i10_index'] = stats['i10_index']
                        if '2yr_mean_citedness' in stats:
                            metrics['2yr_impact'] = round(stats['2yr_mean_citedness'], 2)
                    if metrics:
                        print(f'  Journal metrics (OpenAlex): Found for {issn}', file=sys.stderr)
                        return metrics
        except Exception as e:
            print(f'  OpenAlex lookup failed: {e}', file=sys.stderr)

        # Try Semantic Scholar for journal info (if no metrics yet)
        try:
            # Search for venue by name
            if journal_name:
                url = 'https://api.semanticscholar.org/graph/v1/venue/search'
                params = {'query': journal_name, 'limit': 1}
                response = self.session.get(url, params=params, timeout=self.timeout)

                if response.status_code == 200:
                    data = response.json()
                    venues = data.get('data', [])
                    if venues:
                        venue = venues[0]
                        if 'hIndex' in venue:
                            metrics['h_index'] = venue['hIndex']
                        if 'citationCount' in venue:
                            metrics['venue_citations'] = venue['citationCount']
                        if metrics:
                            print(f'  Journal metrics (Semantic Scholar): Found for {journal_name[:30]}', file=sys.stderr)
                            return metrics
        except Exception as e:
            print(f'  Semantic Scholar lookup failed: {e}', file=sys.stderr)

        # Return None if no metrics found
        if not metrics:
            print(f'  Journal metrics: Not available', file=sys.stderr)
            return None

        return metrics

    def _format_impact_factor_field(self, metrics: Dict, journal_name: str = '') -> Optional[str]:
        """Format impact metrics as a BibTeX-friendly string.

        Args:
            metrics: Dict of metric name -> value
            journal_name: Journal name for context

        Returns:
            Formatted string or None
        """
        if not metrics:
            return None

        parts = []
        if 'h_index' in metrics:
            parts.append(f"h-index: {metrics['h_index']}")
        if 'i10_index' in metrics:
            parts.append(f"i10: {metrics['i10_index']}")
        if 'works_count' in metrics:
            parts.append(f"papers: {metrics['works_count']:,}")
        if 'cited_by_count' in metrics:
            parts.append(f"citations: {metrics['cited_by_count']:,}")
        if 'venue_citations' in metrics:
            parts.append(f"venue_citations: {metrics['venue_citations']:,}")

        if parts:
            return ' | '.join(parts)
        return None

    def fetch_abstract_from_crossref(self, doi: str) -> Optional[str]:
        """Fetch abstract from CrossRef API.

        Note: Not all CrossRef entries have abstracts.

        Returns:
            Abstract text or None if unavailable
        """
        try:
            url = f'https://api.crossref.org/works/{doi}'
            headers = {'User-Agent': 'BibExtractor/1.0'}
            response = self.session.get(url, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                abstract = data.get('message', {}).get('abstract')
                if abstract:
                    # Clean up JATS tags if present
                    abstract = re.sub(r'</?jats:[^>]+>', '', abstract)
                    abstract = re.sub(r'</?(sec|title|p)>', '', abstract)
                    abstract = abstract.strip()
                    print(f'  Abstract (CrossRef): Found ({len(abstract)} chars)', file=sys.stderr)
                    return abstract
        except Exception as e:
            pass

        return None

    def fetch_crossref_work_metadata(self, doi: str) -> Optional[Dict]:
        """Fetch structured CrossRef metadata for field backfilling."""
        try:
            url = f'https://api.crossref.org/works/{doi}'
            headers = {'User-Agent': 'BibExtractor/1.0'}
            response = self.session.get(url, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                return response.json().get('message', {})
        except Exception:
            pass

        return None

    def fetch_abstract_from_semantic_scholar(self, doi: str) -> Optional[str]:
        """Fetch abstract from Semantic Scholar API.

        Returns:
            Abstract text or None if unavailable
        """
        try:
            url = f'https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=abstract'
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                abstract = data.get('abstract')
                if abstract:
                    print(f'  Abstract (Semantic Scholar): Found ({len(abstract)} chars)', file=sys.stderr)
                    return abstract
        except Exception as e:
            pass

        return None

    def fetch_abstract_from_pubmed(self, pmid: str) -> Optional[str]:
        """Fetch abstract from PubMed API.

        Returns:
            Abstract text or None if unavailable
        """
        try:
            url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
            params = {
                'db': 'pubmed',
                'id': pmid,
                'retmode': 'xml'
            }
            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)

                # Find abstract element
                abstract_elem = root.find('.//Abstract')
                if abstract_elem is not None:
                    # Get all AbstractText elements
                    abstract_texts = []
                    for text_elem in abstract_elem.findall('.//AbstractText'):
                        label = text_elem.get('Label', '')
                        text = ''.join(text_elem.itertext())
                        if label:
                            abstract_texts.append(f'{label}: {text}')
                        else:
                            abstract_texts.append(text)

                    abstract = ' '.join(abstract_texts)
                    if abstract:
                        print(f'  Abstract (PubMed): Found ({len(abstract)} chars)', file=sys.stderr)
                        return abstract
        except Exception as e:
            pass

        return None

    def fetch_abstract_from_arxiv(self, arxiv_id: str) -> Optional[str]:
        """Fetch abstract from arXiv API.

        Returns:
            Abstract text or None if unavailable
        """
        try:
            url = f'http://export.arxiv.org/api/query?id_list={arxiv_id}'
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)

                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                summary = root.find('.//atom:summary', ns)
                if summary is not None and summary.text:
                    abstract = summary.text.strip()
                    print(f'  Abstract (arXiv): Found ({len(abstract)} chars)', file=sys.stderr)
                    return abstract
        except Exception as e:
            pass

        return None

    def extract_abstract(self, identifier: str, identifier_type: str = None) -> Optional[str]:
        """Extract abstract from multiple sources.

        Tries sources in order based on identifier type.

        Args:
            identifier: DOI, PMID, or arXiv ID
            identifier_type: 'doi', 'pmid', 'arxiv', or None for auto-detect

        Returns:
            Abstract text or None if unavailable
        """
        # Auto-detect identifier type if not specified
        if identifier_type is None:
            if identifier.isdigit():
                identifier_type = 'pmid'
            elif re.match(r'^\d{4}\.\d{4,5}$', identifier):
                identifier_type = 'arxiv'
            else:
                identifier_type = 'doi'

        # Try sources based on identifier type
        if identifier_type == 'pmid':
            # Try PubMed first for PMIDs
            abstract = self.fetch_abstract_from_pubmed(identifier)
            if abstract:
                return abstract

        elif identifier_type == 'arxiv':
            # Try arXiv for arXiv IDs
            abstract = self.fetch_abstract_from_arxiv(identifier)
            if abstract:
                return abstract

        # For DOIs or as fallback, try CrossRef then Semantic Scholar
        if identifier_type == 'doi':
            abstract = self.fetch_abstract_from_crossref(identifier)
            if abstract:
                return abstract

            abstract = self.fetch_abstract_from_semantic_scholar(identifier)
            if abstract:
                return abstract

        print(f'  Abstract: Not available', file=sys.stderr)
        return None

    def fetch_from_crossref(self, doi: str, fetch_abstract: bool = False) -> Optional[str]:
        """Fetch BibTeX from CrossRef API.

        Args:
            doi: The DOI to fetch
            fetch_abstract: If True, also fetch abstract from available sources

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

                crossref_metadata = self.fetch_crossref_work_metadata(doi)

                # Fetch citation count
                citation_count = self.fetch_citation_count(doi)

                # Optionally fetch abstract
                abstract = None
                if fetch_abstract:
                    abstract = self.extract_abstract(doi, 'doi')

                # Fetch journal impact factor
                impact_factor = None
                # Extract journal info from bibtex for impact factor lookup
                # Note: CrossRef uses uppercase field names (ISSN, DOI, etc.)
                journal_match = re.search(r'journal\s*=\s*\{([^}]+)\}', bibtex, re.IGNORECASE)
                issn_match = re.search(r'issn\s*=\s*\{([^}]+)\}', bibtex, re.IGNORECASE)
                journal_name = journal_match.group(1) if journal_match else ''
                issn = issn_match.group(1) if issn_match else ''

                if journal_name or issn:
                    metrics = self.fetch_journal_impact_factor(issn, journal_name)
                    if metrics:
                        impact_factor = self._format_impact_factor_field(metrics, journal_name)

                # Post-process to fix common issues and add citations/abstract/impact_factor
                bibtex = self._fix_bibtex_fields(
                    bibtex,
                    doi,
                    citation_count,
                    abstract,
                    impact_factor,
                    crossref_metadata=crossref_metadata,
                )
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

    def _fix_bibtex_fields(self, bibtex: str, doi: str, citation_count: Optional[int] = None,
                           abstract: Optional[str] = None, impact_factor: Optional[str] = None,
                           crossref_metadata: Optional[Dict] = None) -> str:
        """Fix and clean up BibTeX fields for consistent formatting.

        This method:
        1. Detects the journal type
        2. Applies journal-specific fixes if needed
        3. Adds citation count if available
        4. Adds abstract if available
        5. Adds impact factor if available
        6. Formats output consistently
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

        for field_name in list(fields.keys()):
            fields[field_name] = self._clean_bibtex_text(fields[field_name])

        fields = self._backfill_fields_from_crossref(fields, crossref_metadata)

        # Apply journal-specific fixes
        fields = self._apply_journal_specific_fixes(fields, self.detected_journal)

        # Apply journal abbreviation (default) or keep full name
        if 'journal' in fields:
            fields['journal'] = self.abbreviate_journal(fields['journal'])
        if 'booktitle' in fields:
            # Conference proceedings might also benefit from abbreviation
            fields['booktitle'] = self.abbreviate_journal(fields['booktitle'])

        # Add citation count if available
        if citation_count is not None:
            fields['citations'] = str(citation_count)

        # Add abstract if available
        if abstract is not None:
            fields['abstract'] = abstract

        # Add impact factor if available
        if impact_factor is not None:
            fields['impact_factor'] = impact_factor

        # Build clean BibTeX entry with consistent field order
        field_order = [
            'author', 'title', 'journal', 'booktitle', 'volume', 'number', 'pages',
            'year', 'month', 'citations', 'impact_factor', 'doi', 'url', 'issn', 'isbn', 'publisher',
            'eprint', 'archive', 'pmid', 'abstract', 'note', 'annotation'
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

    def _backfill_fields_from_crossref(self, fields: Dict, metadata: Optional[Dict]) -> Dict:
        """Backfill missing BibTeX fields from structured CrossRef metadata."""
        if not metadata:
            return fields

        def as_text(value):
            if value is None:
                return None
            return self._clean_bibtex_text(str(value))

        if not fields.get('volume') and metadata.get('volume'):
            fields['volume'] = as_text(metadata.get('volume'))

        if not fields.get('number') and metadata.get('issue'):
            fields['number'] = as_text(metadata.get('issue'))

        if not fields.get('pages'):
            page_value = metadata.get('page')
            article_number = (
                metadata.get('article-number')
                or metadata.get('article_number')
                or metadata.get('article')
            )
            chosen = page_value or article_number
            if chosen:
                fields['pages'] = as_text(chosen)

        return fields

    def _clean_bibtex_text(self, value: str) -> str:
        """Normalize text extracted from upstream metadata providers."""
        if not value:
            return value

        value = value.replace('\n', ' ')
        value = re.sub(r'<mml:mi>\s*He\s*</mml:mi>.*?<mml:mn>\s*3\s*</mml:mn>', '3He', value, flags=re.I | re.S)
        value = re.sub(r'<[^>]+>', ' ', value)
        value = value.replace('$_2$', '2')
        value = value.replace('$_', '')
        value = re.sub(r'\s+', ' ', value).strip()
        value = value.replace(' andV-I', ' and V-I')
        value = value.replace('V-Icharacteristics', 'V-I characteristics')
        value = value.replace('NbSe 2', 'NbSe2')
        return value

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

    def generate_inline_citation(self, bibtex: str, style: str = 'journal') -> str:
        """Generate inline citation from BibTeX entry.

        Args:
            bibtex: BibTeX entry string
            style: Citation style - 'journal', 'author', 'numbered', or 'nature'
                - 'journal': Journal, Volume, Pages, (Year) - e.g., Phys. Rev. B, 109, 144303, (2024)
                - 'author': Author (Year) Journal, Volume, Pages - e.g., Smith et al. (2024) Nature, 123, 456
                - 'numbered': [Number] - e.g., [1]
                - 'nature': Nature style - e.g., Smith, J. et al. Nature 123, 456 (2024)

        Returns:
            Formatted inline citation string
        """
        # Extract fields
        fields = {}
        field_pattern = r'(\w+)\s*=\s*\{([^}]+)\}'
        for match in re.finditer(field_pattern, bibtex):
            field_name = match.group(1).lower()
            field_value = match.group(2).strip()
            fields[field_name] = field_value

        # Get required fields
        journal = fields.get('journal', '')
        booktitle = fields.get('booktitle', '')
        venue = journal or booktitle
        volume = fields.get('volume', '')
        number = fields.get('number', '')
        pages = fields.get('pages', '')
        year = fields.get('year', '')
        authors = fields.get('author', '')
        title = fields.get('title', '')
        doi = fields.get('doi', '')
        eprint = fields.get('eprint', '')
        archive_prefix = fields.get('archiveprefix', '')

        # Format authors
        first_author = ''
        if authors:
            author_list = authors.split(' and ')
            first = author_list[0]
            if ',' in first:
                first_author = first.split(',')[0].strip()
            else:
                first_author = first.split()[-1].strip() if first.split() else first

        if style == 'journal':
            # Format: Journal, Volume, Pages, (Year)
            parts = []
            if venue:
                # Use italic formatting for journal name
                parts.append(f'\\textit{{{venue}}}')
            elif archive_prefix and eprint:
                parts.append(f'{archive_prefix}:{eprint}')
            elif eprint:
                parts.append(eprint)
            if volume:
                parts.append(volume)
            if pages:
                # Clean up page format for inline citation
                clean_pages = pages.replace('--', '-')
                parts.append(clean_pages)

            # Build citation
            citation = ', '.join(parts)
            if year:
                if parts:
                    citation += f', ({year})'
                else:
                    citation = f'({year})'

            return citation

        elif style == 'author':
            # Format: Author et al. (Year) Journal, Volume, Pages
            parts = []
            if first_author:
                if len(authors.split(' and ')) > 1:
                    parts.append(f'{first_author} et al.')
                else:
                    parts.append(first_author)
            if year:
                parts.append(f'({year})')
            if venue:
                parts.append(f'\\textit{{{venue}}}')
            if volume:
                parts.append(volume)
            if pages:
                clean_pages = pages.replace('--', '-')
                parts.append(clean_pages)

            return ' '.join(parts)

        elif style == 'nature':
            # Format: Author, F. et al. Nature 123, 456 (2024)
            parts = []
            if authors:
                author_list = authors.split(' and ')
                first = author_list[0]
                if ',' in first:
                    last, first_name = first.split(',', 1)
                    # Get initials
                    initials = '. '.join(n[0] for n in first_name.strip().split() if n) + '.'
                    parts.append(f'{last.strip()}, {initials}')
                else:
                    parts.append(first)
                if len(author_list) > 1:
                    parts[-1] = parts[-1].rstrip('.') + ' et al.'

            if venue:
                parts.append(f'\\textit{{{venue}}}')

            if volume and pages:
                clean_pages = pages.replace('--', '-')
                parts.append(f'{volume}, {clean_pages}')
            elif volume:
                parts.append(volume)

            if year:
                parts.append(f'({year})')

            return ' '.join(parts)

        elif style == 'numbered':
            # Just return [cite_key] format
            key_match = re.match(r'@\w+\{([^,]+),', bibtex)
            if key_match:
                return f'\\cite{{{key_match.group(1)}}}'
            return ''

        elif style == 'apa':
            # APA format: Author, A. A., & Author, B. B. (Year). Title. Journal, Volume(Issue), Pages.
            parts = []
            if authors:
                author_list = authors.split(' and ')
                formatted_authors = []
                for auth in author_list:
                    if ',' in auth:
                        last, first = auth.split(',', 1)
                        initials = '. '.join(n[0] for n in first.strip().split() if n) + '.'
                        formatted_authors.append(f'{last.strip()}, {initials}')
                    else:
                        formatted_authors.append(auth)

                if len(formatted_authors) == 1:
                    parts.append(formatted_authors[0])
                elif len(formatted_authors) == 2:
                    parts.append(f'{formatted_authors[0]} & {formatted_authors[1]}')
                else:
                    parts.append(f'{formatted_authors[0]} et al.')

            if year:
                parts.append(f'({year})')

            if title:
                parts.append(title + '.')

            if venue:
                venue_part = f'\\textit{{{venue}}}'
                if volume:
                    venue_part += f', {volume}'
                    if number:
                        venue_part += f'({number})'
                parts.append(venue_part + '.')

            return ' '.join(parts)

        return ''

    def generate_latex_href(self, bibtex: str, style: str = 'journal') -> str:
        """Generate LaTeX \\href command for DOI/URL.

        Args:
            bibtex: BibTeX entry string
            style: Citation style (see generate_inline_citation)

        Returns:
            LaTeX \\href command with inline citation
        """
        fields = {}
        field_pattern = r'(\w+)\s*=\s*\{([^}]+)\}'
        for match in re.finditer(field_pattern, bibtex):
            field_name = match.group(1).lower()
            field_value = match.group(2).strip()
            fields[field_name] = field_value

        doi = fields.get('doi', '')
        url = fields.get('url', '')

        # Generate link URL
        link_url = f'https://doi.org/{doi}' if doi else url

        # Generate inline citation
        inline = self.generate_inline_citation(bibtex, style)

        if link_url and inline:
            return f'\\href{{{link_url}}}{{{inline}}}'

        return inline

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

    def fetch_from_pubmed(self, pmid: str, fetch_abstract: bool = False) -> Optional[str]:
        """Fetch metadata from PubMed and convert to BibTeX.

        Args:
            pmid: PubMed ID
            fetch_abstract: If True, also fetch abstract

        Returns:
            BibTeX string or None
        """
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
                bibtex = self._pubmed_to_bibtex(data, pmid)

                # Optionally fetch abstract
                if bibtex and fetch_abstract:
                    abstract = self.fetch_abstract_from_pubmed(pmid)
                    if abstract:
                        bibtex = self._add_abstract_to_bibtex(bibtex, abstract)

                return bibtex
            else:
                return None

        except Exception as e:
            print(f'  Warning: PubMed fetch failed: {e}', file=sys.stderr)
            return None

    def fetch_from_arxiv(self, arxiv_id: str, fetch_abstract: bool = False) -> Optional[str]:
        """Fetch metadata from arXiv and convert to BibTeX.

        Args:
            arxiv_id: arXiv identifier
            fetch_abstract: If True, also fetch abstract

        Returns:
            BibTeX string or None
        """
        # Use arXiv API with JSON format
        url = f'http://export.arxiv.org/api/query?id_list={arxiv_id}'

        try:
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == 200:
                bibtex = self._arxiv_to_bibtex(response.text, arxiv_id)

                # arXiv entries usually include abstract in the API response
                # which is handled in _arxiv_to_bibtex
                return bibtex
            else:
                print(f'  Warning: arXiv returned status {response.status_code}', file=sys.stderr)
                return self._fetch_from_arxiv_html(arxiv_id)

        except Exception as e:
            print(f'  Warning: arXiv fetch failed: {e}', file=sys.stderr)
            return self._fetch_from_arxiv_html(arxiv_id)

    def _fetch_from_arxiv_html(self, arxiv_id: str) -> Optional[str]:
        """Fallback HTML fetch for arXiv when the API is unavailable."""
        try:
            url = f'https://arxiv.org/abs/{arxiv_id}'
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return self._arxiv_html_to_bibtex(response.text, arxiv_id)
            print(f'  Warning: arXiv HTML returned status {response.status_code}', file=sys.stderr)
        except Exception as e:
            print(f'  Warning: arXiv HTML fetch failed: {e}', file=sys.stderr)
        return None

    def _arxiv_html_to_bibtex(self, html: str, arxiv_id: str) -> Optional[str]:
        """Convert arXiv HTML meta tags to BibTeX."""
        def meta_values(name: str) -> List[str]:
            pattern = (
                rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']|'
                rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(name)}["\']'
            )
            results = re.findall(pattern, html, flags=re.IGNORECASE)
            values = []
            for first, second in results:
                if first:
                    values.append(first)
                elif second:
                    values.append(second)
            return values

        titles = meta_values('citation_title')
        authors = meta_values('citation_author')
        dates = meta_values('citation_date')
        abstracts = meta_values('citation_abstract')

        title = titles[0].strip() if titles else ''
        year = ''
        if dates:
            year_match = re.match(r'(\d{4})', dates[0].strip())
            if year_match:
                year = year_match.group(1)

        authors_str = ' and '.join(authors) if authors else 'Unknown'
        bibtex = f'@misc{{{arxiv_id},\n'
        bibtex += f'  author    = {{{authors_str}}},\n'
        bibtex += f'  title     = {{{title}}},\n'
        if year:
            bibtex += f'  year      = {{{year}}},\n'
        bibtex += f'  eprint    = {{{arxiv_id}}},\n'
        bibtex += '  archivePrefix = {arXiv},\n'
        bibtex += f'  url       = {{https://arxiv.org/abs/{arxiv_id}}}'
        if abstracts:
            abstract = abstracts[0].strip().replace('{', '\\{').replace('}', '\\}')
            bibtex += f',\n  abstract  = {{{abstract}}}'
        bibtex += '\n}'
        return bibtex

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

            # Extract abstract (summary)
            summary_elem = entry.find('atom:summary', ns)
            abstract = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else None

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
            bibtex += f'  url       = {{https://arxiv.org/abs/{arxiv_id}}}'
            if abstract:
                bibtex += f',\n  abstract  = {{{abstract}}}'
            bibtex += '\n}'

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

    def extract_bibtex(self, identifier: str, fetch_abstract: bool = False) -> Optional[str]:
        """Extract BibTeX entry from identifier (DOI, URL, PMID, arXiv ID).

        Args:
            identifier: DOI, URL, PMID, or arXiv ID
            fetch_abstract: If True, also fetch abstract from available sources
        """
        identifier = identifier.strip()

        # Check if it's a URL
        if identifier.startswith(('http://', 'https://')):
            # Try to extract DOI from URL
            doi = self.extract_doi_from_url(identifier)
            if doi:
                print(f'  Extracted DOI: {doi}', file=sys.stderr)
                return self.fetch_from_crossref(doi, fetch_abstract=fetch_abstract)

            # Try arXiv
            arxiv_id = self.extract_arxiv_id_from_url(identifier)
            if arxiv_id:
                print(f'  Extracted arXiv ID: {arxiv_id}', file=sys.stderr)
                return self.fetch_from_arxiv(arxiv_id, fetch_abstract=fetch_abstract)

            # Try PubMed
            pmid = self.extract_pmid_from_url(identifier)
            if pmid:
                print(f'  Extracted PMID: {pmid}', file=sys.stderr)
                return self.fetch_from_pubmed(pmid, fetch_abstract=fetch_abstract)

            # Fallback: try treating URL as DOI
            if 'doi' in identifier.lower():
                doi = self.clean_doi(identifier)
                return self.fetch_from_crossref(doi, fetch_abstract=fetch_abstract)

            print(f'  Warning: Could not extract identifier from URL: {identifier}', file=sys.stderr)
            return None

        # Check if it's a PMID (numeric)
        if identifier.isdigit():
            return self.fetch_from_pubmed(identifier, fetch_abstract=fetch_abstract)

        # Check if it's an arXiv ID
        arxiv_match = re.match(r'^\d{4}\.\d{4,5}$', identifier)
        if arxiv_match:
            return self.fetch_from_arxiv(identifier, fetch_abstract=fetch_abstract)

        # Treat as DOI
        doi = self.clean_doi(identifier)
        return self.fetch_from_crossref(doi, fetch_abstract=fetch_abstract)

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
                matches = re.findall(r'@(\w+)\{([^,]+),', content)
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

        # Check existing file content for proper spacing
        file_exists = Path(bib_file).exists()
        needs_separator = False
        if file_exists:
            try:
                with open(bib_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                    if existing_content and not existing_content.endswith('\n\n'):
                        needs_separator = True
            except Exception:
                needs_separator = True

        # Write to file
        with open(bib_file, 'a', encoding='utf-8') as f:
            if needs_separator:
                f.write('\n\n')
            f.write(bibtex)

        return key

    def process_batch(self, identifiers: List[str], bib_file: str,
                    delay: float = 1.0, fetch_abstract: bool = False,
                    parallel: int = 1) -> tuple[int, int]:
        """Process multiple identifiers and append to BibTeX file.

        Args:
            identifiers: List of DOIs, URLs, PMIDs, or arXiv IDs
            bib_file: Output BibTeX file path
            delay: Delay between requests in seconds (per worker)
            fetch_abstract: If True, also fetch abstracts
            parallel: Number of parallel workers (default: 1, sequential)

        Returns:
            Tuple of (successful_count, failed_count)
        """
        # Create file if it doesn't exist
        Path(bib_file).touch(exist_ok=True)

        # Read existing keys
        existing_keys = self.read_existing_keys(bib_file)

        print(f'\nProcessing {len(identifiers)} identifier(s)...', file=sys.stderr)
        if parallel > 1:
            print(f'Using {parallel} parallel workers', file=sys.stderr)
        print(f'Output file: {bib_file}\n', file=sys.stderr)

        if parallel > 1 and len(identifiers) > 1:
            # Parallel processing
            return self._process_batch_parallel(
                identifiers, bib_file, existing_keys,
                delay, fetch_abstract, parallel
            )
        else:
            # Sequential processing (original behavior)
            return self._process_batch_sequential(
                identifiers, bib_file, existing_keys,
                delay, fetch_abstract
            )

    def _process_batch_sequential(self, identifiers: List[str], bib_file: str,
                                  existing_keys: set, delay: float,
                                  fetch_abstract: bool) -> tuple[int, int]:
        """Process identifiers sequentially."""
        successful = 0
        failed = 0

        for i, identifier in enumerate(identifiers, 1):
            print(f'[{i}/{len(identifiers)}] Processing: {identifier}', file=sys.stderr)

            bibtex = self.extract_bibtex(identifier, fetch_abstract=fetch_abstract)

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

        print(f'\nSummary: {successful}/{len(identifiers)} successful, {failed} failed', file=sys.stderr)
        return successful, failed

    def _process_batch_parallel(self, identifiers: List[str], bib_file: str,
                                existing_keys: set, delay: float,
                                fetch_abstract: bool, workers: int) -> tuple[int, int]:
        """Process identifiers in parallel using ThreadPoolExecutor."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading

        # Thread-safe lock for file writes
        write_lock = threading.Lock()
        # Thread-safe set for tracking keys
        keys_lock = threading.Lock()
        processed_keys = set(existing_keys)

        successful = 0
        failed = 0
        results = []

        def process_single(identifier: str, index: int) -> Tuple[int, str, Optional[str]]:
            """Process a single identifier. Returns (index, identifier, bibtex)."""
            # Add delay per worker to avoid rate limiting
            time.sleep(delay * (index % workers))

            try:
                bibtex = self.extract_bibtex(identifier, fetch_abstract=fetch_abstract)
                return (index, identifier, bibtex)
            except Exception as e:
                print(f'  Error processing {identifier}: {e}', file=sys.stderr)
                return (index, identifier, None)

        # Process in parallel
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(process_single, identifier, i): identifier
                for i, identifier in enumerate(identifiers)
            }

            for future in as_completed(futures):
                identifier = futures[future]
                try:
                    index, ident, bibtex = future.result()

                    if bibtex:
                        with write_lock:
                            key = self._generate_key_from_bibtex(bibtex, processed_keys)
                            with keys_lock:
                                if key in processed_keys:
                                    key = self._make_unique_key(key, processed_keys)
                                processed_keys.add(key)

                            # Replace placeholder key and append
                            bibtex = re.sub(r'(@\w+\s*\{)[^,]+,', f'\\1{key},', bibtex, count=1)

                            with open(bib_file, 'a', encoding='utf-8') as f:
                                f.write('\n\n' + bibtex)

                        successful += 1
                        print(f'[{index+1}/{len(identifiers)}] {identifier} -> SUCCESS: {key}', file=sys.stderr)
                    else:
                        failed += 1
                        print(f'[{index+1}/{len(identifiers)}] {identifier} -> FAILED', file=sys.stderr)

                except Exception as e:
                    failed += 1
                    print(f'  Exception: {e}', file=sys.stderr)

        print(f'\nSummary: {successful}/{len(identifiers)} successful, {failed} failed', file=sys.stderr)
        return successful, failed

    def _generate_key_from_bibtex(self, bibtex: str, existing_keys: set) -> str:
        """Generate citation key from BibTeX content."""
        return self.generate_citation_key(bibtex, existing_keys)

    def _make_unique_key(self, base_key: str, existing_keys: set) -> str:
        """Make a key unique by adding suffix."""
        for suffix in ['a', 'b', 'c', 'd', 'e', 'f']:
            new_key = base_key + suffix
            if new_key not in existing_keys:
                return new_key

        i = 1
        while f'{base_key}{i}' in existing_keys:
            i += 1
        return f'{base_key}{i}'


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

    parser.add_argument(
        '--full-journal-name',
        action='store_true',
        help='Use full journal names instead of abbreviations (default: abbreviated)'
    )

    parser.add_argument(
        '--abstract',
        action='store_true',
        help='Fetch and include abstract in BibTeX entry'
    )

    parser.add_argument(
        '--inline',
        action='store_true',
        help='Output inline citation format instead of BibTeX'
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
        help='Output LaTeX \\href command with DOI link for inline citations'
    )

    parser.add_argument(
        '--parallel',
        type=int,
        default=1,
        help='Number of parallel workers for batch processing (default: 1)'
    )

    args = parser.parse_args()

    # Create extractor
    extractor = BibExtractor(timeout=args.timeout, use_full_journal_name=args.full_journal_name)

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
    extractor = BibExtractor(timeout=args.timeout, use_full_journal_name=args.full_journal_name)

    # Process
    if args.print_only or args.inline:
        # Print to stdout only
        print(f'# Extracting {len(identifiers)} bibliography entry(ies)', file=sys.stderr)
        for i, identifier in enumerate(identifiers, 1):
            print(f'[{i}/{len(identifiers)}] {identifier}', file=sys.stderr)
            bibtex = extractor.extract_bibtex(identifier, fetch_abstract=args.abstract)
            if bibtex:
                print()
                if args.inline:
                    # Output inline citation format
                    if args.latex_href:
                        citation = extractor.generate_latex_href(bibtex, style=args.inline_style)
                    else:
                        citation = extractor.generate_inline_citation(bibtex, style=args.inline_style)
                    print(citation)
                else:
                    print(bibtex)
            else:
                print(f'  Failed to extract: {identifier}', file=sys.stderr)
            if i < len(identifiers):
                time.sleep(args.delay)
    else:
        # Append to file
        extractor.process_batch(
            identifiers, args.output,
            delay=args.delay,
            fetch_abstract=args.abstract,
            parallel=args.parallel
        )


if __name__ == '__main__':
    main()
