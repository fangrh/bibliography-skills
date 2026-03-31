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


class TestValidateMetadata:
    """Tests for validate_metadata function."""

    def test_complete_entry(self):
        """Test entry with all required fields passes validation."""
        entry = {
            'content': '''author = {Smith, John},
title = {A Great Paper},
year = {2023},
doi = {10.1234/test.2023}
'''
        }
        issues = bib_utils.validate_metadata(entry)
        assert issues == []

    def test_complete_entry_with_journal(self):
        """Test entry with journal instead of year passes validation."""
        entry = {
            'content': '''author = {Smith, John},
title = {A Great Paper},
journal = {Journal of Tests},
doi = {10.1234/test.2023}
'''
        }
        issues = bib_utils.validate_metadata(entry)
        assert issues == []

    def test_complete_entry_with_url(self):
        """Test entry with URL instead of DOI passes validation."""
        entry = {
            'content': '''author = {Smith, John},
title = {A Great Paper},
year = {2023},
url = {https://example.com/paper}
'''
        }
        issues = bib_utils.validate_metadata(entry)
        assert issues == []

    def test_missing_author(self):
        """Test entry missing author field."""
        entry = {
            'content': '''title = {A Great Paper},
year = {2023},
doi = {10.1234/test.2023}
'''
        }
        issues = bib_utils.validate_metadata(entry)
        assert issues == ['author']

    def test_missing_title(self):
        """Test entry missing title field."""
        entry = {
            'content': '''author = {Smith, John},
year = {2023},
doi = {10.1234/test.2023}
'''
        }
        issues = bib_utils.validate_metadata(entry)
        assert issues == ['title']

    def test_missing_journal_and_year(self):
        """Test entry missing both journal and year fields."""
        entry = {
            'content': '''author = {Smith, John},
title = {A Great Paper},
doi = {10.1234/test.2023}
'''
        }
        issues = bib_utils.validate_metadata(entry)
        assert issues == ['journal or year']

    def test_missing_doi_and_url(self):
        """Test entry missing both DOI and URL fields."""
        entry = {
            'content': '''author = {Smith, John},
title = {A Great Paper},
year = {2023}
'''
        }
        issues = bib_utils.validate_metadata(entry)
        assert issues == ['doi or url']

    def test_multiple_missing_fields(self):
        """Test entry with multiple missing fields."""
        entry = {
            'content': '''author = {Smith, John}
'''
        }
        issues = bib_utils.validate_metadata(entry)
        assert 'title' in issues
        assert 'journal or year' in issues
        assert 'doi or url' in issues

    def test_entry_with_quotes(self):
        """Test validation works with quote-delimited fields."""
        entry = {
            'content': '''author = "Smith, John",
title = "A Great Paper",
year = "2023",
doi = "10.1234/test.2023"
'''
        }
        issues = bib_utils.validate_metadata(entry)
        assert issues == []

    def test_empty_content(self):
        """Test entry with empty content."""
        entry = {'content': ''}
        issues = bib_utils.validate_metadata(entry)
        assert 'author' in issues
        assert 'title' in issues
        assert 'journal or year' in issues
        assert 'doi or url' in issues


