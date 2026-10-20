"""Spec: formal-semantics.md §4.2 Replace - per SPARQL 1.1 REPLACE() / XPath
F&O 3.1 fn:replace, which is normative where the summary falls short.

Expected values are XPath's (F&O 3.1 §5.6.4 fn:replace, §5.6.1 flags, and the
XSD 1.1 regular-expression syntax F&O §5.6.1 builds on), not any host
library's.
"""

from __future__ import annotations

import pytest

from web_algebra.operation import Operation


def _replace(settings, input_, pattern, replacement, flags=None):
    args = {"input": input_, "pattern": pattern, "replacement": replacement}
    if flags is not None:
        args["flags"] = flags
    return str(Operation.process_json(settings, {"@op": "Replace", "args": args}))


@pytest.mark.parametrize(
    "input_, pattern, replacement, flags, expected",
    [
        # $ matches only at the very end of the string without the m flag
        ("a\n", "a$", "X", None, "a\n"),
        ("a\nb", "a$", "X", "m", "X\nb"),
        # ^ likewise only at the start without m
        ("x\na", "^a", "X", None, "x\na"),
        # Unicode category escapes are XSD regex syntax
        ("éb1", r"\p{L}", "X", None, "XX1"),
        ("éb1", r"\P{L}", "X", None, "ébX"),
        ("a1", r"\p{Nd}", "X", None, "aX"),
        # XSD multi-character escapes
        ("a b", r"\s", "_", None, "a_b"),
        ("a_b", r"\i", "X", None, "XXX"),
        # character-class subtraction
        ("abc", "[a-c-[b]]", "X", None, "XbX"),
        # $N beyond the groups: the longest digit run that names a group;
        # a group that does not exist is the zero-length string
        ("ab", "(a)", "$2", None, "b"),
        ("ab", "(a)", "$10", None, "a0b"),
        ("ab", "(a)(b)", "$2$1", None, "ba"),
        # escapes in the replacement
        ("ab", "a", r"\$", None, "$b"),
        ("ab", "a", r"\\", None, "\\b"),
        # x flag: whitespace in the pattern is removed; # is an ordinary char
        ("a#b", "a #b", "X", "x", "X"),
        ("a b", "a b", "X", "x", "a b"),
        # q flag: pattern and replacement are literal
        ("a.b", ".", "$1", "q", "a$1b"),
        # i flag
        ("AbA", "a", "x", "i", "xbx"),
        # s flag: . matches newline
        ("a\nb", "a.b", "X", "s", "X"),
        ("a\nb", "a.b", "X", None, "a\nb"),
    ],
)
def test_xpath_fn_replace(settings, input_, pattern, replacement, flags, expected):
    assert _replace(settings, input_, pattern, replacement, flags) == expected


@pytest.mark.parametrize(
    "pattern",
    [
        "(?P<n>a)",  # Python named group: not XSD syntax
        "(?i)a",  # inline flags: not XSD syntax
        "a{,2}",  # not a valid XSD quantifier
        r"\d+?(?=b)",  # lookahead: not XSD syntax
        "[",  # unterminated class
    ],
)
def test_a_pattern_that_is_not_xsd_regex_syntax_raises(settings, pattern):
    # FORX0002
    with pytest.raises(ValueError):
        _replace(settings, "ab", pattern, "X")


@pytest.mark.parametrize("replacement", ["${1}", "\\x", "$", "a\\"])
def test_an_invalid_replacement_raises(settings, replacement):
    # FORX0004
    with pytest.raises(ValueError):
        _replace(settings, "ab", "(a)", replacement)


@pytest.mark.parametrize("pattern", ["a*", "b?", "", "x|"])
def test_a_pattern_matching_the_empty_string_raises(settings, pattern):
    # FORX0003 (XPath 3.1)
    with pytest.raises(ValueError):
        _replace(settings, "ab", pattern, "X")


@pytest.mark.parametrize("flags", ["g", "ix ", "z"])
def test_invalid_flags_raise(settings, flags):
    # FORX0001
    with pytest.raises(ValueError):
        _replace(settings, "ab", "a", "X", flags)
