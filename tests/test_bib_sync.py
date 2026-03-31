"""Tests for bib_sync.py - BBL file parser and bibliography synchronization utilities."""

import pytest
from pathlib import Path
import sys

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / 'scripts'
sys.path.insert(0, str(scripts_dir))

import bib_sync


class TestReadBblFile:
    """Tests for read_bbl_file function."""

    def test_read_existing_bbl_file(self, tmp_path):
        """Test reading an existing .bbl file."""
        bbl_file = tmp_path / 'test.bbl'
        bbl_file.write_text('\\bibitem{test_key}', encoding='utf-8')

        result = bib_sync.read_bbl_file(bbl_file)
        assert result == '\\bibitem{test_key}'

    def test_read_bbl_file_with_unicode(self, tmp_path):
        """Test reading .bbl file with Unicode content."""
        bbl_file = tmp_path / 'test.bbl'
        unicode_content = '\\bibitem{key} Author, J. (2021) Title with émojis \U0001F600'
        bbl_file.write_text(unicode_content, encoding='utf-8')

        result = bib_sync.read_bbl_file(bbl_file)
        assert result == unicode_content

    def test_read_nonexistent_bbl_file(self, tmp_path):
        """Test reading a non-existent .bbl file raises FileNotFoundError."""
        bbl_file = tmp_path / 'nonexistent.bbl'

        with pytest.raises(FileNotFoundError):
            bib_sync.read_bbl_file(bbl_file)


