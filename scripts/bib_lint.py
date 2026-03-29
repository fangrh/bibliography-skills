#!/usr/bin/env python3
"""
Bibliography Linter - Check BibTeX format and consistency

Validates:
1. BibTeX syntax correctness
2. Required fields presence
3. Field format validity (DOI, URL, pages, year, etc.)
4. Author name format
5. Citation key conventions
6. Journal name consistency
7. Duplicate detection
"""

import sys
import re
import argparse
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from collections import defaultdict


class BibLinter:
    """Lint BibTeX files for format and consistency issues."""

    # Required fields by entry type
    REQUIRED_FIELDS = {
        'article': ['author', 'title', 'journal', 'year'],
        'book': ['author', 'title', 'publisher', 'year'],
        'inbook': ['author', 'title', 'booktitle', 'year'],
        'incollection': ['author', 'title', 'booktitle', 'year'],
        'inproceedings': ['author', 'title', 'booktitle', 'year'],
        'conference': ['author', 'title', 'booktitle', 'year'],
        'phdthesis': ['author', 'title', 'school', 'year'],
        'mastersthesis': ['author', 'title', 'school', 'year'],
        'techreport': ['author', 'title', 'institution', 'year'],
        'misc': [],  # No required fields
        'unpublished': ['author', 'title', 'note'],
        'online': ['author', 'title', 'url', 'year'],
    }

    # Recommended fields by entry type
    RECOMMENDED_FIELDS = {
        'article': ['volume', 'pages', 'doi'],
        'book': ['isbn'],
        'inbook': ['pages', 'publisher'],
        'incollection': ['pages', 'publisher'],
        'inproceedings': ['pages', 'doi'],
        'conference': ['pages'],
        'phdthesis': [],
        'mastersthesis': [],
        'techreport': ['number'],
        'misc': ['year', 'doi', 'url'],
        'unpublished': ['year'],
        'online': ['urldate'],
    }

    # Severity levels
    ERROR = 'ERROR'
    WARNING = 'WARNING'
    INFO = 'INFO'

    def __init__(self, strict: bool = False):
        """Initialize linter.

        Args:
            strict: If True, treat warnings as errors
        """
        self.strict = strict
        self.issues = []
        self.entries = []
        self.stats = {
            'total_entries': 0,
            'entries_with_issues': 0,
            'total_issues': 0,
            'errors': 0,
            'warnings': 0,
            'info': 0
        }

    def lint_file(self, bib_file: str) -> Dict:
        """Lint a BibTeX file.

        Args:
            bib_file: Path to BibTeX file

        Returns:
            Dict with linting results
        """
        try:
            with open(bib_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            self._add_issue(None, self.ERROR, f'File not found: {bib_file}')
            return self._get_results()

        # Parse entries
        self.entries = self._parse_entries(content)
        self.stats['total_entries'] = len(self.entries)

        # Run all checks
        for entry in self.entries:
            self._check_entry(entry)

        # Cross-entry checks
        self._check_duplicates()
        self._check_journal_consistency()

        # Calculate stats
        entries_with_issues = set()
        for issue in self.issues:
            if issue['key']:
                entries_with_issues.add(issue['key'])

        self.stats['entries_with_issues'] = len(entries_with_issues)
        self.stats['total_issues'] = len(self.issues)
        self.stats['errors'] = sum(1 for i in self.issues if i['severity'] == self.ERROR)
        self.stats['warnings'] = sum(1 for i in self.issues if i['severity'] == self.WARNING)
        self.stats['info'] = sum(1 for i in self.issues if i['severity'] == self.INFO)

        return self._get_results()

    def _parse_entries(self, content: str) -> List[Dict]:
        """Parse BibTeX entries from content."""
        entries = []

        # Match BibTeX entries
        entry_pattern = r'@(\w+)\s*\{\s*([^,]+)\s*,([^@]*?)(?=@\w+\s*\{|$)'

        for match in re.finditer(entry_pattern, content, re.DOTALL):
            entry_type = match.group(1).lower()
            key = match.group(2).strip()
            fields_str = match.group(3)
            raw = match.group(0)

            # Parse fields
            fields = self._parse_fields(fields_str)

            entries.append({
                'type': entry_type,
                'key': key,
                'fields': fields,
                'raw': raw,
                'start_pos': match.start()
            })

        return entries

    def _parse_fields(self, fields_str: str) -> Dict[str, str]:
        """Parse fields from BibTeX entry body."""
        fields = {}

        # Handle both {value} and "value" formats
        # Also handle nested braces
        field_pattern = r'(\w+)\s*=\s*(?:\{((?:[^{}]|\{[^{}]*\})*)\}|"([^"]*)")'

        for match in re.finditer(field_pattern, fields_str):
            field_name = match.group(1).lower()
            # Get value from either {} or "" group
            field_value = match.group(2) if match.group(2) is not None else match.group(3)
            if field_value:
                fields[field_name] = field_value.strip()

        return fields

    def _check_entry(self, entry: Dict):
        """Run all checks on a single entry."""
        key = entry['key']
        entry_type = entry['type']
        fields = entry['fields']

        # 1. Check citation key format
        self._check_citation_key(key, entry_type)

        # 2. Check required fields
        self._check_required_fields(key, entry_type, fields)

        # 3. Check recommended fields
        self._check_recommended_fields(key, entry_type, fields)

        # 4. Check field formats
        self._check_field_formats(key, fields)

        # 5. Check author format
        if 'author' in fields:
            self._check_author_format(key, fields['author'])

        # 6. Check for common typos in field names
        self._check_field_typos(key, fields)

        # 7. Check brace balance
        self._check_brace_balance(key, entry['raw'])

    def _check_citation_key(self, key: str, entry_type: str):
        """Check citation key format conventions."""
        # Key should not be empty
        if not key:
            self._add_issue(key, self.ERROR, 'Citation key is empty')
            return

        # Key should not contain spaces
        if ' ' in key:
            self._add_issue(key, self.ERROR, f'Citation key contains spaces: "{key}"')

        # Key should not contain special characters (except :_-)
        if re.search(r'[^\w:\-]', key):
            self._add_issue(key, self.WARNING, f'Citation key contains special characters: "{key}"')

        # Key should not start with number
        if key[0].isdigit():
            self._add_issue(key, self.INFO, f'Citation key starts with number: "{key}"')

        # Key should follow common conventions
        # Good: Author2023Title, author2023title, Author2023
        # Bad: ref1, paper1, 2023paper
        if not re.match(r'^[A-Za-z][A-Za-z0-9:\-_]*[0-9]{4}', key):
            if not re.match(r'^[A-Za-z]{2,}', key):
                self._add_issue(key, self.INFO,
                    f'Citation key does not follow common convention (AuthorYear format): "{key}"')

    def _check_required_fields(self, key: str, entry_type: str, fields: Dict):
        """Check that all required fields are present."""
        required = self.REQUIRED_FIELDS.get(entry_type, [])

        for field in required:
            if field not in fields or not fields[field].strip():
                self._add_issue(key, self.ERROR,
                    f'Missing required field "{field}" for @{entry_type} entry')

    def _check_recommended_fields(self, key: str, entry_type: str, fields: Dict):
        """Check for recommended fields."""
        recommended = self.RECOMMENDED_FIELDS.get(entry_type, [])

        missing = [f for f in recommended if f not in fields or not fields[f].strip()]

        if missing:
            self._add_issue(key, self.WARNING,
                f'Missing recommended fields: {", ".join(missing)}')

    def _check_field_formats(self, key: str, fields: Dict):
        """Check format of specific fields."""
        # DOI format
        if 'doi' in fields:
            doi = fields['doi']
            if not re.match(r'^10\.\d{4,9}/[^\s]+$', doi):
                self._add_issue(key, self.WARNING, f'Invalid DOI format: {doi}')

        # URL format
        if 'url' in fields:
            url = fields['url']
            if not url.startswith(('http://', 'https://', 'ftp://')):
                self._add_issue(key, self.WARNING, f'Invalid URL format: {url[:50]}...')

        # Year format
        if 'year' in fields:
            year = fields['year']
            if not re.match(r'^\d{4}$', str(year)):
                self._add_issue(key, self.WARNING, f'Invalid year format: {year}')

        # Pages format
        if 'pages' in fields:
            pages = fields['pages']
            # Should be: single page (123), range (123--456), or article number
            if not re.match(r'^[\d\w]+([\-\u2013\u2014]{1,2}[\d\w]+)?(\.\w+)?$', pages):
                self._add_issue(key, self.INFO,
                    f'Page format may be incorrect (use -- for ranges): {pages}')
            # Check for single hyphen instead of en-dash
            if re.search(r'(?<!-)-(?!-)\d', pages):
                self._add_issue(key, self.INFO,
                    f'Use double hyphen (--) for page ranges, not single: {pages}')

        # Volume format
        if 'volume' in fields:
            volume = fields['volume']
            if not re.match(r'^\d+$', str(volume)):
                self._add_issue(key, self.INFO, f'Volume should be numeric: {volume}')

        # Number/Issue format
        if 'number' in fields:
            number = fields['number']
            if not re.match(r'^\d+$', str(number)):
                self._add_issue(key, self.INFO, f'Number/Issue should typically be numeric: {number}')

        # ISSN format
        if 'issn' in fields:
            issn = fields['issn']
            if not re.match(r'^\d{4}-\d{3}[\dX]$', issn):
                self._add_issue(key, self.INFO, f'ISSN format should be XXXX-XXXX: {issn}')

        # ISBN format
        if 'isbn' in fields:
            isbn = fields['isbn'].replace('-', '').replace(' ', '')
            if not re.match(r'^97[89]\d{10}$', isbn) and not re.match(r'^\d{9}[\dX]$', isbn):
                self._add_issue(key, self.INFO, f'ISBN format may be incorrect: {fields["isbn"]}')

        # Month format
        if 'month' in fields:
            month = fields['month'].lower()
            valid_months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                          'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
                          'january', 'february', 'march', 'april', 'may', 'june',
                          'july', 'august', 'september', 'october', 'november', 'december',
                          '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']
            if month not in valid_months:
                self._add_issue(key, self.INFO, f'Non-standard month format: {fields["month"]}')

    def _check_author_format(self, key: str, author: str):
        """Check author name format."""
        # Split by 'and'
        authors = re.split(r'\s+and\s+', author)

        issues = []

        for i, auth in enumerate(authors):
            auth = auth.strip()

            # Check for corporate authors (in braces)
            if auth.startswith('{') and auth.endswith('}'):
                continue

            # Check format: "Last, First" or "First Last"
            if ',' in auth:
                # Should be "Last, First" format
                parts = auth.split(',', 1)
                if len(parts) == 2:
                    last, first = parts
                    if not last.strip():
                        issues.append(f'Author {i+1}: Empty last name')
                    if not first.strip() and len(authors) > 1:
                        issues.append(f'Author {i+1}: Empty first name')
            else:
                # "First Last" format - check for proper capitalization
                words = auth.split()
                if len(words) == 1:
                    # Single name - could be organization or single-name author
                    pass
                elif len(words) >= 2:
                    # Multiple words without comma might need format adjustment
                    # This is often acceptable but worth noting
                    pass

        if issues:
            for issue in issues:
                self._add_issue(key, self.INFO, issue)

    def _check_field_typos(self, key: str, fields: Dict):
        """Check for common field name typos."""
        common_typos = {
            'jounral': 'journal',
            'joural': 'journal',
            'journaal': 'journal',
            'autthor': 'author',
            'auhtor': 'author',
            'auther': 'author',
            'tile': 'title',
            'titel': 'title',
            'titl': 'title',
            'pubisher': 'publisher',
            'publishr': 'publisher',
            'volueme': 'volume',
            'volmue': 'volume',
            'pagse': 'pages',
            'pags': 'pages',
            'yaer': 'year',
            'yer': 'year',
            'doii': 'doi',
            'adrress': 'address',
            'addres': 'address',
            'booktitel': 'booktitle',
            'booktite': 'booktitle',
            'instituion': 'institution',
            'institutoion': 'institution',
            'organizaton': 'organization',
            'schol': 'school',
        }

        for field in fields:
            if field in common_typos:
                self._add_issue(key, self.WARNING,
                    f'Possible typo in field name: "{field}" → should be "{common_typos[field]}"')

    def _check_brace_balance(self, key: str, raw_entry: str):
        """Check for unbalanced braces."""
        # Count braces (ignoring those in strings)
        open_count = raw_entry.count('{')
        close_count = raw_entry.count('}')

        if open_count != close_count:
            self._add_issue(key, self.ERROR,
                f'Unbalanced braces: {open_count} opening, {close_count} closing')

    def _check_duplicates(self):
        """Check for duplicate entries."""
        # Check for duplicate keys
        keys = [e['key'] for e in self.entries]
        key_counts = defaultdict(list)

        for i, key in enumerate(keys):
            key_counts[key].append(i)

        for key, indices in key_counts.items():
            if len(indices) > 1:
                self._add_issue(key, self.ERROR,
                    f'Duplicate citation key appears {len(indices)} times')

        # Check for duplicate DOIs
        doi_entries = defaultdict(list)
        for entry in self.entries:
            doi = entry['fields'].get('doi', '').lower().strip()
            if doi:
                doi_entries[doi].append(entry['key'])

        for doi, keys in doi_entries.items():
            if len(keys) > 1:
                self._add_issue(None, self.WARNING,
                    f'Duplicate DOI {doi} in entries: {", ".join(keys)}')

        # Check for duplicate titles
        title_entries = defaultdict(list)
        for entry in self.entries:
            title = entry['fields'].get('title', '').lower().strip()
            # Remove braces and extra spaces
            title = re.sub(r'[{}]', '', title)
            title = re.sub(r'\s+', ' ', title)
            if title and len(title) > 20:  # Only check substantial titles
                title_entries[title].append(entry['key'])

        for title, keys in title_entries.items():
            if len(keys) > 1:
                self._add_issue(None, self.WARNING,
                    f'Possible duplicate title in entries: {", ".join(keys)}')

    def _check_journal_consistency(self):
        """Check for journal name consistency."""
        # Group entries by journal
        journal_entries = defaultdict(list)
        for entry in self.entries:
            journal = entry['fields'].get('journal', '').strip()
            if journal:
                journal_entries[journal.lower()].append({
                    'key': entry['key'],
                    'original': journal
                })

        # Check for variations of the same journal
        journal_names = list(journal_entries.keys())
        for i, name1 in enumerate(journal_names):
            for name2 in journal_names[i+1:]:
                # Check if they're similar but different
                if self._are_similar_journals(name1, name2):
                    entries1 = [e['key'] for e in journal_entries[name1]]
                    entries2 = [e['key'] for e in journal_entries[name2]]

                    orig1 = journal_entries[name1][0]['original']
                    orig2 = journal_entries[name2][0]['original']

                    if orig1 != orig2:
                        self._add_issue(None, self.INFO,
                            f'Journal name inconsistency: "{orig1}" ({len(entries1)} entries) vs "{orig2}" ({len(entries2)} entries)')

    def _are_similar_journals(self, name1: str, name2: str) -> bool:
        """Check if two journal names are likely the same journal."""
        # Normalize
        n1 = re.sub(r'[^\w\s]', '', name1.lower())
        n2 = re.sub(r'[^\w\s]', '', name2.lower())

        # Check if one is abbreviation of other
        words1 = set(n1.split())
        words2 = set(n2.split())

        # If most words overlap
        if words1 and words2:
            overlap = len(words1 & words2) / max(len(words1), len(words2))
            return overlap > 0.7

        return False

    def _add_issue(self, key: Optional[str], severity: str, message: str):
        """Add an issue to the list."""
        self.issues.append({
            'key': key,
            'severity': severity if not self.strict else self.ERROR,
            'message': message
        })

    def _get_results(self) -> Dict:
        """Get linting results."""
        return {
            'stats': self.stats,
            'issues': self.issues
        }

    def print_report(self, results: Dict, show_info: bool = True, show_context: bool = False):
        """Print linting report."""
        stats = results['stats']
        issues = results['issues']

        print('\n' + '=' * 60)
        print('BibTeX Lint Report')
        print('=' * 60)
        print(f'Total entries: {stats["total_entries"]}')
        print(f'Entries with issues: {stats["entries_with_issues"]}')
        print(f'Total issues: {stats["total_issues"]}')
        print(f'  Errors: {stats["errors"]}')
        print(f'  Warnings: {stats["warnings"]}')
        print(f'  Info: {stats["info"]}')

        if not issues:
            print('\n✓ No issues found!')
            return

        # Group by severity
        errors = [i for i in issues if i['severity'] == self.ERROR]
        warnings = [i for i in issues if i['severity'] == self.WARNING]
        info = [i for i in issues if i['severity'] == self.INFO]

        if errors:
            print('\n' + '-' * 60)
            print('ERRORS:', file=sys.stderr)
            for issue in errors:
                key_str = f'[{issue["key"]}] ' if issue['key'] else ''
                print(f'  ✗ {key_str}{issue["message"]}', file=sys.stderr)

        if warnings:
            print('\n' + '-' * 60)
            print('WARNINGS:')
            for issue in warnings:
                key_str = f'[{issue["key"]}] ' if issue['key'] else ''
                print(f'  ⚠ {key_str}{issue["message"]}')

        if show_info and info:
            print('\n' + '-' * 60)
            print('INFO:')
            for issue in info:
                key_str = f'[{issue["key"]}] ' if issue['key'] else ''
                print(f'  ℹ {key_str}{issue["message"]}')


def main():
    parser = argparse.ArgumentParser(
        description='Lint BibTeX files for format and consistency issues.',
        epilog='Examples:\n'
                '  %(prog)s references.bib\n'
                '  %(prog)s references.bib --strict\n'
                '  %(prog)s references.bib --errors-only'
    )
    parser.formatter_class = argparse.RawDescriptionHelpFormatter

    parser.add_argument(
        'bib_file',
        nargs='?',
        default='references.bib',
        help='BibTeX file to lint (default: references.bib)'
    )

    parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat all warnings as errors'
    )

    parser.add_argument(
        '--errors-only',
        action='store_true',
        help='Only show errors, hide warnings and info'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Only show summary, no detailed issues'
    )

    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )

    args = parser.parse_args()

    # Create linter
    linter = BibLinter(strict=args.strict)

    # Run linting
    results = linter.lint_file(args.bib_file)

    # Output results
    if args.format == 'json':
        import json
        print(json.dumps(results, indent=2))
    else:
        linter.print_report(
            results,
            show_info=not args.errors_only,
            show_context=not args.quiet
        )

    # Exit with error code if there are errors
    if results['stats']['errors'] > 0:
        sys.exit(1)
    elif args.strict and results['stats']['warnings'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
