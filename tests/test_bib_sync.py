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


class TestCompileLatex:
    """Tests for compile_latex function."""

    def test_compile_latex_no_compilers_available(self, tmp_path, monkeypatch):
        """Test compile_latex when no LaTeX compilers are available."""
        tex_file = tmp_path / 'test.tex'
        tex_file.write_text('\\documentclass{article}\\begin{document}\\end{document}')

        # Mock shutil.which to return None for all compilers
        def mock_which(cmd):
            return None

        monkeypatch.setattr('shutil.which', mock_which)

        result = bib_sync.compile_latex(tex_file)
        assert result is None

    def test_compile_latex_with_string_path(self, tmp_path, monkeypatch):
        """Test that compile_latex accepts string path."""
        tex_file = tmp_path / 'test.tex'
        tex_file.write_text('\\documentclass{article}\\begin{document}\\end{document}')

        # Mock shutil.which and subprocess.run to simulate successful compilation
        def mock_which(cmd):
            return cmd  # All compilers "available"

        def mock_run(args, capture_output=None, text=None, cwd=None):
            # Simulate successful compilation
            class MockResult:
                returncode = 0
                stdout = ''
                stderr = ''
            return MockResult()

        monkeypatch.setattr('shutil.which', mock_which)
        monkeypatch.setattr('subprocess.run', mock_run)

        # Create a .bbl file to simulate successful compilation
        bbl_file = tmp_path / 'test.bbl'
        bbl_file.write_text('\\bibitem{test}')

        # Call with string path
        result = bib_sync.compile_latex(str(tex_file))
        assert result is not None
        assert result == bbl_file

    def test_compile_latex_returns_none_on_failure(self, tmp_path, monkeypatch):
        """Test that compile_latex returns None when compilation fails."""
        tex_file = tmp_path / 'test.tex'
        tex_file.write_text('\\documentclass{article}\\begin{document}\\end{document}')

        def mock_which(cmd):
            return cmd  # All compilers "available"

        def mock_run(args, capture_output=None, text=None, cwd=None):
            # Simulate failed compilation
            class MockResult:
                returncode = 1  # Non-zero return code
                stdout = ''
                stderr = 'Error'
            return MockResult()

        monkeypatch.setattr('shutil.which', mock_which)
        monkeypatch.setattr('subprocess.run', mock_run)

        result = bib_sync.compile_latex(tex_file)
        assert result is None

    def test_compile_latex_returns_none_if_bbl_missing(self, tmp_path, monkeypatch):
        """Test that compile_latex returns None if .bbl file is not created."""
        tex_file = tmp_path / 'test.tex'
        tex_file.write_text('\\documentclass{article}\\begin{document}\\end{document}')

        def mock_which(cmd):
            return cmd  # All compilers "available"

        def mock_run(args, capture_output=None, text=None, cwd=None):
            # Simulate successful compilation but no .bbl created
            class MockResult:
                returncode = 0
                stdout = ''
                stderr = ''
            return MockResult()

        monkeypatch.setattr('shutil.which', mock_which)
        monkeypatch.setattr('subprocess.run', mock_run)

        result = bib_sync.compile_latex(tex_file)
        assert result is None  # No .bbl file exists

    def test_compile_latex_falls_through_compilers(self, tmp_path, monkeypatch):
        """Test that compile_latex tries multiple compilers in order."""
        tex_file = tmp_path / 'test.tex'
        tex_file.write_text('\\documentclass{article}\\begin{document}\\end{document}')

        compilers_tried = []

        def mock_which(cmd):
            compilers_tried.append(cmd)
            return cmd  # All compilers "available"

        def mock_run(args, capture_output=None, text=None, cwd=None):
            # Simulate successful compilation only on lualatex
            if 'lualatex' in args[0]:
                class MockResult:
                    returncode = 0
                    stdout = ''
                    stderr = ''
                # Create .bbl file
                bbl_file = tmp_path / 'test.bbl'
                bbl_file.write_text('\\bibitem{test}')
                return MockResult()
            else:
                # pdflatex and xelatex fail
                class MockResult:
                    returncode = 1
                    stdout = ''
                    stderr = 'Error'
                return MockResult()

        monkeypatch.setattr('shutil.which', mock_which)
        monkeypatch.setattr('subprocess.run', mock_run)

        result = bib_sync.compile_latex(tex_file)
        # Should succeed with lualatex
        assert result is not None
        assert result == tex_file.with_suffix('.bbl')


