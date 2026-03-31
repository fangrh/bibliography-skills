"""Tests for bib_utils.py - Bibliography utility functions."""

import pytest
from pathlib import Path
import sys

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / 'scripts'
sys.path.insert(0, str(scripts_dir))

import bib_utils


class TestNormalizeTitle:
    """Tests for normalize_title function."""

    def test_basic_normalization(self):
        """Test basic title normalization."""
        assert bib_utils.normalize_title("A Paper Title") == "apapertitle"

    def test_lowercase_conversion(self):
        """Test lowercase conversion."""
        assert bib_utils.normalize_title("UPPERCASE Title") == "uppercasetitle"

    def test_special_char_removal(self):
        """Test removal of special characters."""
        assert bib_utils.normalize_title("Paper: Title!") == "papertitle"
        assert bib_utils.normalize_title("Title-With-Hyphens") == "titlewithhyphens"
        assert bib_utils.normalize_title("Title_Underscore") == "titleunderscore"
        assert bib_utils.normalize_title("Title.With.Dots") == "titlewithdots"

    def test_punctuation_removal(self):
        """Test removal of punctuation."""
        assert bib_utils.normalize_title("Hello, World!") == "helloworld"
        assert bib_utils.normalize_title("Question? Answer.") == "questionanswer"

    def test_whitespace_handling(self):
        """Test whitespace handling."""
        assert bib_utils.normalize_title("Title   With    Spaces") == "titlewithspaces"
        assert bib_utils.normalize_title("  Leading Space") == "leadingspace"
        assert bib_utils.normalize_title("Trailing Space  ") == "trailingspace"

    def test_empty_string(self):
        """Test empty string input."""
        assert bib_utils.normalize_title("") == ""

    def test_only_special_chars(self):
        """Test string with only special characters."""
        assert bib_utils.normalize_title("!!!@@@###") == ""

    def test_numbers_preserved(self):
        """Test that numbers are preserved."""
        assert bib_utils.normalize_title("Paper 2023 Title") == "paper2023title"
        assert bib_utils.normalize_title("Version 1.2.3") == "version123"


class TestCheckDuplicates:
    """Tests for check_duplicates function."""

    def test_no_duplicates(self, tmp_path):
        """Test file with no duplicates."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{smith2023,
    author = {Smith, John},
    title = {First Paper},
    year = {2023},
    doi = {10.1234/first.2023}
}

@article{jones2024,
    author = {Jones, Jane},
    title = {Second Paper},
    year = {2024},
    doi = {10.1234/second.2024}
}
''', encoding='utf-8')

        duplicates = bib_utils.check_duplicates(bib_file)
        assert duplicates == []

    def test_duplicate_by_doi(self, tmp_path):
        """Test detection of duplicates by DOI."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{smith2023a,
    author = {Smith, John},
    title = {First Paper},
    year = {2023},
    doi = {10.1234/same.doi}
}

@article{smith2023b,
    author = {Smith, John},
    title = {Same Paper Different Title},
    year = {2023},
    doi = {10.1234/same.doi}
}
''', encoding='utf-8')

        duplicates = bib_utils.check_duplicates(bib_file)
        assert len(duplicates) == 1
        assert ('smith2023a', 'smith2023b') in duplicates

    def test_duplicate_by_title(self, tmp_path):
        """Test detection of duplicates by normalized title."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{paper1,
    author = {Smith, John},
    title = {A Great Paper Title},
    year = {2023}
}

@article{paper2,
    author = {Jones, Jane},
    title = {A Great Paper Title!},
    year = {2024}
}
''', encoding='utf-8')

        duplicates = bib_utils.check_duplicates(bib_file)
        assert len(duplicates) == 1
        assert ('paper1', 'paper2') in duplicates

    def test_duplicate_by_author_year(self, tmp_path):
        """Test detection of duplicates by author + year."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{paper1,
    author = {Smith, John},
    title = {First Paper},
    year = {2023}
}

@article{paper2,
    author = {Smith, John},
    title = {Second Paper},
    year = {2023}
}
''', encoding='utf-8')

        duplicates = bib_utils.check_duplicates(bib_file)
        assert len(duplicates) == 1
        assert ('paper1', 'paper2') in duplicates

    def test_multiple_duplicates(self, tmp_path):
        """Test detection of multiple duplicate pairs."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{dup1a,
    author = {Smith, John},
    title = {Same Title},
    year = {2023},
    doi = {10.1234/one}
}

@article{dup1b,
    author = {Jones, Jane},
    title = {Same Title},
    year = {2023}
}

@article{dup2a,
    author = {Brown, Bob},
    title = {Another Paper},
    year = {2022},
    doi = {10.1234/two}
}