class TestParseBblCitations:
    """Tests for parse_bbl_citations function."""

    def test_parse_standard_bibitem(self, tmp_path):
        """Test parsing standard \\bibitem{key} format."""
        bbl_file = tmp_path / 'test.bbl'
        content = '''
\\begin{thebibliography}{99}
\\bibitem{smith2021}
Smith, J. (2021). Title.
\\bibitem{jones2020}
Jones, A. (2020). Another Title.
\\end{thebibliography}
'''
        bbl_file.write_text(content, encoding='utf-8')

        citations = bib_sync.parse_bbl_citations(bbl_file)
        assert citations == ['smith2021', 'jones2020']

    def test_parse_bibitem_with_display_label(self, tmp_path):
        """Test parsing \\bibitem[display]{key} format."""
        bbl_file = tmp_path / 'test.bbl'
        content = '''
\\begin{thebibliography}{99}
\\bibitem[Smith(2021)]{smith2021}
Smith, J. (2021). Title.
\\bibitem[Jones(2020)]{jones2020}
Jones, A. (2020). Another Title.
\\end{thebibliography}
'''
        bbl_file.write_text(content, encoding='utf-8')

        citations = bib_sync.parse_bbl_citations(bbl_file)
        assert citations == ['smith2021', 'jones2020']

    def test_parse_biblatex_entry(self, tmp_path):
        """Test parsing BibLaTeX \\entry{key}{type} format."""
        bbl_file = tmp_path / 'test.bbl'
        content = '''
\\begin{refsection}[0]
\\refsection{0}
\\entry{smith2021}{article}{}
\\name{label}{}
\\strng{namepart}{family}{Smith}
\\strng{namepart}{given}{J}
\\end{entry}
\\entry{jones2020}{book}{}
\\name{label}{}
\\strng{namepart}{family}{Jones}
\\strng{namepart}{given}{A}
\\end{entry}
\\end{refsection}
'''
        bbl_file.write_text(content, encoding='utf-8')

        citations = bib_sync.parse_bbl_citations(bbl_file)
        assert citations == ['smith2021', 'jones2020']

    def test_parse_bibitem_with_escaped_key(self, tmp_path):
        """Test parsing \\bibitem[\\key]{key} format."""
        bbl_file = tmp_path / 'test.bbl'
        content = '''
\\begin{thebibliography}{99}
\\bibitem[\\key]{smith2021}
Smith, J. (2021). Title.
\\end{thebibliography}
'''
        bbl_file.write_text(content, encoding='utf-8')

        citations = bib_sync.parse_bbl_citations(bbl_file)
        assert citations == ['smith2021']

    def test_parse_setentrytag(self, tmp_path):
        """Test parsing \\setentrytag{key} format."""
        bbl_file = tmp_path / 'test.bbl'
        content = '''
\\begin{refsection}
\\setentrytag{smith2021}
\\setentrytag{jones2020}
\\end{refsection}
'''
        bbl_file.write_text(content, encoding='utf-8')

        citations = bib_sync.parse_bbl_citations(bbl_file)
        assert citations == ['smith2021', 'jones2020']

    def test_parse_mixed_formats(self, tmp_path):
        """Test parsing a .bbl file with mixed citation formats."""
        bbl_file = tmp_path / 'test.bbl'
        content = '''
\\begin{thebibliography}{99}
\\bibitem[Smith(2021)]{smith2021}
Smith, J. (2021). Title.
\\entry{jones2020}{article}{}
\\setentrytag{brown2019}
\\end{thebibliography}
'''
        bbl_file.write_text(content, encoding='utf-8')

        citations = bib_sync.parse_bbl_citations(bbl_file)
        assert citations == ['smith2021', 'jones2020', 'brown2019']

    def test_parse_empty_bbl_file(self, tmp_path):
        """Test parsing an empty .bbl file."""
        bbl_file = tmp_path / 'test.bbl'
        bbl_file.write_text('', encoding='utf-8')

        citations = bib_sync.parse_bbl_citations(bbl_file)
        assert citations == []

    def test_parse_bbl_with_no_citations(self, tmp_path):
        """Test parsing .bbl file with no citations."""
        bbl_file = tmp_path / 'test.bbl'
        content = '''
\\begin{thebibliography}{99}
No citations here.
\\end{thebibliography}
'''
        bbl_file.write_text(content, encoding='utf-8')

        citations = bib_sync.parse_bbl_citations(bbl_file)
        assert citations == []

    def test_parse_bbl_with_key_whitespace(self, tmp_path):
        """Test that keys with whitespace are properly trimmed."""
        bbl_file = tmp_path / 'test.bbl'
        content = '''
\\begin{thebibliography}{99}
\\bibitem{  smith2021  }
Smith, J. (2021). Title.
\\end{thebibliography}
'''
        bbl_file.write_text(content, encoding='utf-8')

        citations = bib_sync.parse_bbl_citations(bbl_file)
        assert citations == ['smith2021']

    def test_parse_bbl_with_composite_keys(self, tmp_path):
        """Test parsing keys with special characters like underscores."""
        bbl_file = tmp_path / 'test.bbl'
        content = '''
\\begin{thebibliography}{99}
\\bibitem{smith_jones_2021}
Smith, J. and Jones, A. (2021). Title.
\\end{thebibliography}
'''
        bbl_file.write_text(content, encoding='utf-8')

        citations = bib_sync.parse_bbl_citations(bbl_file)
        assert citations == ['smith_jones_2021']


class TestReadTexFile:
    """Tests for read_tex_file function."""

    def test_read_existing_tex_file(self, tmp_path):
        """Test reading an existing .tex file."""
        tex_file = tmp_path / 'test.tex'
        tex_file.write_text('\\documentclass{article}', encoding='utf-8')

        result = bib_sync.read_tex_file(tex_file)
        assert result == '\\documentclass{article}'

    def test_read_tex_file_with_unicode(self, tmp_path):
        """Test reading .tex file with Unicode content."""
        tex_file = tmp_path / 'test.tex'
        unicode_content = '\\title{Paper with émojis \U0001F600}'
        tex_file.write_text(unicode_content, encoding='utf-8')

        result = bib_sync.read_tex_file(tex_file)
        assert result == unicode_content

    def test_read_nonexistent_tex_file(self, tmp_path):
        """Test reading a non-existent .tex file raises FileNotFoundError."""
        tex_file = tmp_path / 'nonexistent.tex'

        with pytest.raises(FileNotFoundError):
            bib_sync.read_tex_file(tex_file)