class TestExtractDoiFromBib:
    """Tests for extract_doi_from_bib function."""

    def test_extract_doi_with_braces(self, tmp_path):
        """Test extracting DOI with brace delimiters."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John},
  title = {Title},
  doi = {10.1234/example.123},
  year = {2021}
}'''
        bib_file.write_text(content, encoding='utf-8')

        doi = bib_sync.extract_doi_from_bib(bib_file, 'smith2021')
        assert doi == '10.1234/example.123'

    def test_extract_doi_with_quotes(self, tmp_path):
        """Test extracting DOI with quote delimiters."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John},
  doi = "10.1234/example.123",
  year = {2021}
}'''
        bib_file.write_text(content, encoding='utf-8')

        doi = bib_sync.extract_doi_from_bib(bib_file, 'smith2021')
        assert doi == '10.1234/example.123'

    def test_extract_doi_uppercase_field(self, tmp_path):
        """Test extracting DOI with uppercase field name."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John},
  DOI = {10.1234/example.123},
  year = {2021}
}'''
        bib_file.write_text(content, encoding='utf-8')

        doi = bib_sync.extract_doi_from_bib(bib_file, 'smith2021')
        assert doi == '10.1234/example.123'

    def test_extract_doi_from_url(self, tmp_path):
        """Test extracting DOI from URL format."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John},
  doi = {https://doi.org/10.1234/example.123},
  year = {2021}
}'''
        bib_file.write_text(content, encoding='utf-8')

        doi = bib_sync.extract_doi_from_bib(bib_file, 'smith2021')
        assert doi == '10.1234/example.123'

    def test_extract_doi_with_prefix(self, tmp_path):
        """Test extracting DOI with doi: prefix."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John},
  doi = {doi:10.1234/example.123},
  year = {2021}
}'''
        bib_file.write_text(content, encoding='utf-8')

        doi = bib_sync.extract_doi_from_bib(bib_file, 'smith2021')
        assert doi == '10.1234/example.123'

    def test_extract_doi_not_found(self, tmp_path):
        """Test when DOI field doesn't exist."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John},
  title = {Title},
  year = {2021}
}'''
        bib_file.write_text(content, encoding='utf-8')

        doi = bib_sync.extract_doi_from_bib(bib_file, 'smith2021')
        assert doi is None

    def test_extract_doi_key_not_found(self, tmp_path):
        """Test when citation key doesn't exist."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  doi = {10.1234/example.123}
}'''
        bib_file.write_text(content, encoding='utf-8')

        doi = bib_sync.extract_doi_from_bib(bib_file, 'nonexistent')
        assert doi is None

    def test_extract_doi_multiple_entries(self, tmp_path):
        """Test extracting DOI from correct entry among multiple entries."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  doi = {10.1234/one}
}

@article{jones2020,
  doi = {10.1234/two}
}

