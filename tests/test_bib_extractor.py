"""Tests for bib_extractor.py - Papis CLI wrapper."""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import sys
import subprocess

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / 'scripts'
sys.path.insert(0, str(scripts_dir))

import bib_extractor


class TestNormalizeToDoi:
    """Tests for normalize_to_doi function."""

    def test_doi_already_normalized(self):
        """Test that a plain DOI is returned as-is."""
        doi = '10.1038/s41586-021-03926-0'
        result = bib_extractor.normalize_to_doi(doi)
        assert result == doi

    def test_doi_with_https_prefix(self):
        """Test DOI with https://doi.org/ prefix."""
        identifier = 'https://doi.org/10.1038/s41586-021-03926-0'
        result = bib_extractor.normalize_to_doi(identifier)
        assert result == '10.1038/s41586-021-03926-0'

    def test_doi_with_http_prefix(self):
        """Test DOI with http://doi.org/ prefix."""
        identifier = 'http://doi.org/10.1038/s41586-021-03926-0'
        result = bib_extractor.normalize_to_doi(identifier)
        assert result == '10.1038/s41586-021-03926-0'

    def test_doi_with_doi_colon_prefix(self):
        """Test DOI with doi: prefix."""
        identifier = 'doi:10.1038/s41586-021-03926-0'
        result = bib_extractor.normalize_to_doi(identifier)
        assert result == '10.1038/s41586-021-03926-0'

    def test_doi_from_url(self):
        """Test extracting DOI from a publisher URL."""
        identifier = 'https://www.nature.com/articles/s41586-021-03926-0'
        result = bib_extractor.normalize_to_doi(identifier)
        # The URL doesn't contain 10. prefix, so it's returned as-is
        assert result == identifier

    def test_doi_from_url_with_doi(self):
        """Test extracting DOI from a URL containing DOI."""
        identifier = 'https://example.com/10.1038/s41586-021-03926-0'
        result = bib_extractor.normalize_to_doi(identifier)
        assert result == '10.1038/s41586-021-03926-0'

    def test_arxiv_id(self):
        """Test arXiv ID format."""
        arxiv_id = '2106.12345'
        result = bib_extractor.normalize_to_doi(arxiv_id)
        assert result == arxiv_id

    def test_arxiv_url(self):
        """Test extracting arXiv ID from URL."""
        identifier = 'https://arxiv.org/abs/2106.12345'
        result = bib_extractor.normalize_to_doi(identifier)
        assert result == '2106.12345'

    def test_arxiv_pdf_url(self):
        """Test extracting arXiv ID from PDF URL."""
        identifier = 'https://arxiv.org/pdf/2106.12345.pdf'
        result = bib_extractor.normalize_to_doi(identifier)
        assert result == '2106.12345'

    def test_pmid_numeric(self):
        """Test that PMID is returned as-is."""
        pmid = '34567890'
        result = bib_extractor.normalize_to_doi(pmid)
        assert result == pmid

    def test_unknown_format(self):
        """Test that unknown format is returned as-is."""
        unknown = 'some-unknown-identifier'
        result = bib_extractor.normalize_to_doi(unknown)
        assert result == unknown


class TestSplitBibEntries:
    """Tests for split_bib_entries function."""

    def test_split_single_entry(self):
        """Test splitting a single BibTeX entry."""
        content = '@article{test,\n  author = {Author},\n  title = {Title}\n}'
        result = bib_extractor.split_bib_entries(content)
        assert len(result) == 1
        assert '@article{test' in result[0]

    def test_split_multiple_entries(self):
        """Test splitting multiple BibTeX entries."""
        content = '@article{test1,\n  author = {Author1},\n  title = {Title1}\n}\n@article{test2,\n  author = {Author2},\n  title = {Title2}\n}'
        result = bib_extractor.split_bib_entries(content)
        assert len(result) == 2
        assert '@article{test1' in result[0]
        assert '@article{test2' in result[1]

    def test_empty_content(self):
        """Test splitting empty content."""
        result = bib_extractor.split_bib_entries('')
        assert len(result) == 0


