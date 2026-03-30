import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bib_smart_search.py"
EXTRACTOR_PATH = REPO_ROOT / "scripts" / "bib_extractor.py"
TITLE_NORMALIZER_PATH = REPO_ROOT / "scripts" / "title_normalizer.py"


def load_module():
    spec = importlib.util.spec_from_file_location("bib_smart_search", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BibSmartSearchTests(unittest.TestCase):
    def test_title_normalizer_converts_tc_math_for_plain_text(self):
        spec = importlib.util.spec_from_file_location(
            "title_normalizer",
            TITLE_NORMALIZER_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        plain = module.normalize_title_for_plain_text(
            "Strain dependence of $T_{c}$ in suspended NbSe2"
        )

        self.assertEqual(plain, "Strain dependence of Tc in suspended NbSe2")

    def test_title_normalizer_cleans_overescaped_latex_math(self):
        spec = importlib.util.spec_from_file_location(
            "title_normalizer",
            TITLE_NORMALIZER_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        bibtex_title = module.normalize_title_for_bibtex(
            r"Strain dependence of \$\textbraceleft{{T}}\textbraceright\_\textbraceleft c\textbraceright\$ in suspended NbSe2"
        )

        self.assertEqual(
            bibtex_title,
            "Strain dependence of {$T_c$} in suspended NbSe2",
        )

    def test_title_normalizer_wraps_bare_math_in_bibtex_title(self):
        spec = importlib.util.spec_from_file_location(
            "title_normalizer",
            TITLE_NORMALIZER_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        bibtex_title = module.normalize_title_for_bibtex(
            "Strain dependence of $T_c$ in suspended NbSe2"
        )

        self.assertEqual(
            bibtex_title,
            "Strain dependence of {$T_c$} in suspended NbSe2",
        )

    def test_common_knowledge_sentence_is_not_marked_for_citation(self):
        module = load_module()
        analyzer = module.CitationNeedAnalyzer()

        result = analyzer.analyze_sentence(
            "Phonons are the quantum mechanical excitations of atomic vibrations in solids."
        )

        self.assertFalse(result.needs_citation)

    def test_quantitative_sentence_is_detected_and_parsed(self):
        module = load_module()
        analyzer = module.CitationNeedAnalyzer()

        claim = analyzer.extract_quantitative_claim(
            "The critical temperature was tuned by up to approximately 0.92 K, corresponding to 12.5% of Tc = 7.3 K."
        )

        self.assertIsNotNone(claim)
        self.assertEqual(claim["values"], ["0.92", "12.5", "7.3"])
        self.assertEqual(claim["units"], ["K", "%", "K"])

    def test_quantitative_candidate_with_matching_numbers_scores_higher(self):
        module = load_module()
        analyzer = module.CitationNeedAnalyzer()

        sentence = (
            "The critical temperature was tuned by up to approximately 0.92 K, "
            "corresponding to 12.5% of Tc = 7.3 K."
        )
        claim = analyzer.extract_quantitative_claim(sentence)

        close_match = {
            "title": "Strain tuning of superconductivity in suspended NbSe2",
            "abstract": "We observe a 0.9 K modulation of Tc, about 12% of a 7.3 K transition.",
            "journal": "Nano Letters",
        }
        loose_match = {
            "title": "Superconductivity in layered materials",
            "abstract": "The transition temperature changes moderately under strain.",
            "journal": "Physical Review B",
        }

        close_score = analyzer.score_quantitative_match(sentence, claim, close_match)
        loose_score = analyzer.score_quantitative_match(sentence, claim, loose_match)

        self.assertGreater(close_score, loose_score)

    def test_local_bib_extractor_can_parse_arxiv_html_fallback(self):
        spec = importlib.util.spec_from_file_location(
            "bib_extractor",
            EXTRACTOR_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        extractor = module.BibExtractor()

        html = """
        <html>
          <head>
            <meta name="citation_title" content="Controllable superconductivity and thermal effects in suspended NbSe2" />
            <meta name="citation_author" content="H. Lu" />
            <meta name="citation_author" content="F. H. Ruan" />
            <meta name="citation_date" content="2025/11/07" />
            <meta name="citation_arxiv_id" content="2511.05763" />
            <meta name="citation_abstract" content="We report tunable superconductivity in suspended NbSe2." />
          </head>
        </html>
        """

        bibtex = extractor._arxiv_html_to_bibtex(html, "2511.05763")

        self.assertIn("@misc{2511.05763", bibtex)
        self.assertIn("Controllable superconductivity and thermal effects in suspended NbSe2", bibtex)
        self.assertIn("eprint    = {2511.05763}", bibtex)

    def test_local_bib_extractor_formats_arxiv_inline_citation(self):
        spec = importlib.util.spec_from_file_location(
            "bib_extractor",
            EXTRACTOR_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        extractor = module.BibExtractor()

        bibtex = """@misc{2511.05763,
  title     = {Controllable Superconductivity in Suspended van der Waals Materials},
  year      = {2025},
  eprint    = {2511.05763},
  archivePrefix = {arXiv},
  url       = {https://arxiv.org/abs/2511.05763}
}"""

        inline = extractor.generate_inline_citation(bibtex, style="journal")
        self.assertEqual(inline, "arXiv:2511.05763, (2025)")

    def test_local_bib_extractor_cleans_crossref_title_markup(self):
        spec = importlib.util.spec_from_file_location(
            "bib_extractor",
            EXTRACTOR_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        extractor = module.BibExtractor()

        dirty = """@article{tmp,
  title = {Single phonon detection for dark matter via quantum evaporation and sensing of
<mml:math xmlns:mml="http://www.w3.org/1998/Math/MathML" display="inline"><mml:mrow><mml:mmultiscripts><mml:mrow><mml:mi>He</mml:mi></mml:mrow><mml:mprescripts/><mml:none/><mml:mrow><mml:mn>3</mml:mn></mml:mrow></mml:mmultiscripts></mml:mrow></mml:math>},
  journal = {Physical Review D},
  doi = {10.1103/physrevd.109.023010}
}"""

        cleaned = extractor._fix_bibtex_fields(dirty, "10.1103/physrevd.109.023010")

        self.assertIn("sensing of 3He", cleaned)
        self.assertNotIn("<mml:math", cleaned)

    def test_local_bib_extractor_normalizes_tc_title_math(self):
        spec = importlib.util.spec_from_file_location(
            "bib_extractor",
            EXTRACTOR_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        extractor = module.BibExtractor()

        dirty = """@article{tmp,
  title = {Strain dependence of $T_{c}$ in suspended NbSe2},
  journal = {Nature Communications},
  doi = {10.1038/s41467-024-48306-0}
}"""

        cleaned = extractor._fix_bibtex_fields(dirty, "10.1038/s41467-024-48306-0")

        self.assertIn("title      = {Strain dependence of {$T_c$} in suspended NbSe2}", cleaned)

    def test_local_bib_extractor_backfills_article_number_into_pages(self):
        spec = importlib.util.spec_from_file_location(
            "bib_extractor",
            EXTRACTOR_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        extractor = module.BibExtractor()

        bibtex = """@article{tmp,
  author = {A. Author},
  title = {Example article},
  journal = {Nature Communications},
  volume = {15},
  year = {2024},
  doi = {10.1038/s41467-024-48306-0}
}"""

        metadata = {
            "volume": "15",
            "issue": "1",
            "article-number": "4979",
            "page": None,
        }

        fixed = extractor._fix_bibtex_fields(
            bibtex,
            "10.1038/s41467-024-48306-0",
            crossref_metadata=metadata,
        )

        self.assertIn("pages      = {4979}", fixed)
        self.assertIn("number     = {1}", fixed)

    def test_bib_searcher_builds_inline_citation_with_article_number(self):
        module = load_module()
        analyzer = module.CitationNeedAnalyzer()

        inline = analyzer.build_inline_citation("10.1038/s41467-024-48306-0")

        self.assertIn("Nat. Commun.", inline)
        self.assertIn("4979", inline)

    def test_bib_searcher_can_use_full_journal_names_for_inline_citations(self):
        module = load_module()
        analyzer = module.CitationNeedAnalyzer(use_full_journal_name=True)

        inline = analyzer.build_inline_citation("10.1038/s41467-024-48306-0")

        self.assertIn("Nature Communications", inline)
        self.assertNotIn("Nat. Commun.", inline)

    def test_bib_searcher_preserves_tc_case_in_local_bib_display_title(self):
        module = load_module()
        analyzer = module.CitationNeedAnalyzer()

        entry = """@article{tmp,
  title = {Strain dependence of {$T_c$} in suspended NbSe2},
  journal = {Nature Communications},
  doi = {10.1038/s41467-024-48306-0}
}"""

        parsed = analyzer._parse_bib_entry(entry)

        self.assertEqual(
            parsed["title"],
            "Strain dependence of T_c in suspended NbSe2",
        )

    def test_rerank_prefers_anchor_matched_phonon_qubit_paper(self):
        module = load_module()
        analyzer = module.CitationNeedAnalyzer()

        sentence = (
            "Superconducting qubit sensors detect mechanical phonons via "
            "piezoelectric coupling to acoustic modes."
        )

        candidates = [
            {
                "title": "Cavity optomechanics",
                "abstract": (
                    "This review covers optical cavities and mechanical resonators "
                    "with radiation-pressure coupling."
                ),
                "journal": "Reviews of Modern Physics",
            },
            {
                "title": (
                    "Resolving the energy of a single mechanical phonon with a "
                    "superconducting qubit"
                ),
                "abstract": (
                    "A superconducting qubit detects acoustic phonons through "
                    "piezoelectric coupling to a mechanical resonator mode."
                ),
                "journal": "Nature",
            },
            {
                "title": "Magnetometry with nitrogen-vacancy defects in diamond",
                "abstract": "NV centers enable nanoscale magnetic sensing.",
                "journal": "Reports on Progress in Physics",
            },
        ]

        reranked = analyzer.rerank_citations(sentence, candidates)

        self.assertEqual(reranked[0]["title"], candidates[1]["title"])
        self.assertGreater(reranked[0]["score"], 0.0)
        self.assertEqual(reranked[-1]["score"], 0.0)

    def test_reference_note_prefers_contribution_sentence_over_background(self):
        module = load_module()
        analyzer = module.CitationNeedAnalyzer()

        candidate = {
            "title": "Gate-Controlled Supercurrent in Epitaxial Al/InAs Nanowires",
            "abstract": (
                "Hybrid superconductor-semiconductor nanowires are a promising platform "
                "for topological quantum devices. Here we demonstrate gate-controlled "
                "supercurrent in epitaxial Al/InAs nanowires. The supercurrent remains "
                "tunable over a broad gate range."
            ),
            "journal": "Nano Letters",
        }

        summary = analyzer.extract_reference_note(candidate)

        self.assertEqual(
            summary["best_evidence"],
            "Here we demonstrate gate-controlled supercurrent in epitaxial Al/InAs nanowires.",
        )
        self.assertIn("gate-controlled supercurrent", summary["reference_note"].lower())
        self.assertNotIn("promising platform", summary["reference_note"].lower())

    def test_suggest_citations_filters_zero_score_irrelevant_results(self):
        module = load_module()
        analyzer = module.CitationNeedAnalyzer()

        sentence = (
            "Superconducting qubit sensors detect mechanical phonons via "
            "piezoelectric coupling to acoustic modes."
        )

        analyzer.search_for_citations = lambda *args, **kwargs: [
            {
                "doi": "",
                "title": "Cavity optomechanics",
                "abstract": "Optical cavities couple to mechanical motion.",
                "journal": "Reviews of Modern Physics",
            },
            {
                "doi": "",
                "title": (
                    "Resolving the energy of a single mechanical phonon with a "
                    "superconducting qubit"
                ),
                "abstract": (
                    "A superconducting qubit detects acoustic phonons through "
                    "piezoelectric coupling."
                ),
                "journal": "Nature",
            },
            {
                "doi": "",
                "title": "Magnetometry with nitrogen-vacancy defects in diamond",
                "abstract": "NV centers enable nanoscale magnetic sensing.",
                "journal": "Reports on Progress in Physics",
            },
        ]

        results = analyzer.suggest_citations_for_sentence(sentence, max_results=3)

        self.assertEqual(len(results), 1)
        self.assertIn("mechanical phonon", results[0]["title"].lower())

    def test_local_bib_extractor_reuses_existing_entry_by_doi(self):
        spec = importlib.util.spec_from_file_location("bib_extractor", EXTRACTOR_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        extractor = module.BibExtractor()

        with tempfile.TemporaryDirectory() as tmpdir:
            bib_path = Path(tmpdir) / "references.bib"
            existing = """@article{ExistingKey,
  author = {A. Author},
  title = {Existing article},
  journal = {Phys. Rev. B},
  volume = {97},
  pages = {205443},
  year = {2018},
  doi = {10.1103/physrevb.97.205443},
  url = {http://dx.doi.org/10.1103/PhysRevB.97.205443}
}"""
            bib_path.write_text(existing, encoding="utf-8")

            def fail_fetch(*args, **kwargs):
                raise AssertionError("network fetch should not be called for existing DOI")

            extractor.fetch_from_crossref = fail_fetch

            reused = extractor.extract_bibtex(
                "10.1103/PhysRevB.97.205443",
                bib_file=str(bib_path),
            )

            self.assertEqual(reused.strip(), existing.strip())

    def test_local_bib_extractor_reuses_existing_entry_by_url(self):
        spec = importlib.util.spec_from_file_location("bib_extractor", EXTRACTOR_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        extractor = module.BibExtractor()

        with tempfile.TemporaryDirectory() as tmpdir:
            bib_path = Path(tmpdir) / "references.bib"
            existing = """@article{ExistingKey,
  author = {A. Author},
  title = {Existing article},
  journal = {Phys. Rev. B},
  volume = {97},
  pages = {205443},
  year = {2018},
  doi = {10.1103/physrevb.97.205443}
}"""
            bib_path.write_text(existing, encoding="utf-8")

            def fail_fetch(*args, **kwargs):
                raise AssertionError("network fetch should not be called for existing DOI URL")

            extractor.fetch_from_crossref = fail_fetch

            reused = extractor.extract_bibtex(
                "https://doi.org/10.1103/PhysRevB.97.205443",
                bib_file=str(bib_path),
            )

            self.assertEqual(reused.strip(), existing.strip())

    def test_bib_searcher_filters_non_materialized_citations_when_bib_file_required(self):
        module = load_module()
        analyzer = module.CitationNeedAnalyzer()

        sentence = "A supported claim requires a finalized bibliography entry."
        analyzer.search_for_citations = lambda *args, **kwargs: [
            {
                "doi": "10.1000/example",
                "title": "Example supported claim",
                "abstract": "Supported claim example abstract",
                "journal": "Example Journal",
            }
        ]
        analyzer.rerank_citations = lambda *args, **kwargs: [
            {
                "doi": "10.1000/example",
                "title": "Example supported claim",
                "abstract": "Supported claim example abstract",
                "journal": "Example Journal",
                "score": 1.0,
            }
        ]
        analyzer._finalize_bibliography_entry = lambda doi, bib_file: None

        results = analyzer.suggest_citations_for_sentence(
            sentence,
            max_results=3,
            bib_file="references.bib",
        )

        self.assertEqual(results, [])

    def test_bib_searcher_uses_existing_bib_entry_for_final_inline_citation(self):
        module = load_module()
        analyzer = module.CitationNeedAnalyzer()

        sentence = "A supported claim requires a finalized bibliography entry."
        analyzer.search_for_citations = lambda *args, **kwargs: [
            {
                "doi": "10.1103/PhysRevB.97.205443",
                "title": "Interfacing planar superconducting qubits with high overtone bulk acoustic phonons",
                "abstract": "Superconducting qubits coupled to bulk acoustic phonons.",
                "journal": "Physical Review B",
            }
        ]
        analyzer.rerank_citations = lambda *args, **kwargs: [
            {
                "doi": "10.1103/PhysRevB.97.205443",
                "title": "Interfacing planar superconducting qubits with high overtone bulk acoustic phonons",
                "abstract": "Superconducting qubits coupled to bulk acoustic phonons.",
                "journal": "Physical Review B",
                "score": 1.0,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            bib_path = Path(tmpdir) / "references.bib"
            bib_path.write_text(
                """@article{ExistingKey,
  author = {Kervinen, Mikael and Rissanen, Ilkka and Sillanpaa, Mika},
  title = {Interfacing planar superconducting qubits with high overtone bulk acoustic phonons},
  journal = {Phys. Rev. B},
  volume = {97},
  pages = {205443},
  year = {2018},
  doi = {10.1103/physrevb.97.205443}
}""",
                encoding="utf-8",
            )

            results = analyzer.suggest_citations_for_sentence(
                sentence,
                max_results=3,
                bib_file=str(bib_path),
            )

        self.assertEqual(len(results), 1)
        self.assertIn("Phys. Rev. B", results[0]["inline_citation"])

    def test_bib_searcher_prefers_local_bib_before_external_search(self):
        module = load_module()
        analyzer = module.CitationNeedAnalyzer()

        sentence = (
            "Superconducting qubit sensors detect mechanical phonons via "
            "piezoelectric coupling to acoustic modes."
        )

        def fail_external_search(*args, **kwargs):
            raise AssertionError("external search should not run when local bibliography already matches")

        analyzer.search_for_citations = fail_external_search

        with tempfile.TemporaryDirectory() as tmpdir:
            bib_path = Path(tmpdir) / "references.bib"
            bib_path.write_text(
                """@article{Kervinen2018,
  author = {Kervinen, Mikael and Rissanen, Ilkka and Sillanpaa, Mika},
  title = {Interfacing planar superconducting qubits with high overtone bulk acoustic phonons},
  journal = {Phys. Rev. B},
  volume = {97},
  pages = {205443},
  year = {2018},
  doi = {10.1103/physrevb.97.205443}
}""",
                encoding="utf-8",
            )

            results = analyzer.suggest_citations_for_sentence(
                sentence,
                max_results=3,
                bib_file=str(bib_path),
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "local-bib")
        self.assertIn("Phys. Rev. B", results[0]["inline_citation"])


if __name__ == "__main__":
    unittest.main()
