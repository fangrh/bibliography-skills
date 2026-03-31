"""Tests for bib_utils.py - Bibliography utility functions."""

import subprocess
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
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


class TestSyncToMain:
    """Tests for sync_to_main function."""

    def test_sync_cited_entries(self, tmp_path):
        """Test syncing only cited entries to main.bib."""
        papis_bib = tmp_path / 'papis.bib'
        main_bib = tmp_path / 'main.bib'

        papis_bib.write_text('''
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

@article{brown2022,
    author = {Brown, Bob},
    title = {Third Paper},
    year = {2022},
    doi = {10.1234/third.2022}
}
''', encoding='utf-8')

        # Only cite smith2023 and brown2022
        cited_keys = {'smith2023', 'brown2022'}

        bib_utils.sync_to_main(papis_bib, main_bib, cited_keys)

        # Read the main.bib file and check contents
        main_content = main_bib.read_text(encoding='utf-8')

        # Should contain smith2023 and brown2022
        assert '@article{smith2023,' in main_content
        assert '@article{brown2022,' in main_content

        # Should NOT contain jones2024 (not cited)
        assert '@article{jones2024,' not in main_content

    def test_sync_all_cited(self, tmp_path):
        """Test syncing when all entries are cited."""
        papis_bib = tmp_path / 'papis.bib'
        main_bib = tmp_path / 'main.bib'

        papis_bib.write_text('''
@article{paper1,
    author = {Author One},
    title = {Title One},
    year = {2023}
}

@article{paper2,
    author = {Author Two},
    title = {Title Two},
    year = {2024}
}
''', encoding='utf-8')

        # Cite all entries
        cited_keys = {'paper1', 'paper2'}

        bib_utils.sync_to_main(papis_bib, main_bib, cited_keys)

        main_content = main_bib.read_text(encoding='utf-8')

        # Should contain both entries
        assert '@article{paper1,' in main_content
        assert '@article{paper2,' in main_content

    def test_sync_none_cited(self, tmp_path):
        """Test syncing when no entries are cited."""
        papis_bib = tmp_path / 'papis.bib'
        main_bib = tmp_path / 'main.bib'

        papis_bib.write_text('''
@article{paper1,
    author = {Author One},
    title = {Title One},
    year = {2023}
}
''', encoding='utf-8')

        # No entries cited
        cited_keys = set()

        bib_utils.sync_to_main(papis_bib, main_bib, cited_keys)

        main_content = main_bib.read_text(encoding='utf-8')

        # Should be empty (only whitespace)
        assert main_content.strip() == ''

    def test_sync_preserves_entry_structure(self, tmp_path):
        """Test that synced entries preserve their structure."""
        papis_bib = tmp_path / 'papis.bib'
        main_bib = tmp_path / 'main.bib'

        papis_bib.write_text('''
@article{smith2023,
    author = {Smith, John and Doe, Jane},
    title = {A Complex Paper Title: With Subtitle},
    journal = {Journal of Tests},
    year = {2023},
    volume = {42},
    number = {3},
    pages = {123--145},
    doi = {10.1234/test.2023}
}
''', encoding='utf-8')

        cited_keys = {'smith2023'}

        bib_utils.sync_to_main(papis_bib, main_bib, cited_keys)

        main_content = main_bib.read_text(encoding='utf-8')

        # Check that all fields are present
        assert 'author = {Smith, John and Doe, Jane}' in main_content
        assert 'title = {A Complex Paper Title: With Subtitle}' in main_content
        assert 'journal = {Journal of Tests}' in main_content
        assert 'year = {2023}' in main_content
        assert 'volume = {42}' in main_content
        assert 'number = {3}' in main_content
        assert 'pages = {123--145}' in main_content
        assert 'doi = {10.1234/test.2023}' in main_content

    def test_sync_overwrites_existing_main(self, tmp_path):
        """Test that sync overwrites existing main.bib content."""
        papis_bib = tmp_path / 'papis.bib'
        main_bib = tmp_path / 'main.bib'

        # Create initial papis.bib
        papis_bib.write_text('''
@article{new2025,
    author = {New Author},
    title = {New Paper},
    year = {2025}
}
''', encoding='utf-8')

        # Create existing main.bib with old content
        main_bib.write_text('''
@article{old2020,
    author = {Old Author},
    title = {Old Paper},
    year = {2020}
}
''', encoding='utf-8')

        cited_keys = {'new2025'}

        bib_utils.sync_to_main(papis_bib, main_bib, cited_keys)

        main_content = main_bib.read_text(encoding='utf-8')

        # Should have new content
        assert '@article{new2025,' in main_content
        # Old content should be gone
        assert '@article{old2020,' not in main_content

    def test_sync_multiple_entry_types(self, tmp_path):
        """Test syncing entries of different types."""
        papis_bib = tmp_path / 'papis.bib'
        main_bib = tmp_path / 'main.bib'

        papis_bib.write_text('''
@article{article2023,
    author = {Author One},
    title = {Journal Article},
    journal = {Journal},
    year = {2023}
}

@book{book2022,
    author = {Author Two},
    title = {Book Title},
    publisher = {Publisher},
    year = {2022}
}

@inproceedings{conf2024,
    author = {Author Three},
    title = {Conference Paper},
    booktitle = {Proceedings},
    year = {2024}
}
''', encoding='utf-8')

        cited_keys = {'article2023', 'conf2024'}

        bib_utils.sync_to_main(papis_bib, main_bib, cited_keys)

        main_content = main_bib.read_text(encoding='utf-8')

        # Should contain cited entries
        assert '@article{article2023,' in main_content
        assert '@inproceedings{conf2024,' in main_content

        # Should NOT contain book entry (not cited)
        assert '@book{book2022,' not in main_content

    def test_sync_nonexistent_papis_bib(self, tmp_path):
        """Test that FileNotFoundError is raised for non-existent papis.bib."""
        papis_bib = tmp_path / 'nonexistent.bib'
        main_bib = tmp_path / 'main.bib'
        cited_keys = {'key1'}

        with pytest.raises(FileNotFoundError):
            bib_utils.sync_to_main(papis_bib, main_bib, cited_keys)