class TestEnsurePdfGitignored:
    """Tests for ensure_pdf_gitignored function."""

    def test_create_new_gitignore(self, tmp_path):
        """Test creating a new .gitignore file."""
        import os
        os.chdir(tmp_path)
        bib_extractor.ensure_pdf_gitignored()
        gitignore_path = Path('.gitignore')
        assert gitignore_path.exists()
        assert '*.pdf' in gitignore_path.read_text()

    def test_append_to_existing_gitignore(self, tmp_path):
        """Test appending *.pdf to existing .gitignore."""
        import os
        os.chdir(tmp_path)
        gitignore_path = Path('.gitignore')
        gitignore_path.write_text('*.pyc\n__pycache__/\n')
        bib_extractor.ensure_pdf_gitignored()
        content = gitignore_path.read_text()
        assert '*.pyc' in content
        assert '*.pdf' in content

    def test_no_duplicate_pattern(self, tmp_path):
        """Test that *.pdf is not added if already present."""
        import os
        os.chdir(tmp_path)
        gitignore_path = Path('.gitignore')
        gitignore_path.write_text('*.pdf\n')
        original_content = gitignore_path.read_text()
        bib_extractor.ensure_pdf_gitignored()
        assert gitignore_path.read_text() == original_content


class TestExportBibtex:
    """Tests for export_bibtex function."""

    @patch.object(bib_extractor, 'PAPIS_AVAILABLE', True)
    @patch('bib_extractor.subprocess.run')
    def test_export_bibtex_calls_papis(self, mock_run):
        """Test that export_bibtex calls papis with correct arguments."""
        bib_extractor.export_bibtex('output.bib')
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        # shell=True means command is passed as a string
        assert kwargs['shell'] is True
        assert 'papis' in args[0]
        assert '--format bibtex' in args[0]
        assert 'output.bib' in args[0]


class TestAddReference:
    """Tests for add_reference function."""

    @patch.object(bib_extractor, 'PAPIS_AVAILABLE', True)
    @patch('bib_extractor.subprocess.run')
    @patch('bib_extractor.Path.read_text')
    @patch('bib_extractor.split_bib_entries')
    def test_add_reference_basic(self, mock_split, mock_read, mock_run):
        """Test basic add_reference call."""
        mock_run.return_value = Mock(capture_output=True)
        mock_read.return_value = '@article{test,\n  author = {Author}\n}'
        mock_split.return_value = ['@article{test,\n  author = {Author}\n}']

        result = bib_extractor.add_reference('10.1038/s41586-021-03926-0')

        # Verify papis add was called
        assert mock_run.call_count >= 2  # add + export
        add_call = mock_run.call_args_list[0]
        args = add_call[0][0]  # First positional argument is the command list
        assert 'papis' in args
        assert '--from' in args
        assert 'doi' in args
        assert '10.1038/s41586-021-03926-0' in args
        assert '--set' in args
        assert 'tags=extracted' in args
        assert result == '@article{test,\n  author = {Author}\n}'

    @patch.object(bib_extractor, 'PAPIS_AVAILABLE', True)
    @patch('bib_extractor.subprocess.run')
    @patch('bib_extractor.Path.read_text')
    @patch('bib_extractor.split_bib_entries')
    def test_add_reference_with_no_pdf(self, mock_split, mock_read, mock_run):
        """Test add_reference with no_pdf=True."""
        mock_run.return_value = Mock(capture_output=True)
        mock_read.return_value = '@article{test,\n  author = {Author}\n}'
        mock_split.return_value = ['@article{test,\n  author = {Author}\n}']

        bib_extractor.add_reference('10.1038/s41586-021-03926-0', no_pdf=True)

        add_call = mock_run.call_args_list[0]
        args = add_call[0][0]
        assert '--no-document' in args

    @patch.object(bib_extractor, 'PAPIS_AVAILABLE', True)
    @patch('bib_extractor.subprocess.run')
    @patch('bib_extractor.Path.read_text')
    @patch('bib_extractor.split_bib_entries')
    def test_add_reference_normalizes_doi(self, mock_split, mock_read, mock_run):
        """Test that add_reference normalizes DOI input."""
        mock_run.return_value = Mock(capture_output=True)
        mock_read.return_value = '@article{test,\n  author = {Author}\n}'
        mock_split.return_value = ['@article{test,\n  author = {Author}\n}']

        bib_extractor.add_reference('https://doi.org/10.1038/s41586-021-03926-0')

        add_call = mock_run.call_args_list[0]
        args = add_call[0][0]
        # Should use normalized DOI (without https://doi.org/)
        doi_index = args.index('doi') + 1
        assert args[doi_index] == '10.1038/s41586-021-03926-0'


