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

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BibSmartSearch/1.0'
        })

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

        # Extract meaningful words
        words = re.findall(r'\b[A-Za-z]{3,}\b', sentence.lower())

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

        return keywords[:8]  # Limit to top 8 terms

    def search_for_citations(self, search_terms: List[str], max_results: int = 5,
                            timeout: int = 15) -> List[Dict]:
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
                'select': 'DOI,title,author,published-print,published-online,year,type'
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

                    results.append({
                        'doi': item.get('DOI', ''),
                        'title': title,
                        'authors': ' and '.join(authors) if authors else 'Unknown',
                        'year': year,
                        'type': item.get('type', 'article'),
                        'source': 'CrossRef'
                    })

        except Exception as e:
            print(f'  CrossRef search error: {e}', file=sys.stderr)

        return results

    def analyze_document(self, content: str, auto_search: bool = True,
                        max_results_per_sentence: int = 3,
                        timeout: int = 15) -> Dict:
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

                    citations = self.search_for_citations(
                        analysis.suggested_search_terms,
                        max_results=max_results_per_sentence,
                        timeout=timeout
                    )

                    analysis.citation_suggestions = citations
                    results['suggested_citations'].extend(citations)

                    if citations:
                        print(f'       Found {len(citations)} suggestions', file=sys.stderr)
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
    analyzer = CitationNeedAnalyzer()

    # Run analysis
    results = analyzer.analyze_document(
        content,
        auto_search=not args.no_search,
        max_results_per_sentence=args.max_results,
        timeout=args.timeout
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