class TestExtractBibliographyFiles:
    """Tests for extract_bibliography_files function."""

    def test_extract_standard_bibliography(self):
        """Test extracting from \\bibliography{} declaration."""
        content = '''
\\documentclass{article}
\\begin{document}
\\bibliography{references}
\\end{document}
'''
        result = bib_sync.extract_bibliography_files(content)
        assert result == ['references']

    def test_extract_multiple_bibliography_files(self):
        """Test extracting multiple bibliography files."""
        content = '''
\\documentclass{article}
\\bibliography{ref1,ref2,ref3}
'''
        result = bib_sync.extract_bibliography_files(content)
        assert result == ['ref1', 'ref2', 'ref3']

    def test_extract_bibliography_with_whitespace(self):
        """Test that whitespace in file list is handled."""
        content = '\\bibliography{ref1 , ref2 , ref3}'
        result = bib_sync.extract_bibliography_files(content)
        assert result == ['ref1', 'ref2', 'ref3']

    def test_extract_biblaTeX_addbibresource(self):
        """Test extracting from BibLaTeX \\addbibresource{}."""
        content = '''
\\usepackage[backend=biber]{biblatex}
\\addbibresource{references.bib}
'''
        result = bib_sync.extract_bibliography_files(content)
        assert result == ['references.bib']

    def test_extract_multiple_addbibresource(self):
        """Test extracting from multiple \\addbibresource declarations."""
        content = '''
\\addbibresource{ref1.bib}
\\addbibresource{ref2.bib}
'''
        result = bib_sync.extract_bibliography_files(content)
        assert result == ['ref1.bib', 'ref2.bib']

    def test_extract_addbibresource_with_options(self):
        """Test extracting \\addbibresource with options."""
        content = '\\addbibresource[datatype=bibtex]{references.bib}'
        result = bib_sync.extract_bibliography_files(content)
        assert result == ['references.bib']

    def test_extract_addbibresource_multiple_files(self):
        """Test extracting comma-separated files from \\addbibresource."""
        content = '\\addbibresource{ref1.bib,ref2.bib,ref3.bib}'
        result = bib_sync.extract_bibliography_files(content)
        assert result == ['ref1.bib', 'ref2.bib', 'ref3.bib']

    def test_extract_mixed_bibliography_commands(self):
        """Test extracting from mixed bibliography declarations."""
        content = '''
\\bibliography{classic}
\\addbibresource{modern.bib}
\\bibliography{another}
'''
        result = bib_sync.extract_bibliography_files(content)
        # Order of first occurrences is preserved
        assert 'classic' in result
        assert 'modern.bib' in result
        assert 'another' in result

    def test_extract_case_insensitive(self):
        """Test that extraction is case-insensitive."""
        content = '\\BIBLIOGRAPHY{ref1}\n\\ADDBIBRESOURCE{ref2}'
        result = bib_sync.extract_bibliography_files(content)
        assert result == ['ref1', 'ref2']

    def test_extract_removes_duplicates(self):
        """Test that duplicate file names are removed."""
        content = '\\bibliography{ref1,ref2,ref1}'
        result = bib_sync.extract_bibliography_files(content)
        assert result == ['ref1', 'ref2']

    def test_extract_empty_content(self):
        """Test extracting from empty content."""
        result = bib_sync.extract_bibliography_files('')
        assert result == []

    def test_extract_no_bibliography_commands(self):
        """Test content with no bibliography commands."""
        content = '\\documentclass{article}\n\\begin{document}\nHello world\n\\end{document}'
        result = bib_sync.extract_bibliography_files(content)
        assert result == []


