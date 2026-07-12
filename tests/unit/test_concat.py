"""Spec: formal-semantics.md §4.2 "Concat — per SPARQL 1.1 CONCAT()":
string literal CONCAT(string literal ltrl1 ... string literal ltrln)
- All inputs typed xsd:string → xsd:string result.
- All inputs carrying the same language tag → result carries it too.
- All other cases (including no inputs) → simple literal.
"""

from __future__ import annotations

import pytest
from rdflib import Literal
from rdflib.namespace import XSD

from web_algebra.operation import Operation


class TestConcatPure:
    def test_concatenates_lexical_forms(self, settings):
        op = Operation.get("Concat")(settings=settings)
        result = op.execute([Literal("foo"), Literal("bar")])
        assert str(result) == "foobar"

    def test_all_xsd_string_yields_xsd_string(self, settings):
        # §4.2: all inputs typed xsd:string → xsd:string
        op = Operation.get("Concat")(settings=settings)
        result = op.execute(
            [Literal("foo", datatype=XSD.string), Literal("bar", datatype=XSD.string)]
        )
        assert result.datatype == XSD.string

    def test_same_language_tag_is_carried(self, settings):
        # §4.2: CONCAT("foo"@en, "bar"@en) → "foobar"@en
        op = Operation.get("Concat")(settings=settings)
        result = op.execute([Literal("foo", lang="en"), Literal("bar", lang="en")])
        assert result.language == "en"
        assert str(result) == "foobar"

    def test_mixed_kinds_yield_simple_literal(self, settings):
        # §4.2: in all other cases the result is a simple literal
        op = Operation.get("Concat")(settings=settings)
        result = op.execute([Literal("foo", lang="en"), Literal("bar")])
        assert result.datatype is None and result.language is None
        mixed_langs = op.execute([Literal("foo", lang="en"), Literal("bar", lang="de")])
        assert mixed_langs.datatype is None and mixed_langs.language is None

    def test_empty_inputs_yield_empty_simple_literal(self, settings):
        op = Operation.get("Concat")(settings=settings)
        result = op.execute([])
        assert str(result) == ""
        assert result.datatype is None and result.language is None

    def test_non_literal_input_raises_type_error(self, settings):
        # §3.7 strict typing
        op = Operation.get("Concat")(settings=settings)
        with pytest.raises(TypeError):
            op.execute([Literal("foo"), 42])
        with pytest.raises(TypeError):
            op.execute("not-a-list")


class TestConcatJson:
    def test_json_dispatch(self, settings):
        # §4.2 JSON: inputs: array of string-compatible Literal forms.
        # JSON string scalars coerce to xsd:string (§2.2), so the result is
        # xsd:string per the all-xsd:string rule.
        op = Operation.get("Concat")(settings=settings)
        result = op.execute_json({"inputs": ["http://ex/", "x"]})
        assert str(result) == "http://ex/x"
        assert result.datatype == XSD.string

    def test_nested_operations_in_inputs(self, settings):
        op = Operation.get("Concat")(settings=settings)
        result = op.execute_json(
            {
                "inputs": [
                    {"@op": "Str", "args": {"input": {"@id": "http://ex/a"}}},
                    "-b",
                ]
            }
        )
        assert str(result) == "http://ex/a-b"