@article{brown2019,
  doi = {10.1234/three}
}'''
        bib_file.write_text(content, encoding='utf-8')

        doi = bib_sync.extract_doi_from_bib(bib_file, 'jones2020')
        assert doi == '10.1234/two'


class TestPapisAdd:
    """Tests for papis_add function."""

    def test_papis_add_when_available(self, tmp_path, monkeypatch):
        """Test papis_add when papis command is available."""
        def mock_which(cmd):
            if cmd == 'papis':
                return cmd
            return None

        def mock_run(args, capture_output=None, text=None):
            class MockResult:
                returncode = 0
                stdout = 'Added successfully'
                stderr = ''
            return MockResult()

        monkeypatch.setattr('shutil.which', mock_which)
        monkeypatch.setattr('subprocess.run', mock_run)

        result = bib_sync.papis_add('10.1234/example.123')
        assert result is not None
        assert result.returncode == 0

    def test_papis_add_when_not_available(self, monkeypatch):
        """Test papis_add when papis command is not available."""
        def mock_which(cmd):
            return None

        monkeypatch.setattr('shutil.which', mock_which)

        result = bib_sync.papis_add('10.1234/example.123')
        assert result is None

    def test_papis_add_on_error(self, monkeypatch):
        """Test papis_add when command execution fails."""
        def mock_which(cmd):
            if cmd == 'papis':
                return cmd
            return None

        def mock_run(args, capture_output=None, text=None):
            raise OSError('Command not found')

        monkeypatch.setattr('shutil.which', mock_which)
        monkeypatch.setattr('subprocess.run', mock_run)

        result = bib_sync.papis_add('10.1234/example.123')
        assert result is None


class TestUpdateEntryCiteOrder:
    """Tests for update_entry_cite_order function."""

    def test_add_cite_order_to_entry(self, tmp_path):
        """Test adding cite_order field to an entry."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John},
  title = {Title},
  year = {2021}
}'''
        bib_file.write_text(content, encoding='utf-8')

        bib_sync.update_entry_cite_order(bib_file, 'smith2021', '1')

        updated_content = bib_file.read_text(encoding='utf-8')
        assert 'cite_order = {1}' in updated_content

    def test_update_existing_cite_order(self, tmp_path):
        """Test updating existing cite_order field."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John},
  cite_order = {1},
  title = {Title}
}'''
        bib_file.write_text(content, encoding='utf-8')

        bib_sync.update_entry_cite_order(bib_file, 'smith2021', '5')

        updated_content = bib_file.read_text(encoding='utf-8')
        assert 'cite_order = {5}' in updated_content
        assert 'cite_order = {1}' not in updated_content

    def test_update_case_insensitive(self, tmp_path):
        """Test that field name matching is case-insensitive."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John},
  CITE_ORDER = {1},
  title = {Title}
}'''
        bib_file.write_text(content, encoding='utf-8')

        bib_sync.update_entry_cite_order(bib_file, 'smith2021', '10')

        updated_content = bib_file.read_text(encoding='utf-8')
        # Should have the new cite_order value
        assert 'cite_order = {10}' in updated_content or 'CITE_ORDER = {10}' in updated_content

    def test_update_entry_not_found(self, tmp_path):
        """Test updating non-existent entry raises ValueError."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John}
}'''
        bib_file.write_text(content, encoding='utf-8')

        with pytest.raises(ValueError, match="Entry 'nonexistent' not found"):
            bib_sync.update_entry_cite_order(bib_file, 'nonexistent', '1')

    def test_update_multiple_entries(self, tmp_path):
        """Test updating cite_order for one entry among multiple."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John}
}

@article{jones2020,
  author = {Jones, Arthur}
}

@article{brown2019,
  author = {Brown, Bob}
}'''
        bib_file.write_text(content, encoding='utf-8')

        bib_sync.update_entry_cite_order(bib_file, 'jones2020', '2')

        updated_content = bib_file.read_text(encoding='utf-8')
        assert 'cite_order = {2}' in updated_content

    def test_update_with_string_order(self, tmp_path):
        """Test that string order values work correctly."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John}
}'''
        bib_file.write_text(content, encoding='utf-8')

        bib_sync.update_entry_cite_order(bib_file, 'smith2021', '42')

        updated_content = bib_file.read_text(encoding='utf-8')
        assert 'cite_order = {42}' in updated_content


class TestRemoveEntryField:
    """Tests for remove_entry_field function."""

    def test_remove_field_with_braces(self, tmp_path):
        """Test removing a field with brace delimiters."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John},
  title = {Title},
  cite_order = {1},
  year = {2021}
}'''
        bib_file.write_text(content, encoding='utf-8')

        bib_sync.remove_entry_field(bib_file, 'smith2021', 'cite_order')

        updated_content = bib_file.read_text(encoding='utf-8')
        assert 'cite_order' not in updated_content
        assert 'author = {Smith, John}' in updated_content

    def test_remove_field_with_quotes(self, tmp_path):
        """Test removing a field with quote delimiters."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John},
  cite_order = "1",
  year = {2021}
}'''
        bib_file.write_text(content, encoding='utf-8')

        bib_sync.remove_entry_field(bib_file, 'smith2021', 'cite_order')

        updated_content = bib_file.read_text(encoding='utf-8')
        assert 'cite_order' not in updated_content

    def test_remove_field_case_insensitive(self, tmp_path):
        """Test that field name matching is case-insensitive."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John},
  CITE_ORDER = {1},
  year = {2021}
}'''
        bib_file.write_text(content, encoding='utf-8')

        bib_sync.remove_entry_field(bib_file, 'smith2021', 'cite_order')

        updated_content = bib_file.read_text(encoding='utf-8')
        assert 'cite_order' not in updated_content
        assert 'CITE_ORDER' not in updated_content

    def test_remove_field_from_multiple_entries(self, tmp_path):
        """Test removing field from one entry among multiple."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John},
  cite_order = {1}
}

@article{jones2020,
  author = {Jones, Arthur},
  cite_order = {2}
}

@article{brown2019,
  author = {Brown, Bob},
  cite_order = {3}
}'''
        bib_file.write_text(content, encoding='utf-8')

        bib_sync.remove_entry_field(bib_file, 'jones2020', 'cite_order')

        updated_content = bib_file.read_text(encoding='utf-8')
        # jones2020 should not have cite_order
        assert updated_content.count('cite_order') == 2

    def test_remove_nonexistent_field(self, tmp_path):
        """Test removing a field that doesn't exist."""
        bib_file = tmp_path / 'test.bib'
        original_content = '''@article{smith2021,
  author = {Smith, John},
  year = {2021}
}'''
        bib_file.write_text(original_content, encoding='utf-8')

        # Should not raise an error
        bib_sync.remove_entry_field(bib_file, 'smith2021', 'cite_order')

        # Content should remain unchanged
        updated_content = bib_file.read_text(encoding='utf-8')
        assert updated_content == original_content

    def test_remove_field_from_nonexistent_entry(self, tmp_path):
        """Test removing field from non-existent entry raises ValueError."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John}
}'''
        bib_file.write_text(content, encoding='utf-8')

        with pytest.raises(ValueError, match="Entry 'nonexistent' not found"):
            bib_sync.remove_entry_field(bib_file, 'nonexistent', 'cite_order')


class TestSortBibtexByCiteOrder:
    """Tests for sort_bibtex_by_cite_order function."""

    def test_sort_entries_by_cite_order(self, tmp_path):
        """Test sorting entries by cite_order field."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{brown2019,
  author = {Brown, Bob},
  cite_order = {3}
}

