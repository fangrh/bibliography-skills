#!/usr/bin/env python3
"""Tests for bib_manage CLI script."""

import argparse
import tempfile
import sys
from pathlib import Path
from typing import Any

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from bib_utils import check_duplicates, sync_to_main, validate_metadata, read_bibtex, write_bibtex


class TestCheckDuplicatesCommand:
    """Test the check-duplicates command functionality."""

    def test_check_duplicates_no_duplicates(self, tmp_path: Path) -> None:
        """Test check_duplicates with no duplicates."""
        bib_file = tmp_path / 'test.bib'
        bib_content = """@article{smith2023test,
  author = {Smith, John},
  title = {A Test Paper},
  year = {2023}
}

@article{jones2024another,
  author = {Jones, Jane},
  title = {Another Paper},
  year = {2024}
}
"""
        bib_file.write_text(bib_content, encoding='utf-8')

        duplicates = check_duplicates(bib_file)
        assert duplicates == []

    def test_check_duplicates_with_duplicates(self, tmp_path: Path) -> None:
        """Test check_duplicates with duplicate entries."""
        bib_file = tmp_path / 'test.bib'
        bib_content = """@article{smith2023test,
  author = {Smith, John},
  title = {A Test Paper},
  year = {2023}
}

@article{smith2023duplicate,
  author = {Smith, John},
  title = {A Test Paper},
  year = {2023}
}

@article{jones2024paper,
  author = {Jones, Jane},
  title = {Another Paper},
  year = {2024}
}
"""
        bib_file.write_text(bib_content, encoding='utf-8')

        duplicates = check_duplicates(bib_file)
        assert len(duplicates) == 1
        assert set(duplicates[0]) == {'smith2023test', 'smith2023duplicate'}


class TestSyncToMainCommand:
    """Test the sync-to-main command functionality."""

    def test_sync_to_main_filters_by_cited_keys(self, tmp_path: Path) -> None:
        """Test sync_to_main only includes cited keys."""
        papis_bib = tmp_path / 'papis.bib'
        main_bib = tmp_path / 'main.bib'

        papis_content = """@article{smith2023test,
  author = {Smith, John},
  title = {A Test Paper},
  year = {2023}
}

@article{jones2024another,
  author = {Jones, Jane},
  title = {Another Paper},
  year = {2024}
}

@article{brown2025third,
  author = {Brown, Bob},
  title = {Third Paper},
  year = {2025}
}
"""
        papis_bib.write_text(papis_content, encoding='utf-8')

        cited_keys = {'smith2023test', 'brown2025third'}
        sync_to_main(papis_bib, main_bib, cited_keys)

        # Verify main.bib contains only cited entries
        main_entries = read_bibtex(main_bib)
        main_keys = {entry['key'] for entry in main_entries}
        assert main_keys == cited_keys

    def test_sync_to_main_empty_cited_keys(self, tmp_path: Path) -> None:
        """Test sync_to_main with no cited keys."""
        papis_bib = tmp_path / 'papis.bib'
        main_bib = tmp_path / 'main.bib'

        papis_content = """@article{smith2023test,
  author = {Smith, John},
  title = {A Test Paper},
  year = {2023}
}
"""
        papis_bib.write_text(papis_content, encoding='utf-8')

        sync_to_main(papis_bib, main_bib, set())

        # Verify main.bib is empty or doesn't exist
        if main_bib.exists():
            main_entries = read_bibtex(main_bib)
            assert len(main_entries) == 0


class TestValidateMetadataCommand:
    """Test the validate-metadata command functionality."""

    def test_validate_metadata_valid_entry(self) -> None:
        """Test validate_metadata with valid entry."""
        entry = {
            'type': 'article',
            'key': 'smith2023',
            'content': 'author = {Smith, John}\ntitle = {A Test Paper}\nyear = {2023}\ndoi = {10.1234/test}'
        }
        issues = validate_metadata(entry)
        assert issues == []

    def test_validate_metadata_missing_author(self) -> None:
        """Test validate_metadata with missing author."""
        entry = {
            'type': 'article',
            'key': 'test2023',
            'content': 'title = {A Test Paper}\nyear = {2023}'
        }
        issues = validate_metadata(entry)
        assert 'author' in issues

    def test_validate_metadata_missing_title(self) -> None:
        """Test validate_metadata with missing title."""
        entry = {
            'type': 'article',
            'key': 'test2023',
            'content': 'author = {Smith, John}\nyear = {2023}'
        }
        issues = validate_metadata(entry)
        assert 'title' in issues

    def test_validate_metadata_missing_journal_or_year(self) -> None:
        """Test validate_metadata with missing journal and year."""
        entry = {
            'type': 'article',
            'key': 'test2023',
            'content': 'author = {Smith, John}\ntitle = {A Test Paper}'
        }
        issues = validate_metadata(entry)
        assert 'journal or year' in issues

    def test_validate_metadata_missing_doi_or_url(self) -> None:
        """Test validate_metadata with missing doi and url."""
        entry = {
            'type': 'article',
            'key': 'test2023',
            'content': 'author = {Smith, John}\ntitle = {A Test Paper}\nyear = {2023}'
        }
        issues = validate_metadata(entry)
        assert 'doi or url' in issues


class TestCLIArgumentParsing:
    """Test that the CLI can be imported and basic structure exists."""

    def test_imports_bib_utils(self) -> None:
        """Test that bib_manage can import bib_utils functions."""
        # This test verifies the module can be imported
        from bib_utils import check_duplicates, sync_to_main, validate_metadata, migrate_bib
        assert callable(check_duplicates)
        assert callable(sync_to_main)
        assert callable(validate_metadata)
        assert callable(migrate_bib)

    def test_bib_manage_imports(self) -> None:
        """Test that bib_manage module can be imported."""
        import bib_manage
        assert hasattr(bib_manage, 'main')
        assert callable(bib_manage.main)
        assert hasattr(bib_manage, 'cmd_check_duplicates')
        assert hasattr(bib_manage, 'cmd_sync_to_main')
        assert hasattr(bib_manage, 'cmd_validate_metadata')
