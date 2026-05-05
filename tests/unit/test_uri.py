"""Spec: formal-semantics.md "URI - Convert term to URI reference"
Abstract: Term → URI
Python:   def execute(self, term: rdflib.term.Node) -> rdflib.URIRef
Plus the Strict Type Checking property (lines 291-295).
"""

from __future__ import annotations

import pytest
from rdflib import BNode, Literal, URIRef

from web_algebra.operation import Operation


class TestURIPure:
    def test_urirefpassthrough(self, settings):
        op = Operation.get("URI")(settings=settings)
        result = op.execute(URIRef("http://example.org/foo"))
        assert isinstance(result, URIRef)
        assert str(result) == "http://example.org/foo"

    def test_literal_lexical_form_becomes_uri(self, settings):
        op = Operation.get("URI")(settings=settings)
        result = op.execute(Literal("http://example.org/bar"))
        assert isinstance(result, URIRef)
        assert str(result) == "http://example.org/bar"

    def test_non_term_raises_type_error(self, settings):
        # Strict Type Checking property: "TypeError raised for mismatched input types"
        op = Operation.get("URI")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(42)

    @pytest.mark.skip(reason="UNCLEAR(spec): URI(BNode) — spec lists BNode as a Term but doesn't define this case")
    def test_bnode_input(self, settings):
        op = Operation.get("URI")(settings=settings)
        op.execute(BNode("b1"))

    @pytest.mark.skip(reason="UNCLEAR(spec): URI(Literal whose lexical form is not a valid URI) unspecified")
    def test_invalid_uri_literal(self, settings):
        op = Operation.get("URI")(settings=settings)
        op.execute(Literal("not a uri"))


class TestURIJson:
    def test_string_input_via_json(self, settings):
        # JSON arg key from existing fixture tests/fixtures/positive/simple-operation.json
        op = Operation.get("URI")(settings=settings)
        result = op.execute_json({"input": "http://example.org/x"})
        assert isinstance(result, URIRef)
        assert str(result) == "http://example.org/x"