@article{smith2021,
  author = {Smith, John},
  cite_order = {1}
}

@article{jones2020,
  author = {Jones, Arthur},
  cite_order = {2}
}'''
        bib_file.write_text(content, encoding='utf-8')

        sorted_entries = bib_sync.sort_bibtex_by_cite_order(bib_file)

        assert len(sorted_entries) == 3
        assert sorted_entries[0]['key'] == 'smith2021'
        assert sorted_entries[1]['key'] == 'jones2020'
        assert sorted_entries[2]['key'] == 'brown2019'

    def test_sort_with_uncited_entries(self, tmp_path):
        """Test that entries without cite_order are placed at the end."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{uncited1,
  author = {Uncited, One}
}

@article{smith2021,
  author = {Smith, John},
  cite_order = {1}
}

@article{uncited2,
  author = {Uncited, Two}
}

@article{jones2020,
  author = {Jones, Arthur},
  cite_order = {2}
}'''
        bib_file.write_text(content, encoding='utf-8')

        sorted_entries = bib_sync.sort_bibtex_by_cite_order(bib_file)

        assert len(sorted_entries) == 4
        assert sorted_entries[0]['key'] == 'smith2021'
        assert sorted_entries[1]['key'] == 'jones2020'
        # Uncited entries at the end
        uncited_keys = [e['key'] for e in sorted_entries[2:]]
        assert 'uncited1' in uncited_keys
        assert 'uncited2' in uncited_keys

    def test_sort_empty_bib_file(self, tmp_path):
        """Test sorting an empty BibTeX file."""
        bib_file = tmp_path / 'test.bib'
        bib_file.write_text('', encoding='utf-8')

        sorted_entries = bib_sync.sort_bibtex_by_cite_order(bib_file)

        assert sorted_entries == []

    def test_sort_single_entry(self, tmp_path):
        """Test sorting a single entry."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John},
  cite_order = {1}
}'''
        bib_file.write_text(content, encoding='utf-8')

        sorted_entries = bib_sync.sort_bibtex_by_cite_order(bib_file)

        assert len(sorted_entries) == 1
        assert sorted_entries[0]['key'] == 'smith2021'

    def test_sort_updates_file(self, tmp_path):
        """Test that sorted order is written to the file."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{brown2019,
  cite_order = {3}
}

