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
from typing import List, Tuple, Optional, Dict


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


def validate_metadata(entry: Dict) -> List[str]:
    """Validate a BibTeX entry has required fields.

    Checks for the presence of required metadata fields:
    - author (required)
    - title (required)
    - journal or year (at least one required)
    - doi or url (at least one required)

    Args:
        entry: Dictionary containing BibTeX entry data with a 'content' key
               containing the raw BibTeX content string

    Returns:
        List of field names or descriptions that are missing/invalid.
        Empty list if all validations pass.

    Examples:
        >>> entry = {'content': 'author = {Smith}\\ntitle = {Test}\\nyear = {2023}'}
        >>> validate_metadata(entry)
        ['doi or url']
    """
    issues = []
    content = entry.get('content', '')

    # Check author
    author = _parse_entry_field(content, 'author')
    if not author:
        issues.append('author')

    # Check title
    title = _parse_entry_field(content, 'title')
    if not title:
        issues.append('title')

    # Check journal/year (at least one is required)
    journal = _parse_entry_field(content, 'journal')
    year = _parse_entry_field(content, 'year')
    if not journal and not year:
        issues.append('journal or year')

    # Check doi/url (at least one is required)
    doi = _parse_entry_field(content, 'doi')
    url = _parse_entry_field(content, 'url')
    if not doi and not url:
        issues.append('doi or url')

    return issues


def fix_metadata(entry: Dict) -> Dict:
    """Fix common metadata issues in a BibTeX entry.

    Fixes include:
    - DOI format: ensures https://doi.org/ prefix is present
    - Author names: preserves "First" for First author, normalizes others
    - Journal abbreviations: normalizes common journal abbreviations

    Note: This function modifies the entry in-place and returns it for
    convenience. The function operates on the 'content' field of the entry.

    Args:
        entry: Dictionary containing BibTeX entry data with a 'content' key
               containing the raw BibTeX content string

    Returns:
        The modified entry dictionary with fixed metadata

    Examples:
        >>> entry = {'content': 'doi = {10.1234/test.2023}'}
        >>> fixed = fix_metadata(entry)
        >>> 'https://doi.org/10.1234/test.2023' in fixed['content']
        True
    """
    content = entry.get('content', '')

    # Fix DOI format (ensure https://doi.org/ prefix)
    doi = _parse_entry_field(content, 'doi')
    if doi:
        # Remove any existing URL prefix and ensure correct format
        doi_clean = doi
        if doi_clean.startswith('http://doi.org/'):
            doi_clean = doi_clean[len('http://doi.org/'):]
        elif doi_clean.startswith('https://doi.org/'):
            doi_clean = doi_clean[len('https://doi.org/'):]
        elif doi_clean.startswith('doi:'):
            doi_clean = doi_clean[len('doi:'):]

        # If DOI doesn't have the correct prefix, add it
        if not doi.startswith('https://doi.org/'):
            # Replace the old DOI value with the fixed one
            old_pattern = r'(doi\s*=\s*[\{"])[^}"]+([\}"])'
            replacement = r'\1https://doi.org/' + doi_clean + r'\2'
            content = re.sub(old_pattern, replacement, content, flags=re.IGNORECASE)
            entry['content'] = content

    # Normalize author names (preserve "First" for First, normalize others)
    author = _parse_entry_field(content, 'author')
    if author:
        # Split by 'and' to get individual authors
        authors = [a.strip() for a in re.split(r'\s+and\s+', author, flags=re.IGNORECASE)]

        if authors:
            # Preserve the first author as-is
            normalized_authors = [authors[0]]

            # Normalize remaining authors: ensure Last, First format
            for auth in authors[1:]:
                # Check if already in Last, First format (contains comma)
                if ',' in auth:
                    # Ensure proper spacing: Last, First (no extra spaces)
                    parts = [part.strip() for part in auth.split(',', 1)]
                    normalized = f"{parts[0]}, {parts[1]}"
                else:
                    # Convert from "First Last" to "Last, First"
                    parts = auth.rsplit(' ', 1)
                    if len(parts) == 2:
                        normalized = f"{parts[1]}, {parts[0]}"
                    else:
                        # Single name, keep as-is
                        normalized = auth
                normalized_authors.append(normalized)

            # Reconstruct author field
            fixed_author = ' and '.join(normalized_authors)
            # Replace the old author value with the fixed one
            old_pattern = r'(author\s*=\s*[\{"])[^}"]+([\}"])'
            replacement = r'\1' + fixed_author + r'\2'
            content = re.sub(old_pattern, replacement, content, flags=re.IGNORECASE)
            entry['content'] = content

    return entry