class TestExtractBibtex:
    """Tests for extract_bibtex function."""

    @patch.object(bib_extractor, 'add_reference')
    @patch('bib_extractor.ensure_pdf_gitignored')
    def test_extract_bibtex_success(self, mock_gitignore, mock_add):
        """Test successful extraction."""
        mock_add.return_value = '@article{test,\n  author = {Author}\n}'

        result = bib_extractor.extract_bibtex('10.1038/s41586-021-03926-0')

        assert result == '@article{test,\n  author = {Author}\n}'
        mock_gitignore.assert_called_once()
        mock_add.assert_called_once()

    @patch.object(bib_extractor, 'add_reference')
    @patch('bib_extractor.ensure_pdf_gitignored')
    def test_extract_bibtex_failure(self, mock_gitignore, mock_add):
        """Test extraction failure."""
        mock_add.return_value = ''

        result = bib_extractor.extract_bibtex('invalid-doi')

        assert result is None

    @patch.object(bib_extractor, 'add_reference')
    @patch('bib_extractor.ensure_pdf_gitignored')
    def test_extract_bibtex_no_pdf(self, mock_gitignore, mock_add):
        """Test extraction with no_pdf=True."""
        mock_add.return_value = '@article{test,\n  author = {Author}\n}'

        bib_extractor.extract_bibtex('10.1038/s41586-021-03926-0', no_pdf=True)

        mock_add.assert_called_once()
        args, kwargs = mock_add.call_args
        assert kwargs['no_pdf'] is True


class TestProcessBatch:
    """Tests for process_batch function."""

    @patch('time.sleep')
    @patch.object(bib_extractor, 'extract_bibtex')
    @patch.object(bib_extractor, 'export_bibtex')
    @patch('bib_extractor.ensure_pdf_gitignored')
    def test_process_batch(self, mock_gitignore, mock_export, mock_extract, mock_sleep):
        """Test processing a batch of identifiers."""
        mock_extract.return_value = '@article{test,\n  author = {Author}\n}'

        bib_extractor.process_batch(
            ['10.1038/s41586-021-03926-0', '10.1126/science.abf5641'],
            output_file='output.bib',
            delay=0.5
        )

        assert mock_extract.call_count == 2
        assert mock_export.call_count == 1
        assert mock_sleep.call_count == 1
        mock_export.assert_called_with('output.bib')

    @patch('time.sleep')
    @patch.object(bib_extractor, 'extract_bibtex')
    @patch.object(bib_extractor, 'export_bibtex')
    @patch('bib_extractor.ensure_pdf_gitignored')
    def test_process_batch_no_delay(self, mock_gitignore, mock_export, mock_extract, mock_sleep):
        """Test processing with zero delay."""
        mock_extract.return_value = '@article{test,\n  author = {Author}\n}'

        bib_extractor.process_batch(['10.1038/s41586-021-03926-0'], delay=0)

        assert mock_extract.call_count == 1
        mock_sleep.assert_not_called()

    @patch('time.sleep')
    @patch.object(bib_extractor, 'extract_bibtex')
    @patch.object(bib_extractor, 'export_bibtex')
    @patch('bib_extractor.ensure_pdf_gitignored')
    def test_process_batch_with_failure(self, mock_gitignore, mock_export, mock_extract, mock_sleep):
        """Test processing with some failures."""
        # First succeeds, second fails
        mock_extract.side_effect = ['@article{test,\n  author = {Author}\n}', None]

        bib_extractor.process_batch(
            ['10.1038/s41586-021-03926-0', 'invalid'],
            delay=0.5
        )

        assert mock_extract.call_count == 2
        mock_export.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
