#!/usr/bin/env python3
"""Helpers for normalizing titles with inline math or markup."""

from __future__ import annotations

import re


def _unescape_overescaped_latex_math(value: str) -> str:
    value = value.replace(r"\textbraceleft", "{")
    value = value.replace(r"\textbraceright", "}")
    value = value.replace(r"\_", "_")
    value = value.replace(r"\$", "$")
    value = re.sub(r"\{\{([A-Za-z0-9+-]+)\}\}", r"{\1}", value)
    value = re.sub(r"\{\s*([A-Za-z0-9+-]+)\s*\}", r"{\1}", value)
    return value


def _strip_markup(value: str) -> str:
    value = value.replace("\n", " ")
    value = _unescape_overescaped_latex_math(value)
    value = re.sub(
        r"<mml:mi>\s*He\s*</mml:mi>.*?<mml:mn>\s*3\s*</mml:mn>",
        "3He",
        value,
        flags=re.I | re.S,
    )
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _normalize_uppercase_subscripts(value: str, formatter) -> str:
    pattern = re.compile(r"(?<!\w)\$?([A-Z])_\{?([A-Za-z0-9+-]+)\}?\$?(?!\w)")
    return pattern.sub(lambda match: formatter(match.group(1), match.group(2)), value)


def _normalize_latex_subscript_math(value: str, formatter) -> str:
    pattern = re.compile(r"\$\{+([A-Z])\}*_\{?([A-Za-z0-9+-]+)\}?\$")
    return pattern.sub(lambda match: formatter(match.group(1), match.group(2)), value)


def normalize_title_for_bibtex(raw_title: str) -> str:
    """Convert title metadata into a BibTeX-safe title string."""
    value = _strip_markup(raw_title)
    value = value.replace("$_2$", "2")
    value = value.replace("$_", "")
    value = _normalize_latex_subscript_math(
        value,
        lambda base, subscript: "{$" + base + "_" + subscript + "$}",
    )
    value = _normalize_uppercase_subscripts(
        value,
        lambda base, subscript: "{$" + base + "_" + subscript + "$}",
    )
    value = re.sub(r"\{\{(\$[^$]+\$)\}\}", r"{\1}", value)
    value = re.sub(r"(?<!\{)(\$[^$]+\$)(?!\})", r"{\1}", value)
    value = value.replace(" andV-I", " and V-I")
    value = value.replace("V-Icharacteristics", "V-I characteristics")
    value = value.replace("NbSe 2", "NbSe2")
    return value


def normalize_title_for_plain_text(raw_title: str) -> str:
    """Convert title metadata into a plain-text title string."""
    value = _strip_markup(raw_title)
    value = value.replace("$_2$", "2")
    value = value.replace("$_", "")
    value = _normalize_latex_subscript_math(
        value,
        lambda base, subscript: base + subscript,
    )
    value = _normalize_uppercase_subscripts(
        value,
        lambda base, subscript: base + subscript,
    )
    value = re.sub(r"\$([^$]+)\$", r"\1", value)
    value = value.replace("{", "").replace("}", "")
    value = value.replace(" andV-I", " and V-I")
    value = value.replace("V-Icharacteristics", "V-I characteristics")
    value = value.replace("NbSe 2", "NbSe2")
    return value
