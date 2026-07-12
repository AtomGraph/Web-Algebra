"""Spec: formal-semantics.md §4.2 "Replace — per SPARQL 1.1 REPLACE() /
XPath fn:replace": string literal REPLACE(string literal arg, simple literal
pattern, simple literal replacement [, simple literal flags])
- Replacement string: $N = capture group, \\$ = literal dollar, \\\\ = literal
  backslash; other uses of \\ or $ are errors.
- Flags: s, m, i, x, q; invalid flags/pattern/zero-length-matching pattern/
  invalid replacement → ValueError (XPath err:FORX000*).
- pattern/replacement/flags must be simple literals (language tag → TypeError).
- The result is a string literal of the same kind as arg.
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef
from rdflib.namespace import XSD

from web_algebra.operation import Operation


class TestReplacePure:
    def test_basic_replace(self, settings):
        op = Operation.get("Replace")(settings=settings)
        result = op.execute(Literal("Hello World"), Literal("World"), Literal("Universe"))
        assert isinstance(result, Literal)
        assert str(result) == "Hello Universe"

    def test_pattern_is_a_regular_expression(self, settings):
        # §4.2: XPath fn:replace pattern semantics
        op = Operation.get("Replace")(settings=settings)
        result = op.execute(Literal("a1b2c3"), Literal("[0-9]"), Literal("#"))
        assert str(result) == "a#b#c#"

    def test_group_reference_with_dollar(self, settings):
        # §4.2: $N references capture group N — fn:replace example:
        # replace("abracadabra", "a(.)", "a$1$1") = "abbraccaddabbra"
        op = Operation.get("Replace")(settings=settings)
        result = op.execute(
            Literal("abracadabra"), Literal("a(.)"), Literal("a$1$1")
        )
        assert str(result) == "abbraccaddabbra"

    def test_escaped_dollar_is_literal(self, settings):
        # §4.2: \$ is a literal dollar in the replacement
        op = Operation.get("Replace")(settings=settings)
        result = op.execute(Literal("price"), Literal("price"), Literal("\\$5"))
        assert str(result) == "$5"

    def test_bare_dollar_in_replacement_raises(self, settings):
        # §4.2: any other use of $ is an error (err:FORX0004)
        op = Operation.get("Replace")(settings=settings)
        with pytest.raises(ValueError):
            op.execute(Literal("abc"), Literal("b"), Literal("x$y"))

    def test_case_insensitive_flag(self, settings):
        # §4.2: flags per fn:replace — i
        op = Operation.get("Replace")(settings=settings)
        result = op.execute(Literal("ABC"), Literal("b"), Literal("x"), Literal("i"))
        assert str(result) == "AxC"

    def test_q_flag_treats_pattern_literally(self, settings):
        # §4.2: flags per fn:replace — q
        op = Operation.get("Replace")(settings=settings)
        result = op.execute(Literal("a.b.c"), Literal("."), Literal("x"), Literal("q"))
        assert str(result) == "axbxc"

    def test_invalid_flag_raises_value_error(self, settings):
        # §3.7/§4.2: invalid flags → ValueError (err:FORX0001)
        op = Operation.get("Replace")(settings=settings)
        with pytest.raises(ValueError):
            op.execute(Literal("abc"), Literal("b"), Literal("x"), Literal("z"))

    def test_zero_length_matching_pattern_raises(self, settings):
        # §3.7/§4.2: pattern matching the zero-length string → ValueError
        # (err:FORX0003)
        op = Operation.get("Replace")(settings=settings)
        with pytest.raises(ValueError):
            op.execute(Literal("abc"), Literal("b?"), Literal("x"))

    def test_result_kind_follows_first_argument(self, settings):
        # §4.2: the result is a string literal of the same kind as arg
        op = Operation.get("Replace")(settings=settings)
        typed = op.execute(
            Literal("chat", datatype=XSD.string), Literal("ch"), Literal("h")
        )
        assert typed.datatype == XSD.string
        tagged = op.execute(Literal("chat", lang="en"), Literal("ch"), Literal("h"))
        assert tagged.language == "en"
        assert str(tagged) == "hat"
        simple = op.execute(Literal("chat"), Literal("ch"), Literal("h"))
        assert simple.datatype is None and simple.language is None

    def test_lang_tagged_pattern_raises_type_error(self, settings):
        # §4.2: pattern must be a simple literal per the REPLACE signature
        op = Operation.get("Replace")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("chat"), Literal("ch", lang="en"), Literal("h"))

    def test_uri_input_raises_type_error(self, settings):
        # §3.7 strict typing
        op = Operation.get("Replace")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("http://example.org/x"), Literal("x"), Literal("y"))

    def test_uri_pattern_raises(self, settings):
        op = Operation.get("Replace")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("Hello"), URIRef("http://example.org/x"), Literal("y"))

    def test_uri_replacement_raises(self, settings):
        op = Operation.get("Replace")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("Hello"), Literal("e"), URIRef("http://example.org/x"))


class TestReplaceJson:
    def test_basic_via_json(self, settings):
        # §4.2 JSON: input · pattern · replacement · flags (optional)
        op = Operation.get("Replace")(settings=settings)
        result = op.execute_json(
            {"input": "Hello World", "pattern": "World", "replacement": "Universe"}
        )
        assert isinstance(result, Literal)
        assert str(result) == "Hello Universe"

    def test_flags_via_json(self, settings):
        op = Operation.get("Replace")(settings=settings)
        result = op.execute_json(
            {"input": "ABC", "pattern": "b", "replacement": "x", "flags": "i"}
        )
        assert str(result) == "AxC"

    def test_uri_input_raises_via_json(self, settings):
        op = Operation.get("Replace")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "input": {"@op": "URI", "args": {"input": "http://example.org/test"}},
                    "pattern": "test",
                    "replacement": "example",
                }
            )