class TestReadBibtex:
    """Tests for read_bibtex function."""

    def test_read_simple_entry(self, tmp_path):
        """Test reading a simple BibTeX entry."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{smith2023,
    author = {Smith, John},
    title = {Test Paper},
    year = {2023}
}
''', encoding='utf-8')

        entries = bib_utils.read_bibtex(bib_file)

        assert len(entries) == 1
        assert entries[0]['type'] == 'article'
        assert entries[0]['key'] == 'smith2023'
        assert 'author = {Smith, John}' in entries[0]['content']

    def test_read_multiple_entries(self, tmp_path):
        """Test reading multiple BibTeX entries."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{paper1,
    author = {Author One},
    title = {Title One}
}

@book{paper2,
    author = {Author Two},
    title = {Title Two}
}

@inproceedings{paper3,
    author = {Author Three},
    title = {Title Three}
}
''', encoding='utf-8')

        entries = bib_utils.read_bibtex(bib_file)

        assert len(entries) == 3
        assert entries[0]['type'] == 'article'
        assert entries[1]['type'] == 'book'
        assert entries[2]['type'] == 'inproceedings'

    def test_read_handles_comments(self, tmp_path):
        """Test that comments are stripped when reading."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
% This is a comment
@article{paper1,
    author = {Author One},
    title = {Title One}
}
% Another comment
''', encoding='utf-8')

        entries = bib_utils.read_bibtex(bib_file)

        assert len(entries) == 1
        # Comments should not be in the entry content
        assert '%' not in entries[0]['content']

    def test_read_empty_file(self, tmp_path):
        """Test reading an empty BibTeX file."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('', encoding='utf-8')

        entries = bib_utils.read_bibtex(bib_file)

        assert entries == []

    def test_read_with_nested_braces(self, tmp_path):
        """Test reading entries with nested braces in content."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('''