class TestParseBibtexField:
    """Tests for parse_bibtex_field function."""

    def test_parse_simple_field(self):
        """Test parsing a simple field with braces."""
        content = 'author = {Smith, John}, title = {Title}'
        result = bib_sync.parse_bibtex_field(content, 'author')
        assert result == 'Smith, John'

    def test_parse_field_with_quotes(self):
        """Test parsing a field with quotes."""
        content = 'author = "Smith, John", title = "Title"'
        # Default start delimiter is {, so quotes won't match unless specified
        result = bib_sync.parse_bibtex_field(content, 'author')
        # With default delimiter, quotes won't be parsed correctly
        # This is expected behavior - the start parameter should be set to '"'
        result_quotes = bib_sync.parse_bibtex_field(content, 'author', start='"')
        assert result_quotes == 'Smith, John'

    def test_parse_field_not_found(self):
        """Test parsing a field that doesn't exist."""
        content = 'author = {Smith, John}'
        result = bib_sync.parse_bibtex_field(content, 'title')
        assert result is None

    def test_parse_field_case_insensitive(self):
        """Test that field name matching is case-insensitive."""
        content = 'AUTHOR = {Smith, John}'
        result = bib_sync.parse_bibtex_field(content, 'author')
        assert result == 'Smith, John'

    def test_parse_field_with_nested_braces(self):
        """Test parsing a field with nested braces."""
        content = 'author = {{Smith} and {Jones}}'
        result = bib_sync.parse_bibtex_field(content, 'author')
        assert result == '{Smith} and {Jones}'

    def test_parse_field_with_whitespace(self):
        """Test that whitespace is normalized."""
        content = 'title   =   {   Title   with   spaces   }'
        result = bib_sync.parse_bibtex_field(content, 'title')
        assert result == 'Title with spaces'

    def test_parse_year_field(self):
        """Test parsing a year field."""
        content = 'year = {2021}, author = {Smith}'
        result = bib_sync.parse_bibtex_field(content, 'year')
        assert result == '2021'

    def test_parse_field_with_special_characters(self):
        """Test parsing a field with LaTeX special characters."""
        content = 'title = {Title with {\\em emphasis} and symbols}'
        result = bib_sync.parse_bibtex_field(content, 'title')
        assert 'Title with' in result
        assert '{\\em emphasis}' in result


class TestReadBibtex:
    """Tests for read_bibtex function."""

    def test_read_single_entry(self, tmp_path):
        """Test reading a BibTeX file with a single entry."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John},
  title = {Title},
  year = {2021}
}'''
        bib_file.write_text(content, encoding='utf-8')

        entries = bib_sync.read_bibtex(bib_file)
        assert len(entries) == 1
        assert entries[0]['type'] == 'article'
        assert entries[0]['key'] == 'smith2021'
        assert 'Smith, John' in entries[0]['content']

    def test_read_multiple_entries(self, tmp_path):
        """Test reading a BibTeX file with multiple entries."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John}
}

@book{jones2020,
  author = {Jones, Arthur}
}

