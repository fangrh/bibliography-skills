#!/usr/bin/env python3
"""
Bibliography Smart Search - Analyze text and find missing citations

Analyzes text to identify statements that need citations but don't have them,
then searches for relevant references.

Uses keyword analysis + pattern matching to determine citation needs.
"""

import sys
import re
import argparse
import json
from typing import Optional, Dict, List, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
import subprocess
import tempfile
import importlib.util

try:
    import requests
except ImportError:
    print("Error: requests module not found. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


@dataclass
class SentenceAnalysis:
    """Result of analyzing a sentence."""
    sentence: str
    needs_citation: bool
    confidence: float  # 0.0 to 1.0
    reason: str
    has_citation: bool
    existing_citations: List[str]
    suggested_search_terms: List[str]
    citation_suggestions: List[Dict]


class CitationNeedAnalyzer:
    """Analyze text to identify statements needing citations."""

    FIELD_PATTERN = r'(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}'
    NOTE_STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
        'this', 'that', 'these', 'those', 'it', 'its', 'they', 'their', 'we',
        'our', 'has', 'have', 'had', 'will', 'would', 'could', 'should',
        'can', 'may', 'might', 'must', 'shall', 'which', 'who', 'whom',
        'whose', 'what', 'where', 'when', 'why', 'how', 'as', 'than', 'so',
        'very', 'too', 'also', 'just', 'only', 'even', 'not', 'no', 'here',
        'paper', 'work', 'study'
    }
    CONTRIBUTION_PATTERNS = [
        (r'^(here\s+)?we\s+(demonstrate|report|show|present|develop|fabricate|realize|investigate|measure|observe|find)\b', 3.0),
        (r'^(in this work|in this paper|this work|this paper)\b', 2.5),
        (r'\bwe\s+(demonstrate|report|show|present|develop|fabricate|realize|investigate|measure|observe|find)\b', 2.5),
        (r'\b(the results|our experiments|our measurements)\s+(show|demonstrate|reveal)\b', 2.2),
    ]
    BACKGROUND_PATTERNS = [
        (r'\b(promising platform|attracted (?:great |considerable )?attention|growing interest)\b', -2.5),
        (r'\b(in recent years|recent advances|recent progress)\b', -2.0),
        (r'\b(is|are)\s+(important|crucial|essential|key)\s+for\b', -1.7),
        (r'\b(has|have)\s+been\s+(widely|extensively)\s+(studied|used|investigated)\b', -1.7),
    ]

    DOMAIN_ANCHOR_PATTERNS = [
        ('superconducting qubit', r'\bsuperconduct(?:ing)?\s+qubit[s]?\b'),
        ('mechanical phonon', r'\bmechanical\s+phonon[s]?\b'),
        ('piezoelectric coupling', r'\bpiezoelectric\s+coupling\b'),
        ('acoustic mode', r'\bacoustic\s+mode[s]?\b'),
        ('phonon', r'\bphonon[s]?\b'),
        ('piezoelectric', r'\bpiezoelectric\b'),
        ('qubit', r'\bqubit[s]?\b'),
        ('acoustic', r'\bacoustic\b'),
        ('mechanical resonator', r'\bmechanical\s+resonator[s]?\b'),
        ('spin defect', r'\bspin\s+defect[s]?\b'),
        ('nv center', r'\bnv\s+cent(?:er|re)[s]?\b'),
    ]

    # High-confidence indicators that a statement needs citation
    CITATION_NEEDED_PATTERNS = [
        # Numerical claims
        (r'\d+(\.\d+)?\s*%', 'percentage_claim'),
        (r'\d+(\.\d+)?\s*(times|fold|x)\s+(faster|slower|better|higher|lower)',
         'comparative_numerical'),
        (r'(achieves|reaches|attains)\s+\d+', 'achievement_claim'),
        (r'(accuracy|precision|recall|F1)\s*(of|:)\s*\d+', 'metric_claim'),

        # Method/technique references
        (r'(using|with|via|through)\s+[A-Z][a-z]+\d*', 'method_reference'),
        (r'(BERT|GPT|ResNet|VGG|Transformer|LSTM|CNN|RNN)\b', 'named_method'),
        (r'\b(our|we)\s+(propose|present|introduce|develop)\b', 'own_contribution'),

        # Factual claims
        (r'\b(shown|demonstrated|proven|established|found)\s+(that|to)\b', 'factual_claim'),
        (r'\b(according\s+to|based\s+on|as\s+reported\s+by)\b', 'source_reference'),
        (r'\b(previously|recently|earlier)\s+(shown|demonstrated|proven|reported)\b',
         'prior_work'),

        # Comparative claims
        (r'\b(outperforms|surpasses|exceeds|beats)\b', 'comparative_claim'),
        (r'\b(better|worse|higher|lower|faster|slower)\s+than\b', 'comparison'),
        (r'\b(state-of-the-art|SOTA|best|leading)\b', 'sota_claim'),

        # Research findings
        (r'\b(discovered|revealed|identified|observed|measured)\s+(that|a|the)\b',
         'finding_claim'),
        (r'\b(suggests|indicates|implies|shows)\s+that\b', 'implication_claim'),
        (r'\b(the\s+results|our\s+experiments|the\s+study)\s+(show|demonstrate|reveal)\b',
         'result_claim'),

        # Technical specifications
        (r'\b(p-value|confidence\s+interval|statistically\s+significant)\b', 'statistical'),
        (r'\b(nanometer|micrometer|millimeter|GHz|MHz|Tesla|Kelvin)\b', 'measurement'),
    ]

    # Common knowledge patterns (usually don't need citation)
    COMMON_KNOWLEDGE_PATTERNS = [
        (r'\b(is|are)\s+(a|an|the)\s+(common|well-known|standard|basic)\b', 'common_knowledge'),
        (r'\b(has|have)\s+been\s+(widely|extensively)\s+(used|studied|adopted)\b', 'established_field'),
        (r'\b(many|several|numerous)\s+(studies|works|papers)\s+have\b', 'general_reference'),
        (r'\b(it|this|these)\s+(is|are)\s+(known|clear|obvious|evident)\b', 'obvious_fact'),
    ]

    # Citation detection patterns
    CITATION_PATTERNS = [
        r'\\cite[pt]?\{([^}]+)\}',  # LaTeX \cite{...}
        r'\\cite[pt]?\*\{([^}]+)\}',  # LaTeX \cite*{...}
        r'\\citeal?p?\{([^}]+)\}',  # LaTeX \citealp{...}
        r'\\textcite\{([^}]+)\}',  # LaTeX \textcite{...}
        r'\\parencite\{([^}]+)\}',  # LaTeX \parencite{...}
        r'\\autocite\{([^}]+)\}',  # LaTeX \autocite{...}
        r'@[a-zA-Z][a-zA-Z0-9:_-]+',  # Pandoc-style @citation
        r'\[([^\]]*,?\s*\d{4}[a-z]?,?\s*[^\]]*)\]',  # [Author, Year]
        r'\([A-Z][a-z]+\s+et\s+al\.?,?\s*\d{4}[a-z]?\)',  # (Author et al., Year)
        r'\([A-Z][a-z]+\s+and\s+[A-Z][a-z]+,?\s*\d{4}[a-z]?\)',  # (Author and Author, Year)
    ]

    def __init__(self, use_full_journal_name: bool = False):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BibSmartSearch/1.0 (mailto:research@example.com)'
        })
        self.extractor_module = None
        self.use_full_journal_name = use_full_journal_name

    def _openalex_abstract_to_text(self, inverted_index: Optional[Dict]) -> str:
        """Convert an OpenAlex inverted abstract index to plain text."""
        if not inverted_index:
            return ''

        positions = []
        for word, indexes in inverted_index.items():
            for index in indexes:
                positions.append((index, word))

        positions.sort(key=lambda item: item[0])
        return ' '.join(word for _, word in positions)

    def analyze_sentence(self, sentence: str) -> SentenceAnalysis:
        """Analyze a single sentence for citation needs.

        Args:
            sentence: The sentence to analyze

        Returns:
            SentenceAnalysis with recommendation
        """
        # Check for existing citations
        existing_citations = self._find_existing_citations(sentence)
        has_citation = len(existing_citations) > 0

        # Calculate citation need score
        need_score = 0.0
        matched_patterns = []

        # Check citation-needed patterns
        for pattern, pattern_type in self.CITATION_NEEDED_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                need_score += 0.25
                matched_patterns.append(pattern_type)

        # Check common knowledge patterns (reduce need)
        for pattern, pattern_type in self.COMMON_KNOWLEDGE_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                need_score -= 0.15
                matched_patterns.append(f"reduced:{pattern_type}")

        # Additional heuristics
        word_count = len(sentence.split())

        # Long sentences with claims often need citations
        if word_count > 15 and need_score > 0:
            need_score += 0.1

        # Sentences with technical terms
        technical_terms = re.findall(r'\b[A-Z][a-z]+(?:ing|tion|ment|ness|ity)\b', sentence)
        if technical_terms:
            need_score += 0.1 * min(len(technical_terms), 3)

        # Normalize score to [0, 1]
        need_score = max(0.0, min(1.0, need_score))

        # Determine if citation needed
        needs_citation = need_score >= 0.3 and not has_citation

        # Generate reason
        if has_citation:
            reason = "Already has citation"
        elif needs_citation:
            reason = f"Citation recommended: {', '.join(matched_patterns[:3])}"
        else:
            reason = "Common knowledge or opinion statement"

        # Generate search terms if needed
        search_terms = []
        if needs_citation:
            search_terms = self._extract_search_terms(sentence)

        return SentenceAnalysis(
            sentence=sentence,
            needs_citation=needs_citation,
            confidence=need_score,
            reason=reason,
            has_citation=has_citation,
            existing_citations=existing_citations,
            suggested_search_terms=search_terms,
            citation_suggestions=[]
        )

    def extract_quantitative_claim(self, sentence: str) -> Optional[Dict]:
        """Extract numeric values and nearby units from a sentence."""
        matches = list(re.finditer(r'(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>%|[A-Za-zμµ]+)?', sentence))

        values = []
        units = []
        snippets = []

        for match in matches:
            value = match.group('value')
            unit = (match.group('unit') or '').strip()
            if not value:
                continue

            start = max(0, match.start() - 18)
            end = min(len(sentence), match.end() + 18)
            snippet = sentence[start:end].strip()

            values.append(value)
            units.append(unit)
            snippets.append(snippet)

        if not values:
            return None

        return {
            'values': values,
            'units': units,
            'snippets': snippets,
        }

    def score_quantitative_match(self, sentence: str, claim: Optional[Dict], candidate: Dict) -> float:
        """Score how well a candidate matches the quantitative details in a sentence."""
        if not claim:
            return 0.0

        haystack = ' '.join([
            candidate.get('title', ''),
            candidate.get('abstract', ''),
            candidate.get('journal', ''),
        ]).lower()

        score = 0.0
        for value, unit in zip(claim.get('values', []), claim.get('units', [])):
            try:
                numeric_value = float(value)
            except ValueError:
                continue

            candidate_values = [
                float(match.group(0))
                for match in re.finditer(r'\d+(?:\.\d+)?', haystack)
            ]

            if any(abs(candidate_value - numeric_value) <= max(0.15, numeric_value * 0.08)
                   for candidate_value in candidate_values):
                score += 1.0

            if unit and unit.lower() in haystack:
                score += 0.35

        lowered_sentence = sentence.lower()
        shared_terms = 0
        for token in ['critical temperature', 'tc', 'strain', 'superconduct', 'modulation']:
            if token in lowered_sentence and token in haystack:
                shared_terms += 1

        score += shared_terms * 0.25
        return score

    def _find_existing_citations(self, text: str) -> List[str]:
        """Find existing citations in text."""
        citations = []

        for pattern in self.CITATION_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                # Clean up citation
                citation = match.strip()
                if citation:
                    citations.append(citation)

        return citations

    def _extract_search_terms(self, sentence: str) -> List[str]:
        """Extract search terms from sentence."""
        sentence = self._strip_latex(sentence)
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'this', 'that', 'these', 'those', 'it', 'its', 'they', 'their', 'we',
            'our', 'has', 'have', 'had', 'will', 'would', 'could', 'should',
            'can', 'may', 'might', 'must', 'shall', 'which', 'who', 'whom',
            'whose', 'what', 'where', 'when', 'why', 'how', 'as', 'than', 'so',
            'very', 'too', 'also', 'just', 'only', 'even', 'not', 'no'
        }

        # Extract meaningful words, including material names like NbSe2
        words = re.findall(r'\b[A-Za-z][A-Za-z0-9_-]{1,}\b', sentence.lower())

        # Filter and deduplicate
        keywords = []
        seen = set()
        for word in words:
            if word not in stop_words and word not in seen:
                keywords.append(word)
                seen.add(word)

        # Also extract phrases (capitalized sequences)
        phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', sentence)
        keywords.extend([p.lower() for p in phrases if p.lower() not in seen])

        # Physics/material tokens that often matter for literature search
        special_terms = re.findall(r'\b(?:nbse2|mos2|wse2|tc|tdgl|epw|dft|tes|raman|phonon|vortex)\b', sentence.lower())
        for term in special_terms:
            if term not in seen:
                keywords.insert(0, term)
                seen.add(term)

        return keywords[:8]  # Limit to top 8 terms

    def _strip_latex(self, text: str) -> str:
        """Remove lightweight LaTeX markup for analysis/search."""
        text = re.sub(r'\\textbf\{([^}]*)\}', r'\1', text)
        text = re.sub(r'\\textit\{([^}]*)\}', r'\1', text)
        text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
        text = re.sub(r'\$([^$]*)\$', r'\1', text)
        text = re.sub(r'\\[a-zA-Z]+', ' ', text)
        text = text.replace('{', ' ').replace('}', ' ')
        return re.sub(r'\s+', ' ', text).strip()

    def _split_reference_sentences(self, text: str) -> List[str]:
        """Split title/abstract text into sentence-like units."""
        if not text:
            return []
        text = self._strip_latex(text)
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [part.strip() for part in parts if part.strip()]

    def _reference_title_terms(self, title: str) -> Set[str]:
        """Extract meaningful title terms for contribution ranking."""
        cleaned = self._strip_latex(title)
        words = re.findall(r'\b[A-Za-z][A-Za-z0-9/-]{1,}\b', cleaned.lower())
        return {
            word for word in words
            if word not in self.NOTE_STOP_WORDS and len(word) > 2
        }

    def _score_reference_sentence(self, sentence: str, title_terms: Set[str], index: int) -> float:
        """Rank a sentence by how well it states what the reference actually does."""
        lowered = sentence.lower()
        score = 0.0

        for pattern, weight in self.CONTRIBUTION_PATTERNS:
            if re.search(pattern, lowered):
                score += weight

        for pattern, weight in self.BACKGROUND_PATTERNS:
            if re.search(pattern, lowered):
                score += weight

        if index == 0 and any(re.search(pattern, lowered) for pattern, _ in self.BACKGROUND_PATTERNS):
            score -= 1.0

        sentence_terms = set(re.findall(r'\b[A-Za-z][A-Za-z0-9/-]{1,}\b', lowered))
        title_overlap = len(sentence_terms & title_terms)
        score += min(title_overlap * 0.35, 2.0)

        word_count = len(sentence.split())
        if 8 <= word_count <= 35:
            score += 0.4
        elif word_count < 5:
            score -= 0.8

        return score

    def extract_reference_note(self, candidate: Dict) -> Dict:
        """Extract the sentence that best states what a reference actually does."""
        title = self._strip_latex(candidate.get('title', '') or '').strip()
        abstract = candidate.get('abstract', '') or ''
        title_terms = self._reference_title_terms(title)
        abstract_sentences = self._split_reference_sentences(abstract)

        if not abstract_sentences:
            note = title
            return {
                'best_evidence': title,
                'reference_note': note,
            }

        ranked = []
        for index, sentence in enumerate(abstract_sentences):
            ranked.append((
                self._score_reference_sentence(sentence, title_terms, index),
                index,
                sentence,
            ))

        ranked.sort(key=lambda item: (item[0], -item[1]), reverse=True)
        best_sentence = ranked[0][2]

        note = best_sentence
        if title and title.lower() not in best_sentence.lower():
            note = f'{title}. {best_sentence}'

        return {
            'best_evidence': best_sentence,
            'reference_note': note,
        }

    def _extract_anchor_terms(self, text: str) -> List[str]:
        """Extract domain anchor phrases that should strongly constrain matching."""
        normalized = self._strip_latex(text).lower()
        anchors = []
        seen = set()

        for label, pattern in self.DOMAIN_ANCHOR_PATTERNS:
            if re.search(pattern, normalized) and label not in seen:
                anchors.append(label)
                seen.add(label)

        return anchors

    def _anchor_match_score(self, sentence: str, candidate: Dict) -> Tuple[float, int]:
        """Score candidate match against anchor terms extracted from the sentence."""
        anchors = self._extract_anchor_terms(sentence)
        if not anchors:
            return 0.0, 0

        candidate_text = ' '.join([
            candidate.get('title', ''),
            candidate.get('abstract', ''),
            candidate.get('journal', ''),
        ]).lower()

        matched = 0
        score = 0.0
        for anchor in anchors:
            if anchor in candidate_text:
                matched += 1
                # Title hits are stronger evidence than abstract hits.
                if anchor in (candidate.get('title', '') or '').lower():
                    score += 1.4
                else:
                    score += 0.8

        return score, matched

    def _term_overlap_score(self, sentence: str, candidate: Dict) -> float:
        """Score a candidate by token overlap with the sentence."""
        source_terms = set(self._extract_search_terms(sentence))
        candidate_text = ' '.join([
            candidate.get('title', ''),
            candidate.get('abstract', ''),
            candidate.get('journal', ''),
        ])
        candidate_terms = set(self._extract_search_terms(candidate_text))
        if not source_terms or not candidate_terms:
            return 0.0
        return len(source_terms & candidate_terms) / len(source_terms)

    def _parse_bib_entry(self, entry: str) -> Dict:
        """Parse a BibTeX entry into a candidate record."""
        fields = {}
        for match in re.finditer(self.FIELD_PATTERN, entry):
            fields[match.group(1).lower()] = match.group(2).strip()

        key_match = re.match(r'@\w+\{([^,]+),', entry.strip())
        display_title = self._strip_latex(fields.get('title', ''))
        return {
            'cite_key': key_match.group(1) if key_match else '',
            'doi': fields.get('doi', ''),
            'title': display_title,
            'authors': fields.get('author', ''),
            'year': fields.get('year', ''),
            'journal': fields.get('journal', '') or fields.get('booktitle', ''),
            'abstract': fields.get('abstract', ''),
            'type': fields.get('entrytype', 'article'),
            'source': 'local-bib',
            'bibtex': entry.strip(),
        }

    def _search_local_bibliography(self, sentence: str, bib_file: Optional[str], max_results: int) -> List[Dict]:
        """Search existing bibliography entries before external APIs."""
        if not bib_file:
            return []

        bib_path = Path(bib_file)
        if not bib_path.exists():
            return []

        extractor = self._build_bib_extractor()
        try:
            content = bib_path.read_text(encoding='utf-8')
        except OSError:
            return []

        candidates = [
            self._parse_bib_entry(entry)
            for entry in extractor._split_bib_entries(content)
        ]
        reranked = self.rerank_citations(sentence, candidates)
        reranked = [candidate for candidate in reranked if candidate.get('score', 0.0) > 0.0]
        return reranked[:max_results]

    def rerank_citations(self, sentence: str, candidates: List[Dict]) -> List[Dict]:
        """Rerank candidates using token overlap and quantitative-match signals."""
        claim = self.extract_quantitative_claim(sentence)
        reranked = []

        for candidate in candidates:
            score = self._term_overlap_score(sentence, candidate)
            score += self.score_quantitative_match(sentence, claim, candidate)
            anchor_score, anchor_matches = self._anchor_match_score(sentence, candidate)
            score += anchor_score

            anchors = self._extract_anchor_terms(sentence)
            if anchors and anchor_matches == 0:
                score = 0.0

            enriched = dict(candidate)
            enriched['score'] = round(score, 4)
            enriched['anchor_matches'] = anchor_matches
            reranked.append(enriched)

        reranked.sort(key=lambda item: item.get('score', 0.0), reverse=True)
        return reranked

    def search_for_citations(self, search_terms: List[str], max_results: int = 5,
                            timeout: int = 15, allow_arxiv: bool = False) -> List[Dict]:
        """Search for relevant citations using the extracted terms.

        Args:
            search_terms: Keywords to search for
            max_results: Maximum results to return
            timeout: Request timeout

        Returns:
            List of citation suggestions
        """
        if not search_terms:
            return []

        query = ' '.join(search_terms[:6])
        results = []

        # Search CrossRef
        try:
            url = 'https://api.crossref.org/works'
            params = {
                'query': query,
                'rows': max_results,
                'select': 'DOI,title,author,published-print,published-online,year,type,container-title,abstract'
            }

            response = self.session.get(url, params=params, timeout=timeout)

            if response.status_code == 200:
                data = response.json()
                items = data.get('message', {}).get('items', [])

                for item in items:
                    title = item.get('title', [''])[0] if isinstance(item.get('title'), list) else item.get('title', '')

                    # Get authors
                    authors = []
                    for author in item.get('author', [])[:3]:
                        family = author.get('family', '')
                        given = author.get('given', '')
                        if family:
                            authors.append(f"{family}, {given}" if given else family)

                    # Get year
                    year = None
                    pub = item.get('published-print') or item.get('published-online') or {}
                    date_parts = pub.get('date-parts', [[None]])
                    if date_parts and date_parts[0]:
                        year = date_parts[0][0]

                    record = {
                        'doi': item.get('DOI', ''),
                        'title': title,
                        'authors': ' and '.join(authors) if authors else 'Unknown',
                        'year': year,
                        'journal': item.get('container-title', [''])[0] if item.get('container-title') else '',
                        'abstract': item.get('abstract', '') or '',
                        'type': item.get('type', 'article'),
                        'source': 'CrossRef'
                    }
                    if allow_arxiv or 'arxiv' not in record['doi'].lower():
                        results.append(record)
            elif response.status_code == 429:
                print('  CrossRef rate-limited, falling back to OpenAlex', file=sys.stderr)

        except Exception as e:
            print(f'  CrossRef search error: {e}', file=sys.stderr)

        if results:
            return results

        # Fallback 1: OpenAlex
        try:
            url = 'https://api.openalex.org/works'
            params = {
                'search': query,
                'per-page': max_results,
                'mailto': 'research@example.com',
            }
            response = self.session.get(url, params=params, timeout=timeout)

            if response.status_code == 200:
                data = response.json()
                for item in data.get('results', []):
                    doi = item.get('doi', '') or ''
                    doi = doi.replace('https://doi.org/', '')
                    authors = []
                    for author in item.get('authorships', [])[:3]:
                        display_name = author.get('author', {}).get('display_name', '')
                        if display_name:
                            authors.append(display_name)

                    record = {
                        'doi': doi,
                        'title': item.get('title', ''),
                        'authors': ' and '.join(authors) if authors else 'Unknown',
                        'year': item.get('publication_year'),
                        'journal': item.get('primary_location', {}).get('source', {}).get('display_name', ''),
                        'abstract': self._openalex_abstract_to_text(item.get('abstract_inverted_index')),
                        'type': item.get('type', 'article'),
                        'source': 'OpenAlex',
                    }
                    journal_text = (record.get('journal') or '').lower()
                    doi_text = (record.get('doi') or '').lower()
                    if allow_arxiv or ('arxiv' not in journal_text and 'arxiv' not in doi_text):
                        results.append(record)
        except Exception as e:
            print(f'  OpenAlex search error: {e}', file=sys.stderr)

        if results:
            return results

        # Fallback 2: Semantic Scholar
        try:
            url = 'https://api.semanticscholar.org/graph/v1/paper/search'
            params = {
                'query': query,
                'limit': max_results,
                'fields': 'paperId,title,authors,year,journal,externalIds,abstract,venue',
            }
            response = self.session.get(url, params=params, timeout=timeout)

            if response.status_code == 200:
                data = response.json()
                for item in data.get('data', []):
                    # Get DOI from external IDs
                    external_ids = item.get('externalIds', {})
                    doi = external_ids.get('DOI', '')
                    if not doi:
                        continue

                    authors = []
                    for author in item.get('authors', [])[:3]:
                        name = author.get('name', '')
                        if name:
                            authors.append(name)

                    journal = item.get('journal', {}) or {}
                    journal_name = journal.get('name', '') if isinstance(journal, dict) else ''
                    if not journal_name:
                        journal_name = item.get('venue', '') or ''

                    record = {
                        'doi': doi,
                        'title': item.get('title', ''),
                        'authors': ' and '.join(authors) if authors else 'Unknown',
                        'year': item.get('year'),
                        'journal': journal_name,
                        'abstract': item.get('abstract', '') or '',
                        'type': 'article',
                        'source': 'Semantic Scholar',
                    }
                    journal_text = (record.get('journal') or '').lower()
                    doi_text = (record.get('doi') or '').lower()
                    if allow_arxiv or ('arxiv' not in journal_text and 'arxiv' not in doi_text):
                        results.append(record)
        except Exception as e:
            print(f'  Semantic Scholar search error: {e}', file=sys.stderr)

        return results

    def _finalize_bibliography_entry(self, doi: str, bib_file: str) -> Optional[str]:
        """Ensure a DOI is backed by a concrete BibTeX entry in bib_file."""
        extractor = self._build_bib_extractor()

        existing_entry = extractor.find_existing_entry(doi, bib_file)
        if existing_entry:
            return existing_entry

        bibtex = extractor.extract_bibtex(doi, bib_file=bib_file)
        if not bibtex:
            return None

        bib_path = Path(bib_file)
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        if not bib_path.exists():
            bib_path.touch()

        existing_keys = extractor.read_existing_keys(bib_file)
        extractor.append_to_file(bibtex, bib_file, existing_keys)
        return extractor.find_existing_entry(doi, bib_file) or bibtex

    def suggest_citations_for_sentence(self, sentence: str, max_results: int = 3,
                                       timeout: int = 15,
                                       allow_arxiv: bool = False,
                                       bib_file: Optional[str] = None) -> List[Dict]:
        """Search and rerank candidates for a sentence."""
        reranked = self._search_local_bibliography(sentence, bib_file, max_results)
        if not reranked:
            search_terms = self._extract_search_terms(sentence)
            candidates = self.search_for_citations(
                search_terms,
                max_results=max(max_results * 2, 6),
                timeout=timeout,
                allow_arxiv=allow_arxiv,
            )
            reranked = self.rerank_citations(sentence, candidates)
            reranked = [candidate for candidate in reranked if candidate.get('score', 0.0) > 0.0][:max_results]
        finalized = []
        for candidate in reranked:
            note_summary = self.extract_reference_note(candidate)
            candidate['best_evidence'] = note_summary['best_evidence']
            candidate['reference_note'] = note_summary['reference_note']
            doi = candidate.get('doi', '')
            if not doi:
                bibtex = candidate.get('bibtex', '')
                if bibtex:
                    extractor = self._build_bib_extractor()
                    candidate['inline_citation'] = extractor.generate_inline_citation(
                        bibtex,
                        style='journal',
                    )
                    finalized.append(candidate)
                    continue

                candidate['inline_citation'] = ''
                if not bib_file:
                    finalized.append(candidate)
                continue

            if bib_file:
                bibtex = self._finalize_bibliography_entry(doi, bib_file)
                if not bibtex:
                    continue
                extractor = self._build_bib_extractor()
                candidate['inline_citation'] = extractor.generate_inline_citation(
                    bibtex,
                    style='journal',
                )
                finalized.append(candidate)
                continue

            candidate['inline_citation'] = self.build_inline_citation(doi) if doi else ''
            finalized.append(candidate)
        return finalized

    def _load_bib_extractor_module(self):
        if self.extractor_module is not None:
            return self.extractor_module

        script_path = Path(__file__).with_name('bib_extractor.py')
        spec = importlib.util.spec_from_file_location('local_bib_extractor', script_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.extractor_module = module
        return module

    def _build_bib_extractor(self):
        module = self._load_bib_extractor_module()
        return module.BibExtractor(use_full_journal_name=self.use_full_journal_name)

    def build_inline_citation(self, doi: str, style: str = 'journal',
                              bib_file: Optional[str] = None) -> str:
        """Generate an inline citation string using the local bib_extractor."""
        extractor = self._build_bib_extractor()
        bibtex = extractor.extract_bibtex(doi, bib_file=bib_file)
        if not bibtex:
            return ''
        return extractor.generate_inline_citation(bibtex, style=style)

    def analyze_document(self, content: str, auto_search: bool = True,
                        max_results_per_sentence: int = 3,
                        timeout: int = 15,
                        audit_cited: bool = False,
                        allow_arxiv: bool = False,
                        bib_file: Optional[str] = None) -> Dict:
        """Analyze a full document for missing citations.

        Args:
            content: Document text content
            auto_search: Automatically search for citations
            max_results_per_sentence: Max search results per sentence
            timeout: Request timeout

        Returns:
            Analysis results with suggestions
        """
        # Split into sentences
        sentences = self._split_sentences(content)

        results = {
            'total_sentences': 0,
            'sentences_needing_citation': 0,
            'sentences_with_citations': 0,
            'sentences_ok': 0,
            'analyses': [],
            'suggested_citations': []
        }

        print(f'\nAnalyzing {len(sentences)} sentences...', file=sys.stderr)

        for i, sentence in enumerate(sentences, 1):
            sentence = sentence.strip()
            if not sentence or len(sentence) < 20:  # Skip very short sentences
                continue

            results['total_sentences'] += 1

            analysis = self.analyze_sentence(sentence)

            if analysis.has_citation:
                results['sentences_with_citations'] += 1
            elif analysis.needs_citation:
                results['sentences_needing_citation'] += 1

                # Search for citations if requested
                if auto_search and analysis.suggested_search_terms:
                    print(f'\n  [{i}] Searching for: {" ".join(analysis.suggested_search_terms[:4])}...', file=sys.stderr)

                    citations = self.suggest_citations_for_sentence(
                        analysis.sentence,
                        max_results=max_results_per_sentence,
                        timeout=timeout,
                        allow_arxiv=allow_arxiv,
                        bib_file=bib_file,
                    )

                    analysis.citation_suggestions = citations
                    results['suggested_citations'].extend(citations)

                    if citations:
                        print(f'       Found {len(citations)} suggestions', file=sys.stderr)
            elif analysis.has_citation and audit_cited and self.extract_quantitative_claim(analysis.sentence):
                analysis.citation_suggestions = self.suggest_citations_for_sentence(
                    analysis.sentence,
                    max_results=max_results_per_sentence,
                    timeout=timeout,
                    allow_arxiv=allow_arxiv,
                    bib_file=bib_file,
                )
                results['analyses'].append(analysis)
                continue
            else:
                results['sentences_ok'] += 1

            results['analyses'].append(analysis)

        return results

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Handle LaTeX citations specially to avoid breaking on periods within
        text = re.sub(r'(\\cite[pt]?\{[^}]+\})', r' \1 ', text)

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

        # Also split on newlines
        result = []
        for s in sentences:
            result.extend(s.split('\n'))

        return [s.strip() for s in result if s.strip()]

    def print_report(self, results: Dict, show_all: bool = False,
                    show_ok: bool = False):
        """Print analysis report."""
        print('\n' + '=' * 60)
        print('Citation Need Analysis Report')
        print('=' * 60)
        print(f'Total sentences: {results["total_sentences"]}')
        print(f'Sentences with citations: {results["sentences_with_citations"]}')
        print(f'Sentences needing citation: {results["sentences_needing_citation"]}')
        print(f'Sentences OK (no citation needed): {results["sentences_ok"]}')

        # Show sentences needing citation
        needing = [a for a in results['analyses'] if a.needs_citation]
        if needing:
            print('\n' + '-' * 60)
            print('Sentences Needing Citations:')
            print('-' * 60)

            for analysis in needing[:20]:  # Limit output
                print(f'\n• "{analysis.sentence[:80]}..."')
                print(f'  Confidence: {analysis.confidence:.0%}')
                print(f'  Reason: {analysis.reason}')

                if analysis.suggested_search_terms:
                    print(f'  Search: {" ".join(analysis.suggested_search_terms[:4])}')

                if analysis.citation_suggestions:
                    print(f'  Suggestions:')
                    for cite in analysis.citation_suggestions[:3]:
                        print(f'    - {cite["title"][:50]}...')
                        print(f'      {cite["authors"]} ({cite["year"]})')
                        print(f'      DOI: {cite["doi"]}')
                        if cite.get('inline_citation'):
                            print(f'      Inline: {cite["inline_citation"]}')
                        if cite.get('reference_note'):
                            print(f'      Note: {cite["reference_note"]}')

        # Show OK sentences if requested
        if show_ok:
            ok = [a for a in results['analyses'] if not a.needs_citation and not a.has_citation]
            if ok:
                print('\n' + '-' * 60)
                print('Sentences Without Citation Need:')
                print('-' * 60)

                for analysis in ok[:10]:
                    print(f'\n• "{analysis.sentence[:60]}..."')
                    print(f'  Reason: {analysis.reason}')


def main():
    parser = argparse.ArgumentParser(
        description='Analyze text and find missing citations.',
        epilog='Examples:\n'
                '  %(prog)s paper.tex\n'
                '  %(prog)s paper.tex --no-search  # Analyze only, no search\n'
                '  %(prog)s paper.tex --show-ok     # Show all sentences'
    )
    parser.formatter_class = argparse.RawDescriptionHelpFormatter

    parser.add_argument(
        'input_file',
        help='Input file to analyze (.tex, .md, or .txt)'
    )

    parser.add_argument(
        '--no-search',
        action='store_true',
        help='Analyze only, do not search for citations'
    )

    parser.add_argument(
        '--max-results',
        type=int,
        default=3,
        help='Max search results per sentence (default: 3)'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=15,
        help='Search timeout in seconds (default: 15)'
    )

    parser.add_argument(
        '--show-ok',
        action='store_true',
        help='Show sentences that don\'t need citations'
    )

    parser.add_argument(
        '--audit-cited',
        action='store_true',
        help='Also audit sentences that already have citations, especially quantitative claims'
    )

    parser.add_argument(
        '--allow-arxiv',
        action='store_true',
        help='Include arXiv/preprint results. Default is to exclude them.'
    )

    parser.add_argument(
        '--full-journal-name',
        action='store_true',
        help='Use full journal names instead of abbreviations in inline citations.'
    )

    parser.add_argument(
        '--bib-file',
        help='Target bibliography file. Final citations must exist here when provided.'
    )

    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )

    args = parser.parse_args()

    # Read input file
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f'Error: File not found: {args.input_file}', file=sys.stderr)
        sys.exit(1)

    # Create analyzer
    analyzer = CitationNeedAnalyzer(use_full_journal_name=args.full_journal_name)

    # Run analysis
    results = analyzer.analyze_document(
        content,
        auto_search=not args.no_search,
        max_results_per_sentence=args.max_results,
        timeout=args.timeout,
        audit_cited=args.audit_cited,
        allow_arxiv=args.allow_arxiv,
        bib_file=args.bib_file,
    )

    # Output results
    if args.format == 'json':
        # Convert dataclass to dict for JSON
        results['analyses'] = [
            {
                'sentence': a.sentence,
                'needs_citation': a.needs_citation,
                'confidence': a.confidence,
                'reason': a.reason,
                'has_citation': a.has_citation,
                'search_terms': a.suggested_search_terms,
                'suggestions': a.citation_suggestions
            }
            for a in results['analyses']
        ]
        print(json.dumps(results, indent=2))
    else:
        analyzer.print_report(results, show_ok=args.show_ok)


if __name__ == '__main__':
    main()
