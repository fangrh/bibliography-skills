#!/usr/bin/env python3
"""
Bibliography Sync - Synchronize BibTeX library with online sources
Updates metadata, citation counts, and removes invalid entries
"""

import sys
import re
import argparse
import json
import time
import math
from typing import Optional, Dict, List, Tuple, Set
from pathlib import Path
from difflib import SequenceMatcher
from collections import Counter

try:
    import requests
except ImportError:
    print("Error: requests module not found. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

# Optional: scikit-learn for advanced similarity
SKLEARN_AVAILABLE = False
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    pass


class BibSync:
    """Synchronize BibTeX entries with online sources."""

    # Minimum similarity score for title matching (0-1)
    TITLE_MATCH_THRESHOLD = 0.75
    # Minimum combined score for accepting a match
    COMBINED_MATCH_THRESHOLD = 0.80

    def __init__(self, timeout: int = 15, delay: float = 1.0, use_full_journal_name: bool = False):
        self.timeout = timeout
        self.delay = delay
        self.use_full_journal_name = use_full_journal_name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BibSync/1.0 (Citation Management Tool)'
        })
        # Import extractor for fetching
        from bib_extractor import BibExtractor
        self.extractor = BibExtractor(timeout=timeout, use_full_journal_name=use_full_journal_name)

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

    def extract_doi_url(self, entry: Dict) -> Tuple[Optional[str], Optional[str]]:
        """Extract DOI and URL from entry."""
        fields = entry.get('fields', {})

        doi = fields.get('doi')
        url = fields.get('url')

        # Clean DOI
        if doi:
            doi = self.extractor.clean_doi(doi)

        return doi, url

    def sync_entry(self, entry: Dict, update_citations: bool = False) -> Dict:
        """Sync a single entry with online sources.

        Returns:
            Dict with keys:
            - status: 'updated', 'matched', 'unmatched', 'invalid', 'error'
            - entry: updated entry dict (if successful)
            - message: status message
        """
        fields = entry.get('fields', {})
        doi, url = self.extract_doi_url(entry)

        result = {
            'status': 'unmatched',
            'entry': entry,
            'message': ''
        }

        # Case 1: Has DOI or URL - fetch fresh metadata
        if doi or url:
            identifier = doi if doi else url
            print(f'  Syncing via {"DOI" if doi else "URL"}: {identifier}', file=sys.stderr)

            try:
                fresh_bibtex = self.extractor.extract_bibtex(identifier)

                if fresh_bibtex:
                    # Parse fresh entry
                    fresh_entry = self._parse_single_entry(fresh_bibtex)

                    if fresh_entry:
                        # Preserve original key
                        fresh_entry['key'] = entry['key']

                        # Merge with existing fields (fresh takes precedence)
                        merged_fields = {**fields, **fresh_entry['fields']}

                        # Optionally update citations
                        if update_citations and doi:
                            citation_count = self.extractor.fetch_citation_count(doi)
                            if citation_count is not None:
                                merged_fields['citations'] = str(citation_count)

                        fresh_entry['fields'] = merged_fields
                        result['status'] = 'updated'
                        result['entry'] = fresh_entry
                        result['message'] = f'Updated from {identifier}'
                        return result
                else:
                    # Check if DOI is invalid
                    result['status'] = 'invalid'
                    result['message'] = f'DOI/URL returned no data: {identifier}'
                    return result

            except Exception as e:
                result['status'] = 'error'
                result['message'] = f'Error syncing {identifier}: {e}'
                return result

        # Case 2: No DOI/URL - try to find by title
        title = fields.get('title', '')
        if not title:
            result['status'] = 'unmatched'
            result['message'] = 'No title, DOI, or URL found'
            return result

        print(f'  Searching by title: {title[:50]}...', file=sys.stderr)

        # Search for the paper
        match_result = self._search_and_match(title, fields)

        if match_result:
            fresh_entry, identifier = match_result

            # Preserve original key
            fresh_entry['key'] = entry['key']

            # Merge fields
            merged_fields = {**fields, **fresh_entry['fields']}

            # Add the found identifier
            if identifier.startswith('10.'):
                merged_fields['doi'] = identifier
            else:
                merged_fields['url'] = identifier

            fresh_entry['fields'] = merged_fields
            result['status'] = 'matched'
            result['entry'] = fresh_entry
            result['message'] = f'Found via title search: {identifier}'
            return result

        result['status'] = 'unmatched'
        result['message'] = f'No match found for title: {title[:50]}...'
        return result

    def _parse_single_entry(self, bibtex: str) -> Optional[Dict]:
        """Parse a single BibTeX entry string."""
        match = re.match(r'@(\w+)\s*\{([^,]+),\s*(.*)\}\s*$', bibtex, re.DOTALL)

        if not match:
            return None

        return {
            'type': match.group(1),
            'key': match.group(2),
            'fields': self._parse_fields(match.group(3)),
            'raw': bibtex
        }

    def _search_and_match(self, title: str, existing_fields: Dict) -> Optional[Tuple[Dict, str]]:
        """Search for paper by title and match against existing fields.

        Returns:
            Tuple of (matched_entry, identifier) or None
        """
        # Get existing author and year for matching
        existing_authors = existing_fields.get('author', '')
        existing_year = existing_fields.get('year', '')

        # Extract first author's last name
        first_author_last = ''
        if existing_authors:
            first_author = existing_authors.split(' and ')[0]
            if ',' in first_author:
                first_author_last = first_author.split(',')[0].strip()
            else:
                parts = first_author.split()
                if parts:
                    first_author_last = parts[-1].strip()

        # Search CrossRef
        try:
            search_url = 'https://api.crossref.org/works'
            params = {
                'query.title': title,
                'rows': 5
            }

            response = self.session.get(search_url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                items = data.get('message', {}).get('items', [])

                for item in items:
                    # Calculate match score
                    score = self._calculate_match_score(
                        item, title, first_author_last, existing_year
                    )

                    if score >= self.COMBINED_MATCH_THRESHOLD:
                        # Found a good match - fetch full BibTeX
                        doi = item.get('DOI')
                        if doi:
                            print(f'    Found match: {doi} (score: {score:.2f})', file=sys.stderr)
                            fresh_bibtex = self.extractor.fetch_from_crossref(doi)
                            if fresh_bibtex:
                                entry = self._parse_single_entry(fresh_bibtex)
                                if entry:
                                    return entry, doi

        except Exception as e:
            print(f'    CrossRef search error: {e}', file=sys.stderr)

        # Try arXiv if no match
        try:
            # Use arXiv API
            search_url = f'http://export.arxiv.org/api/query?search_query=ti:"{title}"&max_results=3'
            response = self.session.get(search_url, timeout=self.timeout)

            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)

                ns = {'atom': 'http://www.w3.org/2005/Atom'}

                for entry in root.findall('.//atom:entry', ns):
                    title_elem = entry.find('atom:title', ns)
                    if title_elem is not None:
                        found_title = title_elem.text

                        # Calculate match score
                        title_score = self._title_similarity(title, found_title)

                        if title_score >= self.TITLE_MATCH_THRESHOLD:
                            # Get arXiv ID from URL
                            id_elem = entry.find('atom:id', ns)
                            if id_elem is not None:
                                arxiv_url = id_elem.text
                                arxiv_id = arxiv_url.split('/abs/')[-1]

                                print(f'    Found arXiv match: {arxiv_id} (score: {title_score:.2f})', file=sys.stderr)
                                fresh_bibtex = self.extractor.fetch_from_arxiv(arxiv_id)
                                if fresh_bibtex:
                                    entry = self._parse_single_entry(fresh_bibtex)
                                    if entry:
                                        return entry, f'https://arxiv.org/abs/{arxiv_id}'

        except Exception as e:
            print(f'    arXiv search error: {e}', file=sys.stderr)

        return None

    def _calculate_match_score(self, item: Dict, title: str, author_last: str, year: str) -> float:
        """Calculate match score between search result and existing entry."""
        scores = []

        # Title similarity (weight: 0.5)
        found_title = item.get('title', [''])[0] if isinstance(item.get('title'), list) else item.get('title', '')
        title_score = self._title_similarity(title, found_title)
        scores.append(title_score * 0.5)

        # Author match (weight: 0.3)
        author_score = 0
        if author_last:
            authors = item.get('author', [])
            if authors:
                for author in authors:
                    found_last = author.get('family', '')
                    if found_last.lower() == author_last.lower():
                        author_score = 1.0
                        break
        scores.append(author_score * 0.3)

        # Year match (weight: 0.2)
        year_score = 0
        if year:
            published = item.get('published-print') or item.get('published-online') or {}
            found_year = published.get('date-parts', [[None]])[0]
            if found_year and str(found_year[0]) == year:
                year_score = 1.0
        scores.append(year_score * 0.2)

        return sum(scores)

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles."""
        # Normalize titles
        t1 = re.sub(r'[^\w\s]', '', title1.lower())
        t2 = re.sub(r'[^\w\s]', '', title2.lower())

        return SequenceMatcher(None, t1, t2).ratio()

    def validate_citation_support(self, entry: Dict, context_sentences: List[str]) -> Dict:
        """Validate if a citation supports its usage context.

        Uses keyword matching to check if the paper's abstract/note
        is relevant to the cited sentences.

        Args:
            entry: BibTeX entry dict
            context_sentences: List of sentences where this citation appears

        Returns:
            Dict with 'status' (supported/unsupported/unclear) and 'reason'
        """
        fields = entry.get('fields', {})
        abstract = fields.get('abstract', '')
        note = fields.get('note', '')
        title = fields.get('title', '')

        if not context_sentences:
            return {'status': 'unclear', 'reason': 'No context sentences provided'}

        # Combine available text for keyword extraction
        paper_text = f"{title} {abstract} {note}".lower()

        if not paper_text.strip():
            return {'status': 'unclear', 'reason': 'No paper metadata available for validation'}

        # Extract keywords from context sentences
        context_keywords = self._extract_keywords(' '.join(context_sentences))

        # Check how many context keywords appear in paper text
        matched_keywords = []
        unmatched_keywords = []

        for keyword in context_keywords:
            if keyword in paper_text:
                matched_keywords.append(keyword)
            else:
                unmatched_keywords.append(keyword)

        match_ratio = len(matched_keywords) / len(context_keywords) if context_keywords else 0

        if match_ratio >= 0.3:
            return {
                'status': 'supported',
                'reason': f'{match_ratio:.0%} keyword match ({len(matched_keywords)}/{len(context_keywords)})',
                'matched_keywords': matched_keywords[:10],
                'unmatched_keywords': unmatched_keywords[:5]
            }
        elif match_ratio >= 0.15:
            return {
                'status': 'unclear',
                'reason': f'{match_ratio:.0%} keyword match - partial support',
                'matched_keywords': matched_keywords[:10],
                'unmatched_keywords': unmatched_keywords[:5]
            }
        else:
            return {
                'status': 'unsupported',
                'reason': f'{match_ratio:.0%} keyword match - may need replacement',
                'matched_keywords': matched_keywords[:5],
                'unmatched_keywords': unmatched_keywords[:10]
            }

    def suggest_sentence_revision(self, entry: Dict, original_sentence: str) -> Optional[Dict]:
        """Suggest how to revise a sentence to better match the citation.

        When citation doesn't support the sentence, first try to suggest
        a revision that aligns with what the paper actually says.

        Args:
            entry: BibTeX entry dict with title, abstract, note fields
            original_sentence: The original sentence using this citation

        Returns:
            Dict with suggested revision and rationale, or None if not possible
        """
        fields = entry.get('fields', {})
        abstract = fields.get('abstract', '')
        note = fields.get('note', '')
        title = fields.get('title', '')

        if not (abstract or note):
            return None

        # Extract key topics from the paper
        paper_keywords = self._extract_keywords(f"{title} {abstract} {note}")

        # What the paper can support (from note/abstract)
        paper_capabilities = []
        if note:
            # Extract main contribution from note
            paper_capabilities.append(note)
        if abstract:
            # Get first sentence of abstract (usually main finding)
            first_sentence = abstract.split('.')[0] + '.'
            if len(first_sentence) > 50:
                paper_capabilities.append(first_sentence[:200] + '...')

        # Extract what the sentence claims
        sentence_keywords = self._extract_keywords(original_sentence)

        # Find what the paper has that the sentence doesn't use
        unused_paper_keywords = [k for k in paper_keywords[:10] if k not in sentence_keywords]

        # Generate suggestion
        if paper_capabilities:
            return {
                'can_revise': True,
                'original_sentence': original_sentence,
                'paper_main_topics': paper_keywords[:8],
                'unused_topics': unused_paper_keywords[:5],
                'suggested_revision': f"Consider revising to focus on: {', '.join(paper_keywords[:5])}",
                'paper_contribution': paper_capabilities[0] if paper_capabilities else None,
                'rationale': 'The sentence claims something not directly supported by this paper. Consider aligning with what the paper actually demonstrates.'
            }

        return None

    def validate_with_revision_suggestion(self, entry: Dict, context_sentences: List[str]) -> Dict:
        """Validate citation and provide actionable suggestions.

        Priority:
        1. If citation supports sentence → OK
        2. If not supported → Try to suggest sentence revision
        3. If revision not possible → Suggest replacement citation

        Args:
            entry: BibTeX entry dict
            context_sentences: List of sentences where this citation appears

        Returns:
            Comprehensive validation result with action suggestions
        """
        # First do basic validation
        validation = self.validate_citation_support(entry, context_sentences)

        result = {
            'original_key': entry.get('key'),
            'validation': validation,
            'action_required': validation['status'] == 'unsupported',
            'suggested_action': None,
            'revision_suggestions': [],
            'replacement_suggestions': []
        }

        # If supported or unclear, no action needed
        if validation['status'] != 'unsupported':
            result['suggested_action'] = 'keep'
            return result

        # Try to suggest sentence revisions first
        print(f'  Citation unsupported - trying to suggest sentence revision...', file=sys.stderr)

        all_suggestions = []
        for sentence in context_sentences[:3]:  # Limit to first 3 sentences
            suggestion = self.suggest_sentence_revision(entry, sentence)
            if suggestion:
                all_suggestions.append(suggestion)

        if all_suggestions:
            result['suggested_action'] = 'revise_sentence'
            result['revision_suggestions'] = all_suggestions
            print(f'  Suggested action: Revise sentence to match citation', file=sys.stderr)
            return result

        # If revision not possible, suggest replacement citation
        print(f'  Revision not possible - suggesting replacement citation...', file=sys.stderr)
        result['suggested_action'] = 'replace_citation'

        # Get original DOI to exclude from search
        fields = entry.get('fields', {})
        original_doi = fields.get('doi', '').lower()
        exclude_dois = {original_doi} if original_doi else set()

        # Search for replacements
        replacements = self.search_replacement_citations(
            context_sentences,
            exclude_dois=exclude_dois,
            max_results=5
        )
        result['replacement_suggestions'] = replacements

        return result

    def validate_multi_citation_sentence(self, entries: List[Dict], sentence: str) -> Dict:
        """Validate a sentence with multiple citations.

        Priority:
        1. Check each citation individually
        2. Keep supported citations, remove unsupported ones
        3. If NO citations remain supported → try sentence revision
        4. If revision not possible → search for replacement citations

        Args:
            entries: List of BibTeX entry dicts for citations in the sentence
            sentence: The sentence containing all citations

        Returns:
            Dict with validation results and suggested actions
        """
        print(f'\n  Validating multi-citation sentence ({len(entries)} citations)...', file=sys.stderr)

        result = {
            'sentence': sentence[:100] + '...' if len(sentence) > 100 else sentence,
            'total_citations': len(entries),
            'supported_citations': [],
            'unsupported_citations': [],
            'unclear_citations': [],
            'suggested_action': None,
            'revision_suggestions': [],
            'replacement_suggestions': []
        }

        # Step 1: Validate each citation individually
        for entry in entries:
            key = entry.get('key', 'unknown')
            validation = self.validate_citation_support(entry, [sentence])
            status = validation['status']

            citation_info = {
                'key': key,
                'validation': validation,
                'doi': entry.get('fields', {}).get('doi', '')
            }

            if status == 'supported':
                result['supported_citations'].append(citation_info)
                print(f'    ✓ {key}: {status} ({validation["reason"]})', file=sys.stderr)
            elif status == 'unclear':
                result['unclear_citations'].append(citation_info)
                print(f'    ? {key}: {status} ({validation["reason"]})', file=sys.stderr)
            else:
                result['unsupported_citations'].append(citation_info)
                print(f'    ✗ {key}: {status} ({validation["reason"]})', file=sys.stderr)

        # Step 2: Decide action based on results
        supported_count = len(result['supported_citations'])
        unclear_count = len(result['unclear_citations'])
        unsupported_count = len(result['unsupported_citations'])

        # Case A: All citations supported or unclear
        if unsupported_count == 0:
            result['suggested_action'] = 'keep_all'
            print(f'  → KEEP ALL: All citations are supported or unclear', file=sys.stderr)
            return result

        # Case B: Some supported, some unsupported → remove unsupported
        if supported_count > 0 or unclear_count > 0:
            result['suggested_action'] = 'remove_unsupported'
            result['citations_to_remove'] = [c['key'] for c in result['unsupported_citations']]
            result['citations_to_keep'] = [c['key'] for c in result['supported_citations'] + result['unclear_citations']]
            print(f'  → REMOVE UNSUPPORTED: Keep {len(result["citations_to_keep"])}, remove {len(result["citations_to_remove"])}', file=sys.stderr)
            return result

        # Case C: ALL citations unsupported → try sentence revision first
        print(f'  → ALL UNSUPPORTED: Trying sentence revision...', file=sys.stderr)

        # Try to suggest sentence revisions using any of the entries
        revision_suggestions = []
        for entry in entries:
            suggestion = self.suggest_sentence_revision(entry, sentence)
            if suggestion:
                suggestion['suggested_key'] = entry.get('key')
                revision_suggestions.append(suggestion)

        if revision_suggestions:
            result['suggested_action'] = 'revise_sentence'
            result['revision_suggestions'] = revision_suggestions
            print(f'  → SUGGEST REVISION: {len(revision_suggestions)} suggestions available', file=sys.stderr)
            return result

        # Case D: Revision not possible → search for replacement citations
        print(f'  → REVISION NOT POSSIBLE: Searching for replacements...', file=sys.stderr)
        result['suggested_action'] = 'replace_citations'

        # Collect all DOIs to exclude
        exclude_dois = set()
        for entry in entries:
            doi = entry.get('fields', {}).get('doi', '').lower()
            if doi:
                exclude_dois.add(doi)

        # Search for replacements
        replacements = self.search_replacement_citations(
            [sentence],
            exclude_dois=exclude_dois,
            max_results=len(entries) * 2  # Get more options
        )
        result['replacement_suggestions'] = replacements

        if replacements:
            print(f'  → FOUND {len(replacements)} replacement candidates', file=sys.stderr)
        else:
            print(f'  → NO replacements found - manual review needed', file=sys.stderr)
            result['suggested_action'] = 'manual_review'

        return result

    def validate_document_citations(self, entries_dict: Dict[str, Dict],
                                    citation_contexts: Dict[str, List[Tuple[str, str]]]) -> List[Dict]:
        """Validate all citations in a document.

        Args:
            entries_dict: Dict mapping citation keys to BibTeX entries
            citation_contexts: Dict mapping citation keys to list of (filename, sentence) tuples

        Returns:
            List of validation results for each unique sentence
        """
        results = []

        # Group citations by sentence (for multi-citation sentences)
        sentence_citations = {}  # sentence -> list of citation keys

        for cite_key, contexts in citation_contexts.items():
            for filename, sentence in contexts:
                sentence_key = sentence.strip()[:80]  # Use first 80 chars as key
                if sentence_key not in sentence_citations:
                    sentence_citations[sentence_key] = {
                        'sentence': sentence,
                        'filename': filename,
                        'citation_keys': []
                    }
                sentence_citations[sentence_key]['citation_keys'].append(cite_key)

        # Validate each unique sentence
        for sentence_key, info in sentence_citations.items():
            sentence = info['sentence']
            filename = info['filename']
            citation_keys = info['citation_keys']

            # Get entry objects for all citations in this sentence
            entries = []
            missing_keys = []
            for key in citation_keys:
                if key in entries_dict:
                    entries.append(entries_dict[key])
                else:
                    missing_keys.append(key)

            if missing_keys:
                print(f'  Warning: Citation keys not found in bib file: {missing_keys}', file=sys.stderr)

            if not entries:
                continue

            print(f'\n[{filename}] Sentence with {len(entries)} citation(s):', file=sys.stderr)
            print(f'  "{sentence[:80]}..."', file=sys.stderr)

            # Validate based on number of citations
            if len(entries) == 1:
                # Single citation - use standard validation
                validation_result = self.validate_with_revision_suggestion(entries[0], [sentence])
                validation_result['sentence'] = sentence[:100]
                validation_result['filename'] = filename
            else:
                # Multiple citations - use multi-citation validation
                validation_result = self.validate_multi_citation_sentence(entries, sentence)
                validation_result['filename'] = filename

            results.append(validation_result)

        return results

    def validate_citation_across_usages(self, entry: Dict, all_contexts: List[Tuple[str, str]],
                                        threshold: float = 0.15) -> Dict:
        """Validate a citation across ALL its usages in the document.

        A citation may be used in multiple sentences. We validate it across
        ALL contexts to determine its overall status.

        Args:
            entry: BibTeX entry dict
            all_contexts: List of (filename, sentence) tuples where this citation appears
            threshold: Minimum match ratio to consider "supported" (default: 0.15 = 15%)

        Returns:
            Dict with overall status and per-sentence results
        """
        key = entry.get('key', 'unknown')
        fields = entry.get('fields', {})
        title = fields.get('title', '')
        abstract = fields.get('abstract', '')
        note = fields.get('note', '')

        # Combine paper content for matching
        paper_text = f"{title} {abstract} {note}".lower()

        result = {
            'key': key,
            'title': title[:50] + '...' if len(title) > 50 else title,
            'total_usages': len(all_contexts),
            'supported_usages': [],
            'unsupported_usages': [],
            'unclear_usages': [],
            'overall_status': 'unknown',
            'sentences_to_remove_from': [],
            'sentences_to_keep_in': [],
            'suggested_action': None
        }

        if not paper_text.strip() or not all_contexts:
            result['overall_status'] = 'unclear'
            result['suggested_action'] = 'keep'  # Safe default
            return result

        # Validate each usage individually
        for filename, sentence in all_contexts:
            # Quick validation for this specific sentence
            sentence_keywords = self._extract_keywords(sentence)
            paper_keywords = self._extract_keywords(paper_text)

            matched = [k for k in sentence_keywords if k in paper_keywords]
            match_ratio = len(matched) / len(sentence_keywords) if sentence_keywords else 0

            usage_result = {
                'filename': filename,
                'sentence': sentence[:80] + '...' if len(sentence) > 80 else sentence,
                'match_ratio': match_ratio,
                'matched_keywords': matched[:5],
                'unmatched_keywords': [k for k in sentence_keywords if k not in paper_keywords][:5]
            }

            if match_ratio >= 0.30:
                result['supported_usages'].append(usage_result)
                result['sentences_to_keep_in'].append((filename, sentence[:50]))
            elif match_ratio >= threshold:
                result['unclear_usages'].append(usage_result)
                result['sentences_to_keep_in'].append((filename, sentence[:50]))
            else:
                result['unsupported_usages'].append(usage_result)
                result['sentences_to_remove_from'].append((filename, sentence[:50]))

        # Determine overall status
        supported_count = len(result['supported_usages'])
        unclear_count = len(result['unclear_usages'])
        unsupported_count = len(result['unsupported_usages'])
        total = result['total_usages']

        good_count = supported_count + unclear_count

        if unsupported_count == 0:
            # All usages are supported or unclear
            result['overall_status'] = 'supported'
            result['suggested_action'] = 'keep_everywhere'
            print(f'  ✓ {key}: Supported in all {total} usage(s)', file=sys.stderr)

        elif good_count > 0:
            # Some supported, some not - selective removal
            result['overall_status'] = 'partial'
            result['suggested_action'] = 'remove_from_unsupported_sentences'
            print(f'  ~ {key}: Supported in {good_count}/{total} usage(s) - remove from {unsupported_count}', file=sys.stderr)

        else:
            # All usages unsupported
            result['overall_status'] = 'unsupported'
            result['suggested_action'] = 'remove_entirely_or_replace'
            print(f'  ✗ {key}: Unsupported in all {total} usage(s)', file=sys.stderr)

        return result

    def validate_all_citations_comprehensive(self, entries_dict: Dict[str, Dict],
                                              citation_contexts: Dict[str, List[Tuple[str, str]]]) -> Dict:
        """Comprehensive validation considering both:
        1. A citation may be used in multiple sentences
        2. A sentence may contain multiple citations

        Args:
            entries_dict: Dict mapping citation keys to BibTeX entries
            citation_contexts: Dict mapping citation keys to list of (filename, sentence) tuples

        Returns:
            Comprehensive validation report
        """
        report = {
            'total_unique_citations': len(entries_dict),
            'total_citations_analyzed': 0,
            'citations_by_status': {
                'supported': [],
                'partial': [],
                'unsupported': []
            },
            'sentence_validations': [],
            'actions': {
                'keep_everywhere': [],
                'remove_from_unsupported_sentences': [],
                'remove_entirely': [],
                'need_replacement': []
            }
        }

        print('\n' + '=' * 60, file=sys.stderr)
        print('Citation Validation Report', file=sys.stderr)
        print('=' * 60, file=sys.stderr)

        # Step 1: Validate each citation across all its usages
        print('\n[Phase 1] Validating citations across all usages...', file=sys.stderr)
        citation_validations = {}

        for key, contexts in citation_contexts.items():
            if key not in entries_dict:
                print(f'  Warning: {key} not found in bibliography', file=sys.stderr)
                continue

            entry = entries_dict[key]
            validation = self.validate_citation_across_usages(entry, contexts)
            citation_validations[key] = validation
            report['total_citations_analyzed'] += 1

            # Categorize by status
            status = validation['overall_status']
            if status in report['citations_by_status']:
                report['citations_by_status'][status].append(key)

            # Categorize by action
            action = validation['suggested_action']
            if action == 'keep_everywhere':
                report['actions']['keep_everywhere'].append(key)
            elif action == 'remove_from_unsupported_sentences':
                report['actions']['remove_from_unsupported_sentences'].append(key)
            elif action == 'remove_entirely_or_replace':
                report['actions']['remove_entirely'].append(key)

        # Step 2: For sentences with multiple citations, check if removal would leave some
        print('\n[Phase 2] Analyzing multi-citation sentences...', file=sys.stderr)

        # Group by sentence
        sentence_citations = {}
        for key, contexts in citation_contexts.items():
            for filename, sentence in contexts:
                sent_key = f"{filename}:{sentence[:60]}"
                if sent_key not in sentence_citations:
                    sentence_citations[sent_key] = {
                        'filename': filename,
                        'sentence': sentence,
                        'citation_keys': []
                    }
                sentence_citations[sent_key]['citation_keys'].append(key)

        for sent_key, info in sentence_citations.items():
            keys = info['citation_keys']
            if len(keys) <= 1:
                continue  # Single citation, already handled

            # Check how many would remain after removal
            would_remain = []
            would_remove = []

            for key in keys:
                if key in citation_validations:
                    val = citation_validations[key]
                    sentence = info['sentence']

                    # Check if this specific usage is supported
                    is_supported_here = any(
                        s['sentence'].startswith(sentence[:50])
                        for s in val['supported_usages'] + val['unclear_usages']
                    )

                    if is_supported_here:
                        would_remain.append(key)
                    else:
                        would_remove.append(key)
                else:
                    would_remain.append(key)  # Unknown, keep by default

            if len(would_remove) > 0:
                sentence_val = {
                    'sentence': info['sentence'][:80],
                    'filename': info['filename'],
                    'total_citations': len(keys),
                    'would_remain': would_remain,
                    'would_remove': would_remove,
                    'action': 'remove_some' if would_remain else 'all_unsupported'
                }
                report['sentence_validations'].append(sentence_val)

                if would_remain:
                    print(f'  "{info["sentence"][:50]}..." - Remove {len(would_remove)}/{len(keys)}, keep {would_remain}', file=sys.stderr)
                else:
                    print(f'  "{info["sentence"][:50]}..." - ALL citations unsupported, needs revision/replacement', file=sys.stderr)
                    report['actions']['need_replacement'].append({
                        'sentence': info['sentence'],
                        'filename': info['filename'],
                        'removed_keys': would_remove
                    })

        # Step 3: Summary
        print('\n' + '=' * 60, file=sys.stderr)
        print('Validation Summary', file=sys.stderr)
        print('=' * 60, file=sys.stderr)
        print(f'  Fully supported: {len(report["citations_by_status"]["supported"])}', file=sys.stderr)
        print(f'  Partially supported: {len(report["citations_by_status"]["partial"])}', file=sys.stderr)
        print(f'  Unsupported: {len(report["citations_by_status"]["unsupported"])}', file=sys.stderr)
        print(f'  Sentences needing attention: {len(report["actions"]["need_replacement"])}', file=sys.stderr)

        return report

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'this', 'that', 'these', 'those', 'it', 'its', 'they', 'their', 'we',
            'our', 'you', 'your', 'he', 'she', 'his', 'her', 'as', 'which', 'who',
            'whom', 'where', 'when', 'why', 'how', 'all', 'each', 'every', 'both',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'not', 'only',
            'own', 'same', 'so', 'than', 'too', 'very', 'just', 'also', 'now',
            'here', 'there', 'then', 'once', 'if', 'because', 'while', 'although',
            'however', 'therefore', 'thus', 'hence', 'among', 'during', 'before',
            'after', 'above', 'below', 'between', 'into', 'through', 'during',
            'further', 'about', 'against', 'any', 'cite', 'cites', 'cited', 'citing',
            'ref', 'refs', 'reference', 'references', 'using', 'used', 'use', 'uses',
            'et', 'al', 'fig', 'figure', 'figures', 'table', 'tables', 'eq', 'equation',
            'section', 'sections', 'chapter', 'chapters', 'example', 'examples'
        }

        # Extract words (3+ characters, alphanumeric)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        # Filter out stop words and duplicates
        keywords = []
        seen = set()
        for word in words:
            if word not in stop_words and word not in seen:
                keywords.append(word)
                seen.add(word)

        return keywords

    # ============================================================
    # Advanced Semantic Matching Methods
    # ============================================================

    def compute_tfidf_similarity(self, text1: str, text2: str) -> float:
        """Compute TF-IDF based cosine similarity between two texts.

        Uses scikit-learn if available, otherwise falls back to manual calculation.

        Args:
            text1: First text (e.g., sentence with citation)
            text2: Second text (e.g., paper abstract/note)

        Returns:
            Similarity score between 0 and 1
        """
        if SKLEARN_AVAILABLE:
            try:
                vectorizer = TfidfVectorizer(
                    stop_words='english',
                    ngram_range=(1, 2),  # Unigrams and bigrams
                    max_features=1000
                )
                tfidf_matrix = vectorizer.fit_transform([text1, text2])
                similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                return float(similarity)
            except Exception:
                pass

        # Fallback: Manual TF-IDF calculation
        return self._manual_cosine_similarity(text1, text2)

    def _manual_cosine_similarity(self, text1: str, text2: str) -> float:
        """Manual cosine similarity calculation without sklearn.

        Uses TF (term frequency) with simple IDF approximation.
        """
        # Tokenize
        words1 = self._extract_keywords(text1)
        words2 = self._extract_keywords(text2)

        if not words1 or not words2:
            return 0.0

        # Build vocabulary
        vocab = set(words1) | set(words2)

        # Compute TF vectors
        tf1 = Counter(words1)
        tf2 = Counter(words2)

        # Normalize vectors
        vec1 = {word: tf1.get(word, 0) for word in vocab}
        vec2 = {word: tf2.get(word, 0) for word in vocab}

        # Compute cosine similarity
        dot_product = sum(vec1[w] * vec2[w] for w in vocab)
        norm1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in vec2.values()))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def compute_semantic_overlap(self, sentence: str, paper_content: str) -> Dict:
        """Compute multiple semantic overlap metrics.

        Combines several approaches for robust matching:
        1. TF-IDF cosine similarity
        2. Keyword overlap ratio
        3. Key phrase matching (n-grams)

        Args:
            sentence: The sentence to validate
            paper_content: Paper's title + abstract + note

        Returns:
            Dict with multiple similarity scores and overall assessment
        """
        # Normalize texts
        sentence_lower = sentence.lower()
        paper_lower = paper_content.lower()

        # 1. TF-IDF similarity
        tfidf_score = self.compute_tfidf_similarity(sentence_lower, paper_lower)

        # 2. Keyword overlap
        sent_keywords = set(self._extract_keywords(sentence_lower))
        paper_keywords = set(self._extract_keywords(paper_lower))

        if sent_keywords:
            overlap = len(sent_keywords & paper_keywords)
            keyword_score = overlap / len(sent_keywords)
        else:
            keyword_score = 0.0

        # 3. Key phrase matching (bigrams)
        def get_bigrams(text):
            words = self._extract_keywords(text)
            return set(zip(words[:-1], words[1:])) if len(words) > 1 else set()

        sent_bigrams = get_bigrams(sentence_lower)
        paper_bigrams = get_bigrams(paper_lower)

        if sent_bigrams:
            bigram_overlap = len(sent_bigrams & paper_bigrams)
            bigram_score = bigram_overlap / len(sent_bigrams)
        else:
            bigram_score = 0.0

        # 4. Combined score (weighted average)
        combined_score = (
            tfidf_score * 0.4 +      # TF-IDF most reliable
            keyword_score * 0.4 +     # Keyword overlap important
            bigram_score * 0.2        # Bigram for context
        )

        # Determine status
        if combined_score >= 0.25:
            status = 'supported'
        elif combined_score >= 0.12:
            status = 'unclear'
        else:
            status = 'unsupported'

        return {
            'tfidf_similarity': round(tfidf_score, 3),
            'keyword_overlap': round(keyword_score, 3),
            'bigram_overlap': round(bigram_score, 3),
            'combined_score': round(combined_score, 3),
            'status': status,
            'matched_keywords': list(sent_keywords & paper_keywords)[:10],
            'unmatched_keywords': list(sent_keywords - paper_keywords)[:10]
        }

    def validate_citation_semantic(self, entry: Dict, context_sentences: List[str],
                                   use_advanced: bool = True) -> Dict:
        """Semantic validation using advanced text matching.

        Args:
            entry: BibTeX entry dict
            context_sentences: Sentences where this citation appears
            use_advanced: Use advanced TF-IDF matching (default: True)

        Returns:
            Validation result with semantic scores
        """
        fields = entry.get('fields', {})
        title = fields.get('title', '')
        abstract = fields.get('abstract', '')
        note = fields.get('note', '')
        key = entry.get('key', 'unknown')

        # Combine paper content
        paper_content = f"{title} {abstract} {note}"

        if not paper_content.strip():
            return {
                'key': key,
                'status': 'unclear',
                'reason': 'No paper content available',
                'scores': {}
            }

        if not context_sentences:
            return {
                'key': key,
                'status': 'unclear',
                'reason': 'No context sentences provided',
                'scores': {}
            }

        # Compute semantic overlap for each sentence
        sentence_results = []
        best_score = 0

        for sentence in context_sentences:
            if use_advanced:
                result = self.compute_semantic_overlap(sentence, paper_content)
            else:
                # Simple keyword matching fallback
                keywords = self._extract_keywords(sentence)
                paper_keywords = self._extract_keywords(paper_content)
                matched = [k for k in keywords if k in paper_keywords]
                score = len(matched) / len(keywords) if keywords else 0

                if score >= 0.30:
                    status = 'supported'
                elif score >= 0.15:
                    status = 'unclear'
                else:
                    status = 'unsupported'

                result = {
                    'combined_score': round(score, 3),
                    'status': status,
                    'matched_keywords': matched[:10]
                }

            result['sentence'] = sentence[:80] + '...' if len(sentence) > 80 else sentence
            sentence_results.append(result)

            if result['combined_score'] > best_score:
                best_score = result['combined_score']

        # Aggregate across all sentences
        supported_count = sum(1 for r in sentence_results if r['status'] == 'supported')
        unsupported_count = sum(1 for r in sentence_results if r['status'] == 'unsupported')
        total = len(sentence_results)

        # Overall status based on best match across all sentences
        if supported_count > 0:
            overall_status = 'supported'
        elif unsupported_count == total:
            overall_status = 'unsupported'
        else:
            overall_status = 'unclear'

        return {
            'key': key,
            'status': overall_status,
            'best_score': round(best_score, 3),
            'supported_sentences': supported_count,
            'unsupported_sentences': unsupported_count,
            'total_sentences': total,
            'sentence_details': sentence_results,
            'matched_keywords': sentence_results[0].get('matched_keywords', []) if sentence_results else []
        }

    def batch_validate_citations(self, entries_dict: Dict[str, Dict],
                                  citation_contexts: Dict[str, List[Tuple[str, str]]],
                                  fast_mode: bool = False) -> List[Dict]:
        """Efficiently validate multiple citations with caching.

        Args:
            entries_dict: Dict mapping citation keys to entries
            citation_contexts: Dict mapping keys to (filename, sentence) tuples
            fast_mode: Use simpler matching for speed

        Returns:
            List of validation results, sorted by match quality
        """
        results = []

        # Pre-compute paper embeddings/content for efficiency
        paper_contents = {}
        for key, entry in entries_dict.items():
            fields = entry.get('fields', {})
            content = f"{fields.get('title', '')} {fields.get('abstract', '')} {fields.get('note', '')}"
            paper_contents[key] = content

        # Validate each citation
        for key, contexts in citation_contexts.items():
            if key not in entries_dict:
                continue

            sentences = [s for _, s in contexts]
            validation = self.validate_citation_semantic(
                entries_dict[key],
                sentences,
                use_advanced=not fast_mode
            )

            validation['usage_count'] = len(contexts)
            validation['files'] = list(set(f for f, _ in contexts))
            results.append(validation)

        # Sort by score (best first)
        results.sort(key=lambda x: x.get('best_score', 0), reverse=True)

        return results

    def search_replacement_citations(self, context_sentences: List[str],
                                     max_results: int = 5) -> List[Dict]:
        """Search for replacement citations based on context.

        Args:
            context_sentences: Sentences where citation is used
            max_results: Maximum number of results to return

        Returns:
            List of potential replacement entries
        """
        # Extract keywords from context
        keywords = self._extract_keywords(' '.join(context_sentences))

        if not keywords:
            return []

        # Search query from top keywords
        query = ' '.join(keywords[:6])

        print(f'  Searching for replacement: "{query[:50]}..."', file=sys.stderr)

        try:
            # Search CrossRef
            search_url = 'https://api.crossref.org/works'
            params = {
                'query': query,
                'rows': max_results
            }

            response = self.session.get(search_url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                items = data.get('message', {}).get('items', [])

                results = []
                for item in items:
                    doi = item.get('DOI')
                    title = item.get('title', [''])[0] if isinstance(item.get('title'), list) else item.get('title', '')

                    if doi and title:
                        results.append({
                            'doi': doi,
                            'title': title,
                            'year': (item.get('published-print') or item.get('published-online', {})).get('date-parts', [[None]])[0][0]
                        })

                return results

        except Exception as e:
            print(f'    Search error: {e}', file=sys.stderr)

        return []

    def search_replacement_citations(self, context_sentences: List[str],
                                     exclude_dois: Optional[Set[str]] = None,
                                     max_results: int = 10) -> List[Dict]:
        """Search for replacement citations based on context, excluding already-rejected DOIs.

        Args:
            context_sentences: Sentences where citation is used
            exclude_dois: Set of DOIs to exclude (already rejected or original)
            max_results: Maximum number of results to return

        Returns:
            List of potential replacement entries (excluding rejected DOIs)
        """
        if exclude_dois is None:
            exclude_dois = set()

        # Extract keywords from context
        keywords = self._extract_keywords(' '.join(context_sentences))

        if not keywords:
            return []

        # Search query from top keywords
        query = ' '.join(keywords[:6])

        print(f'  Searching for replacement: "{query[:50]}..."', file=sys.stderr)
        if exclude_dois:
            print(f'  Excluding {len(exclude_dois)} already-rejected DOI(s)', file=sys.stderr)

        try:
            # Search CrossRef with more results to account for exclusions
            search_url = 'https://api.crossref.org/works'
            params = {
                'query': query,
                'rows': max_results + len(exclude_dois)  # Get extra to account for exclusions
            }

            response = self.session.get(search_url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                items = data.get('message', {}).get('items', [])

                results = []
                for item in items:
                    doi = item.get('DOI', '').lower()
                    title = item.get('title', [''])[0] if isinstance(item.get('title'), list) else item.get('title', '')

                    # Skip excluded DOIs (case-insensitive comparison)
                    if doi and doi in {d.lower() for d in exclude_dois}:
                        print(f'    Skipping excluded DOI: {doi}', file=sys.stderr)
                        continue

                    if doi and title:
                        results.append({
                            'doi': doi,
                            'title': title,
                            'year': (item.get('published-print') or item.get('published-online', {})).get('date-parts', [[None]])[0][0]
                        })

                    if len(results) >= max_results:
                        break

                return results

        except Exception as e:
            print(f'    Search error: {e}', file=sys.stderr)

        return []

    def validate_and_suggest_replacement(self, entry: Dict, context_sentences: List[str],
                                        max_attempts: int = 3) -> Dict:
        """Validate citation and suggest replacement if unsupported.

        This method prevents infinite loops by:
        1. Tracking the original DOI
        2. Tracking all rejected replacement DOIs
        3. Excluding all tracked DOIs from future searches

        Args:
            entry: BibTeX entry dict
            context_sentences: Sentences where this citation appears
            max_attempts: Maximum number of replacement attempts

        Returns:
            Dict with validation result and optional replacement suggestions
        """
        fields = entry.get('fields', {})
        original_doi = fields.get('doi', '').lower()

        # First, validate the original citation
        validation = self.validate_citation_support(entry, context_sentences)

        result = {
            'original_key': entry.get('key'),
            'original_doi': original_doi,
            'validation': validation,
            'needs_replacement': validation['status'] == 'unsupported',
            'replacement_suggestions': [],
            'rejected_dois': set()
        }

        # If citation is supported or unclear, no replacement needed
        if validation['status'] != 'unsupported':
            return result

        # Track rejected DOIs (start with original)
        rejected_dois = {original_doi} if original_doi else set()

        # Search for replacements, excluding already-rejected DOIs
        suggestions = self.search_replacement_citations(
            context_sentences,
            exclude_dois=rejected_dois,
            max_results=max_attempts
        )

        # Filter out any suggestions that are the same as original (safety check)
        filtered_suggestions = []
        for suggestion in suggestions:
            suggestion_doi = suggestion.get('doi', '').lower()
            if suggestion_doi not in rejected_dois:
                filtered_suggestions.append(suggestion)
                # Add to rejected list to prevent future selection
                rejected_dois.add(suggestion_doi)

        result['replacement_suggestions'] = filtered_suggestions
        result['rejected_dois'] = rejected_dois

        return result

    def _entry_to_bibtex(self, entry: Dict) -> str:
        """Convert entry dict back to BibTeX string."""
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

    def sync_library(self, bib_file: str, dry_run: bool = False,
                     remove_invalid: bool = False, update_citations: bool = False,
                     validate_citations: bool = False, search_replacements: bool = False,
                     verbose: bool = False) -> Dict:
        """Synchronize entire BibTeX library.

        Args:
            bib_file: Path to BibTeX file
            dry_run: Preview changes without modifying
            remove_invalid: Remove entries that cannot be matched
            update_citations: Update citation counts from online sources
            validate_citations: Validate if citations support their usage context
            search_replacements: Search for replacements for unsupported citations
            verbose: Show detailed progress

        Returns:
            Statistics dict with counts
        """
        stats = {
            'total': 0,
            'updated': 0,
            'matched': 0,
            'unmatched': 0,
            'invalid': 0,
            'error': 0,
            'removed': 0,
            'unmatched_entries': [],
            'invalid_entries': [],
            'citation_validations': [],
            'replacement_suggestions': []
        }

        # Parse file
        entries, header = self.parse_bib_file(bib_file)
        stats['total'] = len(entries)

        print(f'\nSyncing {len(entries)} entries from {bib_file}', file=sys.stderr)
        print('=' * 50, file=sys.stderr)

        # Process each entry
        synced_entries = []

        for i, entry in enumerate(entries, 1):
            key = entry.get('key', 'unknown')
            print(f'\n[{i}/{len(entries)}] {key}', file=sys.stderr)

            result = self.sync_entry(entry, update_citations=update_citations)
            status = result['status']

            if verbose:
                print(f'  Status: {status} - {result["message"]}', file=sys.stderr)

            stats[status] = stats.get(status, 0) + 1

            if status == 'updated':
                synced_entries.append(result['entry'])

            elif status == 'matched':
                synced_entries.append(result['entry'])

            elif status == 'unmatched':
                if remove_invalid:
                    stats['removed'] += 1
                    stats['unmatched_entries'].append({
                        'key': key,
                        'title': entry.get('fields', {}).get('title', 'N/A'),
                        'reason': result['message']
                    })
                else:
                    synced_entries.append(entry)
                    stats['unmatched_entries'].append({
                        'key': key,
                        'title': entry.get('fields', {}).get('title', 'N/A'),
                        'reason': result['message']
                    })

            elif status == 'invalid':
                if remove_invalid:
                    stats['removed'] += 1
                else:
                    synced_entries.append(entry)
                stats['invalid_entries'].append({
                    'key': key,
                    'title': entry.get('fields', {}).get('title', 'N/A'),
                    'reason': result['message']
                })

            elif status == 'error':
                synced_entries.append(entry)  # Keep on error

            # Rate limiting
            time.sleep(self.delay)

        # Write output
        if not dry_run:
            # Create backup
            backup_file = bib_file + '.bak'
            try:
                import shutil
                shutil.copy2(bib_file, backup_file)
                print(f'\nBackup created: {backup_file}', file=sys.stderr)
            except Exception as e:
                print(f'Warning: Could not create backup: {e}', file=sys.stderr)

            # Write synced entries
            with open(bib_file, 'w', encoding='utf-8') as f:
                if header:
                    f.write(header)

                for entry in synced_entries:
                    f.write('\n\n')
                    f.write(self._entry_to_bibtex(entry))

                f.write('\n')

            print(f'\nUpdated: {bib_file}', file=sys.stderr)
        else:
            print(f'\nDry run - no changes made', file=sys.stderr)

        return stats

    def print_report(self, stats: Dict):
        """Print sync report."""
        print('\n' + '=' * 50, file=sys.stderr)
        print('Sync Report', file=sys.stderr)
        print('=' * 50, file=sys.stderr)
        print(f'Total entries: {stats["total"]}', file=sys.stderr)
        print(f'Updated (from DOI/URL): {stats.get("updated", 0)}', file=sys.stderr)
        print(f'Matched (via title search): {stats.get("matched", 0)}', file=sys.stderr)
        print(f'Unmatched: {stats.get("unmatched", 0)}', file=sys.stderr)
        print(f'Invalid: {stats.get("invalid", 0)}', file=sys.stderr)
        print(f'Errors: {stats.get("error", 0)}', file=sys.stderr)
        print(f'Removed: {stats.get("removed", 0)}', file=sys.stderr)

        if stats.get('unmatched_entries'):
            print('\nUnmatched entries:', file=sys.stderr)
            for entry in stats['unmatched_entries']:
                print(f'  - {entry["key"]}: {entry["title"][:40]}...', file=sys.stderr)

        if stats.get('invalid_entries'):
            print('\nInvalid entries:', file=sys.stderr)
            for entry in stats['invalid_entries']:
                print(f'  - {entry["key"]}: {entry["reason"]}', file=sys.stderr)

        # Print multi-citation validation results
        if stats.get('citation_validations'):
            print('\n' + '=' * 50, file=sys.stderr)
            print('Citation Validation Results:', file=sys.stderr)
            print('=' * 50, file=sys.stderr)

            for val in stats['citation_validations']:
                # Handle multi-citation validation
                if 'total_citations' in val:
                    self._print_multi_citation_result(val)
                else:
                    self._print_single_citation_result(val)

    def _print_multi_citation_result(self, val: Dict):
        """Print multi-citation validation result."""
        total = val.get('total_citations', 0)
        supported = len(val.get('supported_citations', []))
        unsupported = len(val.get('unsupported_citations', []))
        action = val.get('suggested_action', 'unknown')
        filename = val.get('filename', '')

        print(f'\n[{filename}] Multi-citation sentence ({total} citations):', file=sys.stderr)
        print(f'  ✓ Supported: {supported}, ✗ Unsupported: {unsupported}', file=sys.stderr)
        print(f'  Sentence: "{val.get("sentence", "")[:60]}..."', file=sys.stderr)

        # Print individual citation status
        if val.get('citations_to_keep'):
            print(f'  Citations to KEEP: {", ".join(val["citations_to_keep"])}', file=sys.stderr)
        if val.get('citations_to_remove'):
            print(f'  Citations to REMOVE: {", ".join(val["citations_to_remove"])}', file=sys.stderr)

        # Print action
        if action == 'keep_all':
            print(f'  ✓ Action: Keep all citations', file=sys.stderr)
        elif action == 'remove_unsupported':
            print(f'  → Action: Remove unsupported citations, keep others', file=sys.stderr)
        elif action == 'revise_sentence':
            print(f'  → Action: Revise sentence (all citations unsupported)', file=sys.stderr)
            for rev in val.get('revision_suggestions', [])[:2]:
                print(f'    Paper [{rev.get("suggested_key")}]: {rev.get("paper_contribution", "")[:60]}...', file=sys.stderr)
        elif action == 'replace_citations':
            print(f'  → Action: Search for replacement citations', file=sys.stderr)
            for rep in val.get('replacement_suggestions', [])[:3]:
                print(f'    - {rep.get("title", "N/A")[:50]}', file=sys.stderr)
        elif action == 'manual_review':
            print(f'  ⚠ Action: Manual review required (no replacements found)', file=sys.stderr)

        # ==================== LLM-Based Validation ====================

    def generate_llm_validation_prompt(self, entry: Dict, context_sentences: List[str]) -> str:
        """Generate a structured prompt for LLM-based citation validation.

        The user should pass this output to the agent (Claude) for evaluation.

        Args:
            entry: BibTeX entry dict with 'fields' containing paper metadata
            context_sentences: List of sentences where this citation appears

        Returns:
            JSON string prompt for LLM evaluation
        """
        fields = entry.get('fields', {})
        key = entry.get('key', 'unknown')

        prompt_data = {
            "task": "validate_citation",
            "citation_key": key,
            "paper_metadata": {
                "title": fields.get('title', ''),
                "abstract": fields.get('abstract', ''),
                "note": fields.get('note', ''),
                "authors": fields.get('author', ''),
                "year": fields.get('year', ''),
                "doi": fields.get('doi', '')
            },
            "context_sentences": context_sentences,
            "evaluation_criteria": {
                "match_score": "0-100: How well does the paper support the claims in the sentences?",
                "relevance": "Is the citation appropriate for this context?",
                "confidence": "How confident are you in this assessment?"
            },
            "output_format": {
                "match_score": "integer 0-100",
                "is_appropriate": "boolean",
                "reasoning": "brief explanation",
                "paper_contribution": "what this paper contributes (if matched)",
                "suggested_action": "keep | replace | revise_sentence"
            }
        }

        return json.dumps(prompt_data, indent=2)

    def load_analysis_results(self, analysis_file: str) -> Dict[str, Dict]:
        """Load citation analysis results from bib-analyze JSON output.

        Args:
            analysis_file: Path to JSON file from bib-analyze --format json

        Returns:
            Dict mapping citation keys to their analysis results
        """
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f'Warning: Analysis file not found: {analysis_file}', file=sys.stderr)
            return {}
        except json.JSONDecodeError:
            print(f'Warning: Invalid JSON in analysis file: {analysis_file}', file=sys.stderr)
            return {}

        # Build lookup by citation key and DOI
        results = {}
        for analysis in data.get('analyses', []):
            suggestions = analysis.get('suggestions', [])
            for suggestion in suggestions:
                doi = suggestion.get('doi', '')
                title = suggestion.get('title', '')
                authors = suggestion.get('authors', '')
                year = suggestion.get('year')

                # Create entry key from suggestions
                if doi:
                    results[doi] = {
                        'title': title,
                        'authors': authors,
                        'year': year,
                        'doi': doi,
                        'confidence': analysis.get('confidence', 0),
                        'needs_citation': analysis.get('needs_citation', False),
                        'source_sentence': analysis.get('sentence', '')[:100]
                    }

        print(f'Loaded {len(results)} analysis results from {analysis_file}', file=sys.stderr)
        return results

    def sync_with_analysis(self, bib_file: str, analysis_file: str,
                          dry_run: bool = False) -> Dict:
        """Sync library using bib-analyze results for scoring.

        Workflow:
        1. Load analysis results from bib-analyze
        2. For each suggested citation:
           - Check if exists in library (by DOI)
           - If exists: Update note with new context
           - If not exists: Add to library with score
        3. Generate report

        Args:
            bib_file: Path to BibTeX file
            analysis_file: Path to JSON file from bib-analyze
            dry_run: Preview changes without modifying

        Returns:
            Statistics dict
        """
        stats = {
            'total_analyzed': 0,
            'already_exists': 0,
            'added_new': 0,
            'notes_updated': 0,
            'skipped': 0,
            'results': []
        }

        # Load existing library
        entries, header = self.parse_bib_file(bib_file)
        existing_dois = {}
        for entry in entries:
            doi = entry.get('fields', {}).get('doi', '').lower()
            if doi:
                existing_dois[doi] = entry

        # Load analysis results
        analysis = self.load_analysis_results(analysis_file)
        stats['total_analyzed'] = len(analysis)

        print(f'\nSyncing with analysis results...', file=sys.stderr)
        print(f'Library has {len(existing_dois)} DOIs, {len(analysis)} suggestions', file=sys.stderr)

        for doi, result in analysis.items():
            title = result.get('title', 'Unknown')
            confidence = result.get('confidence', 0)

            print(f'\n  [{doi}] {title[:40]}... (confidence: {confidence:.0%})', file=sys.stderr)

            if doi.lower() in existing_dois:
                # Already exists - update note
                entry = existing_dois[doi.lower()]
                existing_note = entry.get('fields', {}).get('note', '')
                new_context = result.get('source_sentence', '')

                if new_context and new_context not in existing_note:
                    updated_note = f"{existing_note}\nAlso cited for: {new_context}".strip()
                    if not dry_run:
                        entry['fields']['note'] = updated_note
                    stats['notes_updated'] += 1
                    stats['results'].append({
                        'doi': doi,
                        'action': 'updated_note',
                        'title': title[:50]
                    })
                    print(f'    → Updated note (already in library)', file=sys.stderr)
                else:
                    stats['already_exists'] += 1
                    print(f'    → Already in library', file=sys.stderr)
            else:
                # New entry - add to library
                if confidence >= 0.5:  # Only add high-confidence suggestions
                    if not dry_run:
                        # Fetch BibTeX and add
                        bibtex = self.extractor.fetch_from_crossref(doi)
                        if bibtex:
                            # Add to file
                            key = self.extractor.generate_citation_key(bibtex, set())
                            # Append to bib file
                            with open(bib_file, 'a', encoding='utf-8') as f:
                                f.write(f'\n\n{bibtex}')
                            stats['added_new'] += 1
                            stats['results'].append({
                                'doi': doi,
                                'action': 'added',
                                'title': title[:50],
                                'key': key
                            })
                            print(f'    → Added to library (key: {key})', file=sys.stderr)
                        else:
                            stats['skipped'] += 1
                            print(f'    → Skipped (could not fetch BibTeX)', file=sys.stderr)
                    else:
                        stats['skipped'] += 1
                        print(f'    → Skipped (dry run)', file=sys.stderr)
                else:
                    stats['skipped'] += 1
                    print(f'    → Skipped (low confidence: {confidence:.0%})', file=sys.stderr)

        print('\n' + 'Sync Summary:', file=sys.stderr)
        print(f'    Analyzed: {stats["total_analyzed"]}', file=sys.stderr)
        print(f'    Already exists: {stats["already_exists"]}', file=sys.stderr)
        print(f'    Notes updated: {stats["notes_updated"]}', file=sys.stderr)
        print(f'    Added new: {stats["added_new"]}', file=sys.stderr)
        print(f'    Skipped: {stats["skipped"]}', file=sys.stderr)

        return stats

    def parse_llm_validation_response(self, response_text: str) -> Dict:
        """Parse LLM validation response.

        Args:
            response_text: Raw text response from LLM

        Returns:
            Parsed validation result dict
        """
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                return json.loads(json_match.group(0))

            # Parse structured text if no JSON found
            result = {}
            patterns = {
                'match_score': r'match_score["\']?\s*:\s*(\d+)',
                'is_appropriate': r'is_appropriate["\']?\s*:\s*(true|false)',
                'suggested_action': r'suggested_action["\']?\s*:\s*["\']?(\w+)["\']?'
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, response_text, re.IGNORECASE)
                if match:
                    value = match.group(1)
                    if key == 'match_score':
                        result[key] = int(value)
                    elif key == 'is_appropriate':
                        result[key] = value.lower() == 'true'
                    else:
                        result[key] = value

            return result
        except Exception as e:
            return {'error': str(e), 'raw_response': response_text}

    def check_citation_exists_in_library(self, bib_file: str, doi: str) -> Optional[Dict]:
        """Check if a citation with given DOI already exists in the library.

        Args:
            bib_file: Path to BibTeX file
            doi: DOI to search for

        Returns:
            Existing entry dict if found, None otherwise
        """
        entries, _ = self.parse_bib_file(bib_file)

        for entry in entries:
            fields = entry.get('fields', {})
            existing_doi = fields.get('doi', '').lower().strip()
            if existing_doi == doi.lower().strip():
                return entry

        return None

    def update_entry_note(self, entry: Dict, new_context: str, source_file: str) -> str:
        """Update entry's note field with new usage context.

        Args:
            entry: BibTeX entry dict
            new_context: The sentence/context where this citation is used
            source_file: The file where this usage was found

        Returns:
            Updated note string
        """
        fields = entry.get('fields', {})
        existing_note = fields.get('note', '')

        # Parse existing usage tracking
        usage_marker = f"[Used in {source_file}]"

        if existing_note:
            # Check if this file is already tracked
            if usage_marker not in existing_note:
                # Append new usage
                updated_note = f"{existing_note}; {usage_marker}: \"{new_context[:100]}...\""
            else:
                # Already tracked, update the context
                updated_note = existing_note
        else:
            # Create new note with usage tracking
            updated_note = f"{usage_marker}: \"{new_context[:100]}...\""

        return updated_note

    def smart_sync(self, bib_file: str, documents: List[str] = None,
                   use_llm: bool = False, verbose: bool = False) -> Dict:
        """Intelligent sync with LLM-based citation validation.

        Workflow:
        1. Parse documents to find citation contexts
        2. For each citation:
           a. If use_llm: Generate prompt for LLM evaluation
           b. Evaluate note-sentence matching
           c. Check if citation exists in library
           d. If exists: Update note with new usage context
           e. If not exists: Add new entry to library
        3. For inappropriate citations:
           a. Suggest revision or replacement

        Args:
            bib_file: Path to BibTeX file
            documents: List of document files to scan for citations
            use_llm: Use LLM-based validation (generates prompts)
            verbose: Show detailed progress

        Returns:
            Statistics dict with results
        """
        stats = {
            'total_entries': 0,
            'citations_validated': 0,
            'citations_appropriate': 0,
            'citations_inappropriate': 0,
            'citations_reused': 0,
            'citations_added': 0,
            'notes_updated': 0,
            'llm_prompts_generated': 0,
            'validation_results': [],
            'actions_taken': []
        }

        # Parse existing library
        entries, header = self.parse_bib_file(bib_file)
        stats['total_entries'] = len(entries)

        # Build DOI lookup map
        doi_to_entry = {}
        for entry in entries:
            doi = entry.get('fields', {}).get('doi', '').lower().strip()
            if doi:
                doi_to_entry[doi] = entry

        # Track citation contexts from documents
        citation_contexts = {}  # key -> [(filename, sentence), ...]

        if documents:
            from bib_citation_tracker import BibCitationTracker
            tracker = BibCitationTracker()

            for doc_file in documents:
                try:
                    doc_citations = tracker.extract_citations_from_file(doc_file)
                    for cite_key, contexts in doc_citations.items():
                        if cite_key not in citation_contexts:
                            citation_contexts[cite_key] = []
                        citation_contexts[cite_key].extend([
                            (doc_file, ctx['sentence']) for ctx in contexts
                        ])
                except Exception as e:
                    if verbose:
                        print(f'  Warning: Could not track citations in {doc_file}: {e}', file=sys.stderr)

        # Process each entry
        llm_prompts = []
        actions = []

        for entry in entries:
            key = entry.get('key', 'unknown')
            doi = entry.get('fields', {}).get('doi', '').lower().strip()

            # Get contexts for this citation
            contexts = citation_contexts.get(key, [])

            if not contexts:
                continue

            stats['citations_validated'] += 1
            sentences = [ctx[1] for ctx in contexts]

            if use_llm:
                # Generate LLM validation prompt
                prompt = self.generate_llm_validation_prompt(entry, sentences)
                llm_prompts.append({
                    'key': key,
                    'prompt': prompt
                })
                stats['llm_prompts_generated'] += 1

                if verbose:
                    print(f'\n[{key}] LLM Prompt Generated:', file=sys.stderr)
                    print(f'  Contexts: {len(contexts)} sentences', file=sys.stderr)
            else:
                # Use semantic validation
                result = self.validate_citation_semantic(entry, sentences)

                validation_result = {
                    'key': key,
                    'status': result.get('status', 'unknown'),
                    'score': result.get('best_score', 0),
                    'contexts_count': len(contexts)
                }

                stats['validation_results'].append(validation_result)

                if result.get('status') == 'supported':
                    stats['citations_appropriate'] += 1
                    actions.append({
                        'key': key,
                        'action': 'keep',
                        'reason': 'Citation is appropriate'
                    })
                else:
                    stats['citations_inappropriate'] += 1

                    # Search for replacement
                    suggestions = self.search_for_replacement_citations(
                        sentences[0] if sentences else '',
                        exclude_dois=[doi] if doi else []
                    )

                    if suggestions:
                        actions.append({
                            'key': key,
                            'action': 'replace',
                            'reason': 'Found replacement candidates',
                            'suggestions': suggestions[:3]
                        })
                    else:
                        actions.append({
                            'key': key,
                            'action': 'revise',
                            'reason': 'No replacement found, suggest revising sentence'
                        })

        stats['actions_taken'] = actions

        # Print summary
        print('\n' + '=' * 60, file=sys.stderr)
        print('Smart Sync Summary', file=sys.stderr)
        print('=' * 60, file=sys.stderr)
        print(f'Total entries: {stats["total_entries"]}', file=sys.stderr)
        print(f'Citations validated: {stats["citations_validated"]}', file=sys.stderr)
        print(f'Appropriate citations: {stats["citations_appropriate"]}', file=sys.stderr)
        print(f'Inappropriate citations: {stats["citations_inappropriate"]}', file=sys.stderr)

        if use_llm and llm_prompts:
            print('\n' + '-' * 60, file=sys.stderr)
            print('LLM Validation Prompts Generated:', file=sys.stderr)
            print('-' * 60, file=sys.stderr)
            for item in llm_prompts:
                print(f'\n[{item["key"]}]:', file=sys.stderr)
                print(item['prompt'])

        if actions:
            print('\n' + '-' * 60, file=sys.stderr)
            print('Recommended Actions:', file=sys.stderr)
            print('-' * 60, file=sys.stderr)
            for action in actions:
                print(f'\n[{action["key"]}]: {action["action"].upper()}', file=sys.stderr)
                print(f'  Reason: {action["reason"]}', file=sys.stderr)
                if action.get('suggestions'):
                    for sug in action['suggestions'][:2]:
                        print(f'  → Suggestion: {sug.get("title", "N/A")[:50]}...', file=sys.stderr)

        return stats


def _print_single_citation_result(self, val: Dict):
        """Print single-citation validation result."""
        key = val.get('original_key', 'unknown')
        action = val.get('suggested_action', 'unknown')
        validation = val.get('validation', {})

        print(f'\n[{key}]', file=sys.stderr)
        print(f'  Status: {validation.get("status", "unknown")}', file=sys.stderr)
        print(f'  Reason: {validation.get("reason", "N/A")}', file=sys.stderr)

        if action == 'revise_sentence':
            print(f'  SUGGESTED ACTION: Revise sentence', file=sys.stderr)
            for rev in val.get('revision_suggestions', []):
                print(f'    Original: "{rev.get("original_sentence", "")[:60]}..."', file=sys.stderr)
                print(f'    Suggestion: {rev.get("suggested_revision", "")}', file=sys.stderr)
                if rev.get('paper_contribution'):
                    print(f'    Paper contribution: {rev.get("paper_contribution")[:80]}...', file=sys.stderr)

        elif action == 'replace_citation':
            print(f'  SUGGESTED ACTION: Replace citation', file=sys.stderr)
            for rep in val.get('replacement_suggestions', []):
                print(f'    - {rep.get("title", "N/A")[:50]} (DOI: {rep.get("doi", "N/A")})', file=sys.stderr)

        elif action == 'keep':
            print(f'  ✓ Citation is well-supported', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='Synchronize BibTeX library with online sources.',
        epilog='Examples:\n'
                '  %(prog)s references.bib\n'
                '  %(prog)s references.bib --dry-run\n'
                '  %(prog)s my_papers.bib --remove-invalid --update-citations'
    )
    parser.formatter_class = argparse.RawDescriptionHelpFormatter

    parser.add_argument(
        'bib_file',
        nargs='?',
        default='references.bib',
        help='BibTeX file to sync (default: references.bib)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying file'
    )

    parser.add_argument(
        '--remove-invalid',
        action='store_true',
        help='Remove entries that cannot be matched'
    )

    parser.add_argument(
        '--update-citations',
        action='store_true',
        help='Update citation counts from online sources'
    )

    parser.add_argument(
        '--validate-citations',
        action='store_true',
        help='Validate if citations support their usage context (requires annotation field)'
    )

    parser.add_argument(
        '--search-replacements',
        action='store_true',
        help='Search for replacement citations for unsupported entries'
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
        '-v', '--verbose',
        action='store_true',
        help='Show detailed progress'
    )

    parser.add_argument(
        '--full-journal-name',
        action='store_true',
        help='Use full journal names instead of abbreviations'
    )

    parser.add_argument(
        '--analysis-file',
        help='JSON file from bib-analyze to use for scoring-based sync'
    )

    parser.add_argument(
        '--llm-validate',
        action='store_true',
        help='Generate LLM validation prompts for agent evaluation'
    )

    parser.add_argument(
        '--documents',
        nargs='+',
        help='Document files to scan for citation contexts (for --llm-validate)'
    )

    args = parser.parse_args()

    # Create syncer
    syncer = BibSync(timeout=args.timeout, delay=args.delay, use_full_journal_name=args.full_journal_name)

    # Check for analysis-based sync
    if args.analysis_file:
        print(f'Using analysis file: {args.analysis_file}', file=sys.stderr)
        stats = syncer.sync_with_analysis(
            args.bib_file,
            args.analysis_file,
            dry_run=args.dry_run
        )
        syncer.print_report({'total': stats['total_analyzed'], **stats})
        return

    # Check for LLM validation mode
    if args.llm_validate:
        if not args.documents:
            print('Error: --documents required for LLM validation', file=sys.stderr)
            sys.exit(1)
        stats = syncer.smart_sync(
            args.bib_file,
            list(args.documents),
            use_llm=True,
            dry_run=args.dry_run
        )
        syncer.print_report(stats)
        return

    # Run sync
    stats = syncer.sync_library(
        args.bib_file,
        dry_run=args.dry_run,
        remove_invalid=args.remove_invalid,
        update_citations=args.update_citations,
        validate_citations=args.validate_citations,
        search_replacements=args.search_replacements,
        verbose=args.verbose
    )

    # Print report
    syncer.print_report(stats)


if __name__ == '__main__':
    main()
