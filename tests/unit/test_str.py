"""Spec: formal-semantics.md §4.2 "Str — cast a Term to a string literal"
Abstract: Term → Literal
- String-compatible literals pass through unchanged (language tag preserved).
- Any other Term yields a Literal of its lexical/IRI form, datatype xsd:string.
- Non-Terms raise TypeError (§3.7 strict typing).
"""

from __future__ import annotations

import pytest
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import XSD

from web_algebra.operation import Operation


class TestStrPure:
    def test_uri_returns_literal(self, settings):
        op = Operation.get("Str")(settings=settings)
        result = op.execute(URIRef("http://example.org/foo"))
        assert isinstance(result, Literal)
        assert str(result) == "http://example.org/foo"

    def test_literal_returns_literal(self, settings):
        op = Operation.get("Str")(settings=settings)
        result = op.execute(Literal("hello"))
        assert isinstance(result, Literal)
        assert str(result) == "hello"

    def test_bnode_returns_literal(self, settings):
        op = Operation.get("Str")(settings=settings)
        bn = BNode("b1")
        result = op.execute(bn)
        assert isinstance(result, Literal)
        assert str(result) == str(bn)

    def test_non_term_raises_type_error(self, settings):
        # Strict Type Checking property: "TypeError raised for mismatched input types"
        op = Operation.get("Str")(settings=settings)
        with pytest.raises(TypeError):
            op.execute([1, 2, 3])

    def test_uri_input_yields_xsd_string(self, settings):
        # §4.2: a non-string-compatible Term yields xsd:string of its IRI form
        op = Operation.get("Str")(settings=settings)
        result = op.execute(URIRef("http://example.org/foo"))
        assert result.datatype == XSD.string

    def test_plain_literal_passes_through_unchanged(self, settings):
        # §4.2: string-compatible literals pass through unchanged
        op = Operation.get("Str")(settings=settings)
        term = Literal("hello")
        result = op.execute(term)
        assert result == term
        assert result.datatype is None

    def test_lang_tagged_literal_preserves_tag(self, settings):
        # §4.2: language tag is preserved on passthrough (documented
        # divergence from SPARQL STR(), which drops it)
        op = Operation.get("Str")(settings=settings)
        term = Literal("hallo", lang="de")
        result = op.execute(term)
        assert result == term
        assert result.language == "de"

    def test_typed_literal_yields_xsd_string_of_lexical_form(self, settings):
        # §4.2: any other Term → xsd:string of its lexical form
        op = Operation.get("Str")(settings=settings)
        result = op.execute(Literal(42))
        assert result.datatype == XSD.string
        assert str(result) == "42"


class TestStrJson:
    def test_string_input_via_json(self, settings):
        # JSON arg key derived from existing fixture tests/fixtures/positive/simple-operation.json
        op = Operation.get("Str")(settings=settings)
        result = op.execute_json({"input": "hello"})
        assert isinstance(result, Literal)
        assert str(result) == "hello"

    def test_nested_uri_op(self, settings):
        op = Operation.get("Str")(settings=settings)
        result = op.execute_json(
            {"input": {"@op": "URI", "args": {"input": "http://example.org/x"}}}
        )
        assert isinstance(result, Literal)
        assert str(result) == "http://example.org/x"
