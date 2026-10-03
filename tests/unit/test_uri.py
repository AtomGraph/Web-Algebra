"""Spec: formal-semantics.md §4.2 "URI — cast a Term to a URI"
Abstract: (URI + Literal) → URI
- URI input returned as-is; Literal yields the URI of its lexical form.
- BNode raises TypeError (a blank node has no IRI).
- The lexical form is NOT validated against RFC 3986.
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

    def test_bnode_raises_type_error(self, settings):
        # §4.2: a BNode raises TypeError — a blank node has no IRI
        op = Operation.get("URI")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(BNode("b1"))

    def test_invalid_uri_literal_is_not_validated(self, settings):
        # §4.2: the lexical form is not validated against RFC 3986 —
        # garbage in, garbage out
        op = Operation.get("URI")(settings=settings)
        result = op.execute(Literal("not a uri"))
        assert isinstance(result, URIRef)
        assert str(result) == "not a uri"


class TestURIJson:
    def test_string_input_via_json(self, settings):
        # JSON arg key from existing fixture tests/fixtures/positive/simple-operation.json
        op = Operation.get("URI")(settings=settings)
        result = op.execute_json({"input": "http://example.org/x"})
        assert isinstance(result, URIRef)
        assert str(result) == "http://example.org/x"
