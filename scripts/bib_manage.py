#!/usr/bin/env python3
"""
Bibliography Management CLI - Command-line interface for bibliography operations.

This script provides a unified CLI for managing papis bibliography libraries,
including duplicate checking, syncing, metadata validation, and migration.
"""

import argparse
import sys
from pathlib import Path
from typing import Set

# Import utilities from bib_utils module
from bib_utils import (
    check_duplicates,
    sync_to_main,
    validate_metadata,
    migrate_bib,
    read_bibtex,
)


def cmd_check_duplicates(args: argparse.Namespace) -> int:
    """Handle check-duplicates action.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for duplicates found, 2 for error)
    """
    bib_path = Path(args.bib)
    if not bib_path.exists():
        print(f"Error: BibTeX file not found: {bib_path}", file=sys.stderr)
        return 2

    try:
        duplicates = check_duplicates(bib_path)
        if duplicates:
            print(f"Found {len(duplicates)} duplicate pair(s):")
            for key1, key2 in duplicates:
                print(f"  - {key1} <-> {key2}")
            return 1
        else:
            print("No duplicates found.")
            return 0
    except Exception as e:
        print(f"Error checking duplicates: {e}", file=sys.stderr)
        return 2


def cmd_sync_to_main(args: argparse.Namespace) -> int:
    """Handle sync-to-main action.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 2 for error)
    """
    papis_bib = Path(args.papis_bib)
    main_bib = Path(args.main_bib)

    if not papis_bib.exists():
        print(f"Error: papis bibliography file not found: {papis_bib}", file=sys.stderr)
        return 2

    # Read cited keys from file or use provided list
    cited_keys: Set[str] = set()

    if args.cited_keys_file:
        cited_file = Path(args.cited_keys_file)
        if not cited_file.exists():
            print(f"Error: Cited keys file not found: {cited_file}", file=sys.stderr)
            return 2
        cited_keys = set(line.strip() for line in cited_file.read_text(encoding='utf-8').splitlines() if line.strip())
    elif args.cited_keys:
        cited_keys = set(args.cited_keys)
    else:
        print("Error: Either --cited-keys-file or --cited-keys is required", file=sys.stderr)
        return 2

    try:
        sync_to_main(papis_bib, main_bib, cited_keys)
        print(f"Synced {len(cited_keys)} cited reference(s) to {main_bib}")
        return 0
    except Exception as e:
        print(f"Error syncing to main: {e}", file=sys.stderr)
        return 2


def cmd_validate_metadata(args: argparse.Namespace) -> int:
    """Handle validate-metadata action.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for validation issues, 2 for error)
    """
    bib_path = Path(args.bib)
    if not bib_path.exists():
        print(f"Error: BibTeX file not found: {bib_path}", file=sys.stderr)
        return 2

    try:
        entries = read_bibtex(bib_path)
        issues_found = False

        for entry in entries:
            issues = validate_metadata(entry)
            if issues:
                issues_found = True
                print(f"{entry['key']}: Missing/invalid - {', '.join(issues)}")

        if issues_found:
            return 1
        else:
            print("All entries have valid metadata.")
            return 0
    except Exception as e:
        print(f"Error validating metadata: {e}", file=sys.stderr)
        return 2


def cmd_cleanup(args: argparse.Namespace) -> int:
    """Handle cleanup action (placeholder for future implementation).

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (2 - not implemented yet)
    """
    print("Error: cleanup action is not yet implemented", file=sys.stderr)
    return 2


def cmd_migrate(args: argparse.Namespace) -> int:
    """Handle migrate action.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 2 for error)
    """
    source_bib = Path(args.source)
    papis_lib_dir = Path(args.library)

    if not source_bib.exists():
        print(f"Error: Source BibTeX file not found: {source_bib}", file=sys.stderr)
        return 2

    try:
        papis_bib = migrate_bib(source_bib, papis_lib_dir)
        print(f"Migrated entries from {source_bib} to {papis_bib}")
        return 0
    except Exception as e:
        print(f"Error migrating BibTeX: {e}", file=sys.stderr)
        return 2


def main() -> int:
    """Main entry point for the bibliography management CLI.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(
        description='Manage papis bibliography',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='action', help='Available actions')

    # check-duplicates action
    dup_parser = subparsers.add_parser(
        'check-duplicates',
        help='Find duplicate entries in BibTeX file'
    )
    dup_parser.add_argument(
        '--bib',
        default='papis.bib',
        help='BibTeX file to check (default: papis.bib)'
    )

    # sync-to-main action
    sync_parser = subparsers.add_parser(
        'sync-to-main',
        help='Sync cited references from papis.bib to main.bib'
    )
    sync_parser.add_argument(
        '--papis-bib',
        default='papis.bib',
        help='Path to papis bibliography file (default: papis.bib)'
    )
    sync_parser.add_argument(
        '--main-bib',
        default='main.bib',
        help='Path to main bibliography file (default: main.bib)'
    )
    sync_keys = sync_parser.add_mutually_exclusive_group(required=True)
    sync_keys.add_argument(
        '--cited-keys-file',
        help='File containing citation keys (one per line)'
    )
    sync_keys.add_argument(
        '--cited-keys',
        nargs='+',
        help='List of citation keys (space-separated)'
    )

    # validate-metadata action
    validate_parser = subparsers.add_parser(
        'validate-metadata',
        help='Validate metadata in BibTeX file'
    )
    validate_parser.add_argument(
        '--bib',
        default='papis.bib',
        help='BibTeX file to validate (default: papis.bib)'
    )

    # cleanup action (placeholder)
    cleanup_parser = subparsers.add_parser(
        'cleanup',
        help='Clean up orphaned or invalid entries (not yet implemented)'
    )

    # migrate action
    migrate_parser = subparsers.add_parser(
        'migrate',
        help='Migrate BibTeX file to papis library'
    )
    migrate_parser.add_argument(
        'source',
        help='Source BibTeX file to migrate'
    )
    migrate_parser.add_argument(
        '--library',
        default='~/.papis/library',
        help='Path to papis library directory (default: ~/.papis/library)'
    )

    # Parse arguments
    args = parser.parse_args()

    # Dispatch to appropriate action
    if args.action == 'check-duplicates':
        return cmd_check_duplicates(args)
    elif args.action == 'sync-to-main':
        return cmd_sync_to_main(args)
    elif args.action == 'validate-metadata':
        return cmd_validate_metadata(args)
    elif args.action == 'cleanup':
        return cmd_cleanup(args)
    elif args.action == 'migrate':
        return cmd_migrate(args)
    else:
        parser.print_help()
        return 2


if __name__ == '__main__':
    sys.exit(main())