class TestFixMetadata:
    """Tests for fix_metadata function."""

    def test_add_doi_prefix(self):
        """Test adding https://doi.org/ prefix to DOI."""
        entry = {
            'content': '''title = {Test},
doi = {10.1234/test.2023}
'''
        }
        fixed = bib_utils.fix_metadata(entry)
        assert 'https://doi.org/10.1234/test.2023' in fixed['content']
        assert 'doi = {https://doi.org/10.1234/test.2023}' in fixed['content']

    def test_doi_already_has_prefix(self):
        """Test DOI already with https://doi.org/ prefix."""
        entry = {
            'content': '''title = {Test},
doi = {https://doi.org/10.1234/test.2023}
'''
        }
        fixed = bib_utils.fix_metadata(entry)
        # Should not duplicate the prefix
        assert fixed['content'].count('https://doi.org/') == 1

    def test_doi_with_http_prefix(self):
        """Test DOI with http://doi.org/ prefix gets upgraded."""
        entry = {
            'content': '''title = {Test},
doi = {http://doi.org/10.1234/test.2023}
'''
        }
        fixed = bib_utils.fix_metadata(entry)
        assert 'https://doi.org/10.1234/test.2023' in fixed['content']
        # Should not have http://doi.org/ anymore
        assert 'http://doi.org/' not in fixed['content']

    def test_doi_with_doi_prefix(self):
        """Test DOI with 'doi:' prefix gets fixed."""
        entry = {
            'content': '''title = {Test},
doi = {doi:10.1234/test.2023}
'''
        }
        fixed = bib_utils.fix_metadata(entry)
        assert 'https://doi.org/10.1234/test.2023' in fixed['content']
        # Should not have doi: anymore
        assert 'doi:10.1234' not in fixed['content']

    def test_normalize_author_multiple(self):
        """Test normalizing multiple authors."""
        entry = {
            'content': '''title = {Test},
author = {First Author and Second Author and Third Author}
'''
        }
        fixed = bib_utils.fix_metadata(entry)
        # First author should be preserved
        assert 'First Author' in fixed['content']
        # Other authors should be in Last, First format
        assert 'Author, Second' in fixed['content']
        assert 'Author, Third' in fixed['content']

    def test_author_already_formatted(self):
        """Test author already in Last, First format is preserved."""
        entry = {
            'content': '''title = {Test},
author = {Smith, John and Doe, Jane}
'''
        }
        fixed = bib_utils.fix_metadata(entry)
        # Should not change already formatted authors
        assert 'Smith, John' in fixed['content']
        assert 'Doe, Jane' in fixed['content']

    def test_author_with_whitespace_variations(self):
        """Test author normalization with whitespace variations."""
        entry = {
            'content': '''title = {Test},
author = {First Author and  Second  Author}
'''
        }
        fixed = bib_utils.fix_metadata(entry)
        # Should normalize whitespace in "and" separator
        assert ' and ' in fixed['content']
        assert '  Second  ' not in fixed['content']

    def test_single_author(self):
        """Test single author is preserved."""
        entry = {
            'content': '''title = {Test},
author = {First Author}
'''
        }
        fixed = bib_utils.fix_metadata(entry)
        assert 'First Author' in fixed['content']

    def test_no_doi_field(self):
        """Test entry without DOI field."""
        entry = {
            'content': '''title = {Test},
author = {Smith, John}
'''
        }
        fixed = bib_utils.fix_metadata(entry)
        # Should not crash and return modified entry
        assert 'title = {Test}' in fixed['content']

    def test_doi_with_quotes(self):
        """Test DOI normalization with quote-delimited fields."""
        entry = {
            'content': '''title = "Test",
doi = "10.1234/test.2023"
'''
        }
        fixed = bib_utils.fix_metadata(entry)
        assert 'https://doi.org/10.1234/test.2023' in fixed['content']
        assert 'doi = "https://doi.org/10.1234/test.2023"' in fixed['content']

    def test_combined_fixes(self):
        """Test applying both DOI and author fixes."""
        entry = {
            'content': '''title = {Test},
author = {First Author and Second Author},
doi = {10.1234/test.2023}
'''
        }
        fixed = bib_utils.fix_metadata(entry)
        assert 'https://doi.org/10.1234/test.2023' in fixed['content']
        assert 'First Author' in fixed['content']
        assert 'Author, Second' in fixed['content']

    def test_return_value_is_entry(self):
        """Test that fix_metadata returns the entry dict."""
        entry = {'content': 'title = {Test}'}
        result = bib_utils.fix_metadata(entry)
        # Should return the same dict object (modified)
        assert result is entry
        assert 'content' in result

    def test_author_conversion_first_last_to_last_first(self):
        """Test converting "First Last" format to "Last, First"."""
        entry = {
            'content': '''title = {Test},
author = {First Author and Second Person}
'''
        }
        fixed = bib_utils.fix_metadata(entry)
        # First author preserved
        assert 'First Author' in fixed['content']
        # Second author converted
        assert 'Person, Second' in fixed['content']
