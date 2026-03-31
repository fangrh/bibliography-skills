#!/usr/bin/env python3
"""
Bibliography Utilities - Shared utility functions for bibliography operations.

This module provides functions for:
- Normalizing titles for comparison
- Detecting duplicate bibliography entries
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple, Optional


def normalize_title(title: str) -> str:
    """Normalize title for duplicate comparison.

    Removes special characters and converts to lowercase to enable
    case-insensitive comparison that ignores formatting differences.

    Args:
        title: The title string to normalize

    Returns:
        Normalized title with special characters removed and lowercased

    Examples:
        >>> normalize_title("A Paper Title!")
        'apapertitle'
        >>> normalize_title("Another: Paper Title")
        'anotherpapertitle'
        >>> normalize_title("Paper-Title_With.Mixed*Case")
        'papertitlewithmixedcase'
    """
    # Remove all non-alphanumeric characters and convert to lowercase
    normalized = re.sub(r'[^a-zA-Z0-9]', '', title.lower())
    return normalized


def _parse_entry_field(content: str, field: str) -> Optional[str]:
    """Parse a specific field from BibTeX entry content.

    Args:
        content: BibTeX entry content (fields and values)
        field: Field name to extract (e.g., 'author', 'title', 'year', 'doi')

    Returns:
        Field value as string, or None if field not found
    """
    # Try brace-delimited format first: field = {value}
    pattern = rf'{field}\s*=\s*\{{'
    match = re.search(pattern, content, re.IGNORECASE)
    if match:
        start = match.end()
        # Find balanced braces
        brace_depth = 1
        i = start
        while i < len(content) and brace_depth > 0:
            if content[i] == '{':
                brace_depth += 1
            elif content[i] == '}':
                brace_depth -= 1
            i += 1
        value = content[start:i - 1].strip()
        return re.sub(r'\s+', ' ', value)

    # Try quote-delimited format: field = "value"
    pattern = rf'{field}\s*=\s*"([^"]*)"'
    match = re.search(pattern, content, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None


def check_duplicates(papis_bib: Path) -> List[Tuple[str, str]]:
    """Find duplicate references in a BibTeX file.

    This function detects duplicates by comparing:
    1. DOI (exact match)
    2. Title (normalized comparison)
    3. Author + Year combination

    Returns pairs of citation keys that are duplicates. Each pair is returned
    only once (key1, key2 where key1 comes before key2 alphabetically).

    Args:
        papis_bib: Path to the BibTeX file to check

    Returns:
        List of duplicate key pairs as tuples (key1, key2)

    Raises:
        FileNotFoundError: If BibTeX file does not exist
        OSError: If file cannot be read
    """
    content = papis_bib.read_text(encoding='utf-8')

    # Parse all BibTeX entries
    entries = {}
    entry_pattern = r'@(\w+)\s*(?:\{|\(\{?)\s*(\w+)\s*,'

    for match in re.finditer(entry_pattern, content):
        entry_type = match.group(1)
        entry_key = match.group(2)
        entry_start = match.start()

        # Find the entry's opening brace
        open_brace = content.find('{', entry_start)
        if open_brace == -1:
            continue

        # Find the entry's closing brace
        brace_depth = 1
        i = open_brace + 1
        while i < len(content) and brace_depth > 0:
            if content[i] == '{':
                brace_depth += 1
            elif content[i] == '}':
                brace_depth -= 1
            i += 1

        entry_content = content[open_brace + 1:i - 1]

        # Extract relevant fields
        doi = _parse_entry_field(entry_content, 'doi')
        title = _parse_entry_field(entry_content, 'title')
        author = _parse_entry_field(entry_content, 'author')
        year = _parse_entry_field(entry_content, 'year')

        entries[entry_key] = {
            'doi': doi,
            'title': title,
            'normalized_title': normalize_title(title) if title else None,
            'author': author,
            'year': year,
        }

    # Find duplicates
    duplicates = set()
    keys = sorted(entries.keys())

    for i, key1 in enumerate(keys):
        entry1 = entries[key1]

        for key2 in keys[i + 1:]:
            entry2 = entries[key2]

            # Check DOI match
            if entry1['doi'] and entry2['doi']:
                if entry1['doi'].lower() == entry2['doi'].lower():
                    duplicates.add(tuple(sorted((key1, key2))))
                    continue

            # Check normalized title match
            if entry1['normalized_title'] and entry2['normalized_title']:
                if entry1['normalized_title'] == entry2['normalized_title']:
                    duplicates.add(tuple(sorted((key1, key2))))
                    continue

            # Check author + year match
            if entry1['author'] and entry1['year'] and entry2['author'] and entry2['year']:
                # Normalize authors for comparison (case-insensitive, minimal whitespace)
                author1_normalized = re.sub(r'\s+', ' ', entry1['author'].lower()).strip()
                author2_normalized = re.sub(r'\s+', ' ', entry2['author'].lower()).strip()
                if author1_normalized == author2_normalized and entry1['year'] == entry2['year']:
                    duplicates.add(tuple(sorted((key1, key2))))

    # Return sorted list of duplicates
    return sorted(duplicates)