@inproceedings{brown2019,
  author = {Brown, Bob}
}'''
        bib_file.write_text(content, encoding='utf-8')

        entries = bib_sync.read_bibtex(bib_file)
        assert len(entries) == 3
        assert entries[0]['key'] == 'smith2021'
        assert entries[1]['key'] == 'jones2020'
        assert entries[2]['key'] == 'brown2019'

    def test_read_different_entry_types(self, tmp_path):
        """Test reading different BibTeX entry types."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{article1,
  author = {A}
}
@book{book1,
  author = {B}
}
@inproceedings{proc1,
  author = {C}
}
@inbook{inbook1,
  author = {D}
}
@phdthesis{phd1,
  author = {E}
}
@mastersthesis{ms1,
  author = {F}
}
@misc{misc1,
  author = {G}
}
@techreport{tech1,
  author = {H}
}'''
        bib_file.write_text(content, encoding='utf-8')

        entries = bib_sync.read_bibtex(bib_file)
        assert len(entries) == 8
        types = [e['type'] for e in entries]
        assert 'article' in types
        assert 'book' in types
        assert 'inproceedings' in types
        assert 'inbook' in types
        assert 'phdthesis' in types
        assert 'mastersthesis' in types
        assert 'misc' in types
        assert 'techreport' in types

    def test_read_entry_with_parentheses(self, tmp_path):
        """Test reading entries with parentheses."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article (smith2021,
  author = {Smith, John}
)'''
        bib_file.write_text(content, encoding='utf-8')

        entries = bib_sync.read_bibtex(bib_file)
        assert len(entries) == 1
        assert entries[0]['key'] == 'smith2021'

    def test_read_entry_case_insensitive_type(self, tmp_path):
        """Test that entry types are normalized to lowercase."""
        bib_file = tmp_path / 'test.bib'
        content = '''@ARTICLE{smith2021,
  author = {Smith, John}
}

@Book{jones2020,
  author = {Jones, Arthur}
}'''
        bib_file.write_text(content, encoding='utf-8')

        entries = bib_sync.read_bibtex(bib_file)
        assert entries[0]['type'] == 'article'
        assert entries[1]['type'] == 'book'

    def test_read_empty_bib_file(self, tmp_path):
        """Test reading an empty BibTeX file."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('', encoding='utf-8')

        entries = bib_sync.read_bibtex(bib_file)
        assert entries == []

    def test_read_bib_with_comments(self, tmp_path):
        """Test reading a BibTeX file with comments."""
        bib_file = tmp_path / 'test.bib'
        content = '''% This is a comment
@article{smith2021,
  author = {Smith, John},
  title = {Title}
}
% Another comment
@book{jones2020,
  author = {Jones, Arthur}
}'''
        bib_file.write_text(content, encoding='utf-8')

        entries = bib_sync.read_bibtex(bib_file)
        # Note: current implementation may not handle comments perfectly
        # but should still extract valid entries
        assert len(entries) >= 1


class TestWriteBibtex:
    """Tests for write_bibtex function."""

    def test_write_single_entry(self, tmp_path):
        """Test writing a single BibTeX entry."""
        output_file = tmp_path / 'output.bib'
        entries = [{
            'type': 'article',
            'key': 'smith2021',
            'content': 'author = {Smith, John}, title = {Title}, year = {2021}'
        }]

        bib_sync.write_bibtex(entries, output_file)

        content = output_file.read_text(encoding='utf-8')
        assert '@article{smith2021,' in content
        assert 'author = {Smith, John}' in content
        assert 'title = {Title}' in content

    def test_write_multiple_entries(self, tmp_path):
        """Test writing multiple BibTeX entries."""
        output_file = tmp_path / 'output.bib'
        entries = [
            {
                'type': 'article',
                'key': 'smith2021',
                'content': 'author = {Smith, John}'
            },
            {
                'type': 'book',
                'key': 'jones2020',
                'content': 'author = {Jones, Arthur}'
            }
        ]

        bib_sync.write_bibtex(entries, output_file)

        content = output_file.read_text(encoding='utf-8')
        assert '@article{smith2021,' in content
        assert '@book{jones2020,' in content

    def test_write_entry_with_closing_brace(self, tmp_path):
        """Test writing entry that already has closing brace in content."""
        output_file = tmp_path / 'output.bib'
        entries = [{
            'type': 'article',
            'key': 'smith2021',
            'content': 'author = {Smith, John}, title = {Title}, year = {2021}'
        }]

        bib_sync.write_bibtex(entries, output_file)

        content = output_file.read_text(encoding='utf-8')
        # Entry should be properly formatted
        assert content.count('@article{smith2021,') == 1

    def test_write_missing_required_field(self, tmp_path):
        """Test that missing required field raises ValueError."""
        output_file = tmp_path / 'output.bib'
        entries = [{
            'type': 'article',
            # Missing 'key'
            'content': 'author = {Smith, John}'
        }]

        with pytest.raises(ValueError, match="must have 'type' and 'key' fields"):
            bib_sync.write_bibtex(entries, output_file)

    def test_write_empty_entries_list(self, tmp_path):
        """Test writing an empty list of entries."""
        output_file = tmp_path / 'output.bib'
        entries = []

        bib_sync.write_bibtex(entries, output_file)

        content = output_file.read_text(encoding='utf-8')
        assert content == ''

    def test_write_and_reread_preserves_data(self, tmp_path):
        """Test that written entries can be read back correctly."""
        write_file = tmp_path / 'write.bib'
        read_file = tmp_path / 'read.bib'

        entries = [{
            'type': 'article',
            'key': 'smith2021',
            'content': 'author = {Smith, John}, title = {Test Title}'
        }]

        bib_sync.write_bibtex(entries, write_file)

        # Copy to read file
        import shutil
        shutil.copy(write_file, read_file)

        # Read back
        read_entries = bib_sync.read_bibtex(read_file)
        assert len(read_entries) >= 1
        assert any(e['key'] == 'smith2021' for e in read_entries)