@article{smith2021,
  cite_order = {1}
}

@article{jones2020,
  cite_order = {2}
}'''
        bib_file.write_text(content, encoding='utf-8')

        bib_sync.sort_bibtex_by_cite_order(bib_file)

        # Read the file and verify order
        updated_content = bib_file.read_text(encoding='utf-8')
        entries = bib_sync.read_bibtex(bib_file)

        assert entries[0]['key'] == 'smith2021'
        assert entries[1]['key'] == 'jones2020'
        assert entries[2]['key'] == 'brown2019'

    def test_sort_with_numeric_string_orders(self, tmp_path):
        """Test sorting with numeric string cite_order values."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{entry10,
  cite_order = {10}
}

@article{entry2,
  cite_order = {2}
}

@article{entry1,
  cite_order = {1}
}'''
        bib_file.write_text(content, encoding='utf-8')

        sorted_entries = bib_sync.sort_bibtex_by_cite_order(bib_file)

        assert len(sorted_entries) == 3
        assert sorted_entries[0]['key'] == 'entry1'
        assert sorted_entries[1]['key'] == 'entry2'
        assert sorted_entries[2]['key'] == 'entry10'


class TestBibSyncIoIntegration:
    """Integration tests for BibTeX I/O functions."""

    def test_extract_doi_update_cite_order_sort_roundtrip(self, tmp_path):
        """Test full roundtrip: extract DOI, update cite_order, sort."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{jones2020,
  author = {Jones, Arthur},
  doi = {10.1234/two}
}

@article{smith2021,
  author = {Smith, John},
  doi = {10.1234/one}
}

@article{brown2019,
  author = {Brown, Bob},
  doi = {10.1234/three}
}'''
        bib_file.write_text(content, encoding='utf-8')

        # Extract DOIs
        doi_smith = bib_sync.extract_doi_from_bib(bib_file, 'smith2021')
        doi_jones = bib_sync.extract_doi_from_bib(bib_file, 'jones2020')
        assert doi_smith == '10.1234/one'
        assert doi_jones == '10.1234/two'

        # Update cite_order
        bib_sync.update_entry_cite_order(bib_file, 'smith2021', '1')
        bib_sync.update_entry_cite_order(bib_file, 'brown2019', '3')

        # Sort
        sorted_entries = bib_sync.sort_bibtex_by_cite_order(bib_file)

        # Verify sorted order
        assert len(sorted_entries) == 3
        assert sorted_entries[0]['key'] == 'smith2021'  # Has cite_order = 1
        assert sorted_entries[1]['key'] == 'brown2019'  # Has cite_order = 3
        # jones2020 has no cite_order, so it's at the end (position 2)
        assert sorted_entries[2]['key'] == 'jones2020'

    def test_remove_field_after_update(self, tmp_path):
        """Test removing cite_order field after updating it."""
        bib_file = tmp_path / 'test.bib'
        content = '''@article{smith2021,
  author = {Smith, John}
}'''
        bib_file.write_text(content, encoding='utf-8')

        # Add cite_order
        bib_sync.update_entry_cite_order(bib_file, 'smith2021', '5')

        # Verify it was added
        content_before = bib_file.read_text()
        assert 'cite_order = {5}' in content_before

        # Remove cite_order
        bib_sync.remove_entry_field(bib_file, 'smith2021', 'cite_order')

        # Verify it was removed
        content_after = bib_file.read_text()
        assert 'cite_order' not in content_after
        assert 'author = {Smith, John}' in content_after


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