@article{dup2b,
    author = {Brown, Bob},
    title = {Another Paper},
    year = {2022},
    doi = {10.1234/two}
}
''', encoding='utf-8')

        duplicates = bib_utils.check_duplicates(bib_file)
        assert len(duplicates) == 2
        assert ('dup1a', 'dup1b') in duplicates
        assert ('dup2a', 'dup2b') in duplicates

    def test_duplicate_with_title_variations(self, tmp_path):
        """Test that title variations normalize correctly."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{paper1,
    author = {Smith, John},
    title = {Paper: Title with Special-Chars!}
}

@article{paper2,
    author = {Jones, Jane},
    title = {Paper   Title   with   Special   Chars}
}
''', encoding='utf-8')

        duplicates = bib_utils.check_duplicates(bib_file)
        assert len(duplicates) == 1
        assert ('paper1', 'paper2') in duplicates

    def test_duplicate_with_whitespace_in_author(self, tmp_path):
        """Test that whitespace in authors is normalized."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{paper1,
    author = {Smith,   John},
    title = {First},
    year = {2023}
}

@article{paper2,
    author = {Smith, John},
    title = {Second},
    year = {2023}
}
''', encoding='utf-8')

        duplicates = bib_utils.check_duplicates(bib_file)
        assert len(duplicates) == 1
        assert ('paper1', 'paper2') in duplicates

    def test_no_duplicate_different_doi(self, tmp_path):
        """Test that different DOIs are not detected as duplicates."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{paper1,
    author = {Smith, John},
    title = {Paper Title},
    year = {2023},
    doi = {10.1234/first}
}

@article{paper2,
    author = {Smith, John},
    title = {Paper Title},
    year = {2023},
    doi = {10.1234/second}
}
''', encoding='utf-8')

        duplicates = bib_utils.check_duplicates(bib_file)
        # Should still be duplicate by title
        assert len(duplicates) == 1
        assert ('paper1', 'paper2') in duplicates

    def test_case_insensitive_doi(self, tmp_path):
        """Test that DOI comparison is case-insensitive."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{paper1,
    author = {Smith, John},
    title = {First},
    year = {2023},
    doi = {10.1234/ABC}
}

@article{paper2,
    author = {Jones, Jane},
    title = {Second},
    year = {2024},
    doi = {10.1234/abc}
}
''', encoding='utf-8')

        duplicates = bib_utils.check_duplicates(bib_file)
        assert len(duplicates) == 1
        assert ('paper1', 'paper2') in duplicates

    def test_missing_fields_no_duplicate(self, tmp_path):
        """Test that missing fields don't cause false positives."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{paper1,
    author = {Smith, John},
    title = {First Paper}
}

@article{paper2,
    author = {Jones, Jane},
    title = {Second Paper}
}
''', encoding='utf-8')

        duplicates = bib_utils.check_duplicates(bib_file)
        assert duplicates == []

    def test_three_way_duplicates(self, tmp_path):
        """Test detection when three entries are duplicates."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{paper1,
    author = {Smith, John},
    title = {Same Title},
    year = {2023}
}

@article{paper2,
    author = {Smith, John},
    title = {Same Title},
    year = {2023}
}

@article{paper3,
    author = {Smith, John},
    title = {Same Title},
    year = {2023}
}
''', encoding='utf-8')

        duplicates = bib_utils.check_duplicates(bib_file)
        # Should return all pairs
        assert len(duplicates) == 3
        assert ('paper1', 'paper2') in duplicates
        assert ('paper1', 'paper3') in duplicates
        assert ('paper2', 'paper3') in duplicates

    def test_nonexistent_file(self, tmp_path):
        """Test that FileNotFoundError is raised for non-existent file."""
        bib_file = tmp_path / 'nonexistent.bib'

        with pytest.raises(FileNotFoundError):
            bib_utils.check_duplicates(bib_file)

    def test_duplicate_pairs_sorted(self, tmp_path):
        """Test that duplicate pairs are returned with keys sorted alphabetically."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{zebra,
    author = {Smith, John},
    title = {Same Title},
    year = {2023}
}

@article{alpha,
    author = {Smith, John},
    title = {Same Title},
    year = {2023}
}
''', encoding='utf-8')

        duplicates = bib_utils.check_duplicates(bib_file)
        assert len(duplicates) == 1
        # Keys should be sorted alphabetically
        assert duplicates[0] == ('alpha', 'zebra')

    def test_bibtex_with_quotes(self, tmp_path):
        """Test parsing BibTeX entries with quote-delimited fields."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{paper1,
    author = "Smith, John",
    title = "Same Title",
    year = "2023"
}

@article{paper2,
    author = "Smith, John",
    title = "Same Title",
    year = "2023"
}
''', encoding='utf-8')

        duplicates = bib_utils.check_duplicates(bib_file)
        assert len(duplicates) == 1
        assert ('paper1', 'paper2') in duplicates

    def test_mixed_entry_types(self, tmp_path):
        """Test duplicates across different entry types."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{smith2023_article,
    author = {Smith, John},
    title = {Same Title},
    year = {2023}
}

@inproceedings{smith2023_conf,
    author = {Smith, John},
    title = {Same Title},
    year = {2023}
}
''', encoding='utf-8')

        duplicates = bib_utils.check_duplicates(bib_file)
        assert len(duplicates) == 1
        assert ('smith2023_article', 'smith2023_conf') in duplicates