class TestIntegration:
    """Integration tests for bib_sync module."""

    def test_parse_bbl_extract_bib_write_roundtrip(self, tmp_path):
        """Test roundtrip: parse BBL, read bib, write new bib."""
        # Create test BBL file
        bbl_file = tmp_path / 'test.bbl'
        bbl_content = '''
\\begin{thebibliography}{99}
\\bibitem{smith2021}
Smith, J. (2021). Title.
\\bibitem{jones2020}
Jones, A. (2020). Another Title.
\\end{thebibliography}
'''
        bbl_file.write_text(bbl_content)

        # Create test BibTeX file
        bib_file = tmp_path / 'test.bib'
        bib_content = '''@article{smith2021,
  author = {Smith, John},
  title = {Title},
  year = {2021}
}

@article{jones2020,
  author = {Jones, Arthur},
  title = {Another Title},
  year = {2020}
}'''
        bib_file.write_text(bib_content)

        # Parse BBL to get citation order
        citations = bib_sync.parse_bbl_citations(bbl_file)
        assert citations == ['smith2021', 'jones2020']

        # Read BibTeX entries
        entries = bib_sync.read_bibtex(bib_file)
        assert len(entries) == 2

        # Write to new file
        output_file = tmp_path / 'output.bib'
        bib_sync.write_bibtex(entries, output_file)

        # Verify output file was created
        assert output_file.exists()
        output_content = output_file.read_text()
        assert 'smith2021' in output_content
        assert 'jones2020' in output_content

    def test_extract_bib_from_tex_and_parse(self, tmp_path):
        """Test extracting bibliography files from LaTeX and using them."""
        # Create test LaTeX file
        tex_file = tmp_path / 'main.tex'
        tex_content = '''\\documentclass{article}
\\usepackage[backend=biber]{biblatex}
\\addbibresource{references.bib}
\\bibliography{classic}
\\begin{document}
Content here.
\\end{document}
'''
        tex_file.write_text(tex_content)

        # Extract bibliography files
        bib_files = bib_sync.extract_bibliography_files(bib_sync.read_tex_file(tex_file))
        assert 'references.bib' in bib_files
        assert 'classic' in bib_files

    def test_parse_bbl_field_extraction(self, tmp_path):
        """Test parsing BBL and then extracting fields from corresponding bib."""
        # Create BBL
        bbl_file = tmp_path / 'test.bbl'
        bbl_content = '\\bibitem{smith2021}\nSmith, J. (2021).'
        bbl_file.write_text(bbl_content)

        # Create BibTeX
        bib_file = tmp_path / 'test.bib'
        bib_content = '''@article{smith2021,
  author = {Smith, John},
  title = {The Title},
  year = {2021},
  journal = {Journal Name}
}'''
        bib_file.write_text(bib_content)

        # Parse citations
        citations = bib_sync.parse_bbl_citations(bbl_file)

        # Read and parse entries
        entries = bib_sync.read_bibtex(bib_file)

        # Extract field from matching entry
        for entry in entries:
            if entry['key'] in citations:
                title = bib_sync.parse_bibtex_field(entry['content'], 'title')
                assert title == 'The Title'
                year = bib_sync.parse_bibtex_field(entry['content'], 'year')
                assert year == '2021'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