@article{paper1,
    author = {Smith, John and {von} Neumann, John},
    title = {Paper with {{nested}} braces},
    abstract = {This has {nested {content}} inside}
}
''', encoding='utf-8')

        entries = bib_utils.read_bibtex(bib_file)

        assert len(entries) == 1
        assert entries[0]['key'] == 'paper1'
        # Should preserve nested content
        assert '{von}' in entries[0]['content']
        assert '{{nested}}' in entries[0]['content']

    def test_read_nonexistent_file(self, tmp_path):
        """Test reading a non-existent file."""
        bib_file = tmp_path / 'nonexistent.bib'

        with pytest.raises(FileNotFoundError):
            bib_utils.read_bibtex(bib_file)


class TestWriteBibtex:
    """Tests for write_bibtex function."""

    def test_write_simple_entry(self, tmp_path):
        """Test writing a simple BibTeX entry."""
        output_file = tmp_path / 'output.bib'

        entries = [{
            'type': 'article',
            'key': 'smith2023',
            'content': 'author = {Smith, John},\ntitle = {Test}'
        }]

        bib_utils.write_bibtex(entries, output_file)

        content = output_file.read_text(encoding='utf-8')
        assert '@article{smith2023,' in content
        assert 'author = {Smith, John}' in content
        assert 'title = {Test}' in content

    def test_write_multiple_entries(self, tmp_path):
        """Test writing multiple BibTeX entries."""
        output_file = tmp_path / 'output.bib'

        entries = [
            {'type': 'article', 'key': 'paper1', 'content': 'title = {First}'},
            {'type': 'book', 'key': 'paper2', 'content': 'title = {Second}'}
        ]

        bib_utils.write_bibtex(entries, output_file)

        content = output_file.read_text(encoding='utf-8')
        assert '@article{paper1,' in content
        assert '@book{paper2,' in content

    def test_write_adds_closing_brace(self, tmp_path):
        """Test that write adds closing brace if content doesn't have it."""
        output_file = tmp_path / 'output.bib'

        entries = [{
            'type': 'article',
            'key': 'paper1',
            'content': 'author = {Smith}'  # No closing brace
        }]

        bib_utils.write_bibtex(entries, output_file)

        content = output_file.read_text(encoding='utf-8')
        # Should end with a closing brace
        assert content.strip().endswith('}')

    def test_write_preserves_closing_brace(self, tmp_path):
        """Test that write doesn't duplicate closing brace."""
        output_file = tmp_path / 'output.bib'

        entries = [{
            'type': 'article',
            'key': 'paper1',
            'content': 'author = {Smith}\n}'  # Has closing brace
        }]

        bib_utils.write_bibtex(entries, output_file)

        content = output_file.read_text(encoding='utf-8')
        # Should not have double closing braces
        assert '}}' not in content

    def test_write_missing_type_raises_error(self, tmp_path):
        """Test that missing 'type' raises ValueError."""
        output_file = tmp_path / 'output.bib'

        entries = [{
            'key': 'paper1',
            'content': 'author = {Smith}'
        }]

        with pytest.raises(ValueError, match="Entry must have 'type' and 'key' fields"):
            bib_utils.write_bibtex(entries, output_file)

    def test_write_missing_key_raises_error(self, tmp_path):
        """Test that missing 'key' raises ValueError."""
        output_file = tmp_path / 'output.bib'

        entries = [{
            'type': 'article',
            'content': 'author = {Smith}'
        }]

        with pytest.raises(ValueError, match="Entry must have 'type' and 'key' fields"):
            bib_utils.write_bibtex(entries, output_file)

    def test_write_empty_content(self, tmp_path):
        """Test writing entry with empty content."""
        output_file = tmp_path / 'output.bib'

        entries = [{
            'type': 'article',
            'key': 'paper1',
            'content': ''
        }]

        bib_utils.write_bibtex(entries, output_file)

        content = output_file.read_text(encoding='utf-8')
        assert '@article{paper1,' in content
        # Should still add a closing brace
        assert content.strip().endswith('}')


class TestMigrateBib:
    """Tests for migrate_bib function."""

    @patch('bib_utils.subprocess.run')
    def test_migrate_bib_success(self, mock_run, tmp_path):
        """Test successful migration of BibTeX file."""
        source_bib = tmp_path / 'source.bib'
        papis_lib_dir = tmp_path / 'papis_lib'

        # Create source BibTeX file
        source_bib.write_text('@article{test2023,\n    title = {Test}\n}', encoding='utf-8')

        # Mock subprocess.run for both add and export commands
        mock_run.return_value = MagicMock(
            stdout='@article{test2023,\n    title = {Test}\n}',
            stderr=''
        )

        result = bib_utils.migrate_bib(source_bib, papis_lib_dir)

        # Check that papis lib directory was created
        assert papis_lib_dir.exists()

        # Check that subprocess.run was called twice (add and export)
        assert mock_run.call_count == 2

        # Check the add command
        add_call = mock_run.call_args_list[0]
        add_cmd = add_call[0][0]
        assert 'papis' in add_cmd
        assert 'add' in add_cmd
        assert '--from' in add_cmd
        assert 'bibtex' in add_cmd
        assert '-l' in add_cmd
        assert str(papis_lib_dir) in add_cmd
        assert str(source_bib) in add_cmd

        # Check the export command
        export_call = mock_run.call_args_list[1]
        export_cmd = export_call[0][0]
        assert 'papis' in export_cmd
        assert 'export' in export_cmd
        assert '--format' in export_cmd
        assert 'bibtex' in export_cmd
        assert '-l' in export_cmd
        assert str(papis_lib_dir) in export_cmd

        # Check that papis.bib was created
        assert result == papis_lib_dir / 'papis.bib'
        assert result.exists()

    @patch('bib_utils.subprocess.run')
    def test_migrate_bib_nonexistent_source(self, mock_run, tmp_path):
        """Test migration with non-existent source file."""
        source_bib = tmp_path / 'nonexistent.bib'
        papis_lib_dir = tmp_path / 'papis_lib'

        with pytest.raises(FileNotFoundError, match="Source BibTeX file not found"):
            bib_utils.migrate_bib(source_bib, papis_lib_dir)

        # subprocess.run should not be called
        mock_run.assert_not_called()

    @patch('bib_utils.subprocess.run')
    def test_migrate_bib_creates_library_dir(self, mock_run, tmp_path):
        """Test that migration creates library directory."""
        source_bib = tmp_path / 'source.bib'
        papis_lib_dir = tmp_path / 'new_lib' / 'nested' / 'path'

        # Create source BibTeX file
        source_bib.write_text('@article{test2023,\n    title = {Test}\n}', encoding='utf-8')

        mock_run.return_value = MagicMock(
            stdout='@article{test2023,\n    title = {Test}\n}',
            stderr=''
        )

        bib_utils.migrate_bib(source_bib, papis_lib_dir)

        # Check that nested directories were created
        assert papis_lib_dir.exists()

    @patch('bib_utils.subprocess.run')
    def test_migrate_bib_papis_add_failure(self, mock_run, tmp_path):
        """Test migration when papis add command fails."""
        source_bib = tmp_path / 'source.bib'
        papis_lib_dir = tmp_path / 'papis_lib'

        source_bib.write_text('@article{test2023,\n    title = {Test}\n}', encoding='utf-8')

        # Mock papis add failure
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd='papis add', stderr='Error importing'
        )

        with pytest.raises(subprocess.CalledProcessError):
            bib_utils.migrate_bib(source_bib, papis_lib_dir)

    @patch('bib_utils.subprocess.run')
    def test_migrate_bib_papis_export_failure(self, mock_run, tmp_path):
        """Test migration when papis export command fails."""
        source_bib = tmp_path / 'source.bib'
        papis_lib_dir = tmp_path / 'papis_lib'

        source_bib.write_text('@article{test2023,\n    title = {Test}\n}', encoding='utf-8')

        # Mock papis export failure (first call succeeds, second fails)
        mock_run.side_effect = [
            MagicMock(stdout='', stderr=''),  # add succeeds
            subprocess.CalledProcessError(returncode=1, cmd='papis export', stderr='Error exporting')
        ]

        with pytest.raises(subprocess.CalledProcessError):
            bib_utils.migrate_bib(source_bib, papis_lib_dir)

    @patch('bib_utils.subprocess.run')
    def test_migrate_bib_writes_output(self, mock_run, tmp_path):
        """Test that migration writes exported content to papis.bib."""
        source_bib = tmp_path / 'source.bib'
        papis_lib_dir = tmp_path / 'papis_lib'

        source_bib.write_text('@article{test2023,\n    title = {Test}\n}', encoding='utf-8')

        exported_bibtex = '''@article{test2023,
    title = {Test},
    author = {Author},
    year = {2023}
}
'''

        mock_run.return_value = MagicMock(
            stdout=exported_bibtex,
            stderr=''
        )

        result = bib_utils.migrate_bib(source_bib, papis_lib_dir)

        # Check that content was written correctly
        content = result.read_text(encoding='utf-8')
        assert content == exported_bibtex

    @patch('bib_utils.subprocess.run')
    def test_migrate_bib_existing_library_dir(self, mock_run, tmp_path):
        """Test migration with existing library directory."""
        source_bib = tmp_path / 'source.bib'
        papis_lib_dir = tmp_path / 'papis_lib'

        # Create source and existing library directory
        source_bib.write_text('@article{test2023,\n    title = {Test}\n}', encoding='utf-8')
        papis_lib_dir.mkdir()

        mock_run.return_value = MagicMock(
            stdout='@article{test2023,\n    title = {Test}\n}',
            stderr=''
        )

        # Should not raise an error
        result = bib_utils.migrate_bib(source_bib, papis_lib_dir)
        assert result == papis_lib_dir / 'papis.bib'

    @patch('bib_utils.subprocess.run')
    def test_migrate_bib_check_true(self, mock_run, tmp_path):
        """Test that subprocess.run is called with check=True."""
        source_bib = tmp_path / 'source.bib'
        papis_lib_dir = tmp_path / 'papis_lib'

        source_bib.write_text('@article{test2023,\n    title = {Test}\n}', encoding='utf-8')

        mock_run.return_value = MagicMock(
            stdout='@article{test2023,\n    title = {Test}\n}',
            stderr=''
        )

        bib_utils.migrate_bib(source_bib, papis_lib_dir)

        # Verify check=True is passed to subprocess.run
        for call in mock_run.call_args_list:
            assert call[1].get('check') is True

    @patch('bib_utils.subprocess.run')
    def test_migrate_bib_capture_output(self, mock_run, tmp_path):
        """Test that subprocess.run is called with capture_output=True."""
        source_bib = tmp_path / 'source.bib'
        papis_lib_dir = tmp_path / 'papis_lib'

        source_bib.write_text('@article{test2023,\n    title = {Test}\n}', encoding='utf-8')

        mock_run.return_value = MagicMock(
            stdout='@article{test2023,\n    title = {Test}\n}',
            stderr=''
        )

        bib_utils.migrate_bib(source_bib, papis_lib_dir)

        # Verify capture_output=True is passed to subprocess.run
        for call in mock_run.call_args_list:
            assert call[1].get('capture_output') is True
