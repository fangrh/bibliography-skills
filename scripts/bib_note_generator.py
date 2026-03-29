#!/usr/bin/env python3
"""
Bibliography Note Generator - Generate notes for BibTeX entries using LLM

Reads BibTeX entries with abstracts and generates concise notes that describe:
- Main topic/contribution
- What this paper could be cited for (methodology, finding, data, etc.)
"""

import sys
import re
import argparse
import json
from typing import Optional, Dict, List
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests module not found. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


class BibNoteGenerator:
    """Generate notes for BibTeX entries using Claude or other LLM APIs."""

    # Prompt template for note generation
    NOTE_PROMPT_TEMPLATE = """Based on this abstract, generate a brief note (2-3 sentences) for a bibliography entry.
Include:
- Main topic/contribution
- What this paper could be cited for (methodology, finding, data, technique, etc.)

Abstract: {abstract}

Generate only the note text, no additional formatting or labels."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-haiku-20240307",
                 timeout: int = 30):
        """Initialize the note generator.

        Args:
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            model: Claude model to use
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.session = requests.Session()

    def parse_bib_file(self, bib_file: str) -> List[Dict]:
        """Parse BibTeX file into entries."""
        try:
            with open(bib_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f'Error: File not found: {bib_file}', file=sys.stderr)
            return []

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

        return entries

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

    def generate_note_with_claude(self, abstract: str) -> Optional[str]:
        """Generate note using Claude API.

        Args:
            abstract: The abstract text

        Returns:
            Generated note or None on failure
        """
        import os

        api_key = self.api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            print('  Warning: No API key found. Set ANTHROPIC_API_KEY environment variable.', file=sys.stderr)
            return None

        prompt = self.NOTE_PROMPT_TEMPLATE.format(abstract=abstract)

        try:
            response = self.session.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json'
                },
                json={
                    'model': self.model,
                    'max_tokens': 200,
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ]
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                note = data.get('content', [{}])[0].get('text', '').strip()
                return note
            else:
                print(f'  Warning: API returned status {response.status_code}', file=sys.stderr)
                return None

        except Exception as e:
            print(f'  Warning: API request failed: {e}', file=sys.stderr)
            return None

    def generate_note_local(self, abstract: str) -> str:
        """Generate a simple note locally without API call.

        This is a fallback when no API is available.
        Creates a basic summary from the first sentence.

        Args:
            abstract: The abstract text

        Returns:
            Generated note
        """
        # Extract first sentence (simplified approach)
        sentences = re.split(r'(?<=[.!?])\s+', abstract)
        if sentences:
            first_sentence = sentences[0]
            # Truncate if too long
            if len(first_sentence) > 200:
                first_sentence = first_sentence[:200] + '...'
            return f"Key contribution: {first_sentence}"
        return "Paper contribution not extracted."

    def update_entry_with_note(self, entry: Dict, note: str) -> str:
        """Update a BibTeX entry with a generated note.

        Args:
            entry: Parsed entry dict
            note: Generated note text

        Returns:
            Updated BibTeX entry string
        """
        entry_type = entry.get('type', 'article')
        key = entry.get('key', 'unknown')
        fields = entry.get('fields', {}).copy()

        # Add/update note field
        fields['note'] = note

        # Field order for consistent output
        field_order = [
            'author', 'title', 'journal', 'booktitle', 'volume', 'number', 'pages',
            'year', 'month', 'citations', 'doi', 'url', 'issn', 'isbn', 'publisher',
            'eprint', 'archive', 'pmid', 'abstract', 'note', 'annotation'
        ]

        # Build new entry
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

    def generate_notes_for_library(self, bib_file: str, output_file: Optional[str] = None,
                                   force: bool = False, dry_run: bool = False,
                                   use_local: bool = False, verbose: bool = False) -> Dict:
        """Generate notes for all entries with abstracts in a BibTeX library.

        Args:
            bib_file: Path to BibTeX file
            output_file: Output file (default: overwrite input)
            force: Regenerate notes even if note field exists
            dry_run: Only print what would be done
            use_local: Use local note generation (no API)
            verbose: Show detailed progress

        Returns:
            Statistics dict
        """
        if output_file is None:
            output_file = bib_file

        entries = self.parse_bib_file(bib_file)

        stats = {
            'total': len(entries),
            'with_abstracts': 0,
            'without_abstracts': 0,
            'already_has_note': 0,
            'generated': 0,
            'failed': 0,
            'skipped': 0
        }

        print(f'\nProcessing {len(entries)} entries from {bib_file}', file=sys.stderr)
        print('=' * 50, file=sys.stderr)

        updated_entries = []

        for i, entry in enumerate(entries, 1):
            key = entry.get('key', 'unknown')
            fields = entry.get('fields', {})

            print(f'\n[{i}/{len(entries)}] {key}', file=sys.stderr)

            has_abstract = 'abstract' in fields and fields['abstract']
            has_note = 'note' in fields and fields['note']

            if has_abstract:
                stats['with_abstracts'] += 1
            else:
                stats['without_abstracts'] += 1
                if verbose:
                    print(f'  No abstract - skipping', file=sys.stderr)
                updated_entries.append(entry)
                stats['skipped'] += 1
                continue

            if has_note and not force:
                print(f'  Already has note - use --force to regenerate', file=sys.stderr)
                stats['already_has_note'] += 1
                updated_entries.append(entry)
                continue

            # Generate note
            abstract = fields['abstract']

            if dry_run:
                print(f'  Would generate note from abstract ({len(abstract)} chars)', file=sys.stderr)
                stats['generated'] += 1
                updated_entries.append(entry)
                continue

            if use_local:
                note = self.generate_note_local(abstract)
            else:
                note = self.generate_note_with_claude(abstract)

            if note:
                print(f'  Generated note: {note[:80]}...', file=sys.stderr)
                updated_bibtex = self.update_entry_with_note(entry, note)
                updated_entries.append({
                    'type': entry['type'],
                    'key': entry['key'],
                    'fields': {**fields, 'note': note},
                    'raw': updated_bibtex
                })
                stats['generated'] += 1
            else:
                print(f'  Failed to generate note', file=sys.stderr)
                updated_entries.append(entry)
                stats['failed'] += 1

        # Write output
        if not dry_run:
            # Create backup
            backup_file = bib_file + '.bak'
            try:
                import shutil
                shutil.copy2(bib_file, backup_file)
                if verbose:
                    print(f'\nBackup created: {backup_file}', file=sys.stderr)
            except Exception as e:
                print(f'Warning: Could not create backup: {e}', file=sys.stderr)

            # Write updated entries
            with open(output_file, 'w', encoding='utf-8') as f:
                for i, entry in enumerate(updated_entries):
                    if i > 0:
                        f.write('\n\n')
                    f.write(self._entry_to_bibtex(entry))

                f.write('\n')

            print(f'\nUpdated: {output_file}', file=sys.stderr)
        else:
            print(f'\nDry run - no changes made', file=sys.stderr)

        return stats

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

    def print_report(self, stats: Dict):
        """Print generation report."""
        print('\n' + '=' * 50, file=sys.stderr)
        print('Note Generation Report', file=sys.stderr)
        print('=' * 50, file=sys.stderr)
        print(f'Total entries: {stats["total"]}', file=sys.stderr)
        print(f'With abstracts: {stats["with_abstracts"]}', file=sys.stderr)
        print(f'Without abstracts: {stats["without_abstracts"]}', file=sys.stderr)
        print(f'Already had notes: {stats["already_has_note"]}', file=sys.stderr)
        print(f'Notes generated: {stats["generated"]}', file=sys.stderr)
        print(f'Failed: {stats["failed"]}', file=sys.stderr)
        print(f'Skipped: {stats["skipped"]}', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='Generate notes for BibTeX entries with abstracts using LLM.',
        epilog='Examples:\n'
                '  %(prog)s references.bib\n'
                '  %(prog)s references.bib --dry-run\n'
                '  %(prog)s references.bib --force --use-local'
    )
    parser.formatter_class = argparse.RawDescriptionHelpFormatter

    parser.add_argument(
        'bib_file',
        nargs='?',
        default='references.bib',
        help='BibTeX file to process (default: references.bib)'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output BibTeX file (default: overwrite input)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying file'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Regenerate notes even if note field exists'
    )

    parser.add_argument(
        '--use-local',
        action='store_true',
        help='Use local note generation (no API required)'
    )

    parser.add_argument(
        '--model',
        default='claude-3-haiku-20240307',
        help='Claude model to use (default: claude-3-haiku-20240307)'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='API request timeout in seconds (default: 30)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed progress'
    )

    args = parser.parse_args()

    # Create generator
    generator = BibNoteGenerator(model=args.model, timeout=args.timeout)

    # Run note generation
    stats = generator.generate_notes_for_library(
        args.bib_file,
        output_file=args.output,
        force=args.force,
        dry_run=args.dry_run,
        use_local=args.use_local,
        verbose=args.verbose
    )

    # Print report
    generator.print_report(stats)


if __name__ == '__main__':
    main()
