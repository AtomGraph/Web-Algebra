"""Spec: formal-semantics.md "Str - Convert any term to string literal"
Abstract: Term → Literal
Python:   def execute(self, term: rdflib.term.Node) -> rdflib.Literal
Plus the Strict Type Checking property (lines 291-295).
"""

from __future__ import annotations

import pytest
from rdflib import BNode, Literal, URIRef

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

    @pytest.mark.skip(reason="UNCLEAR(spec): result Literal datatype (xsd:string vs simple literal) unspecified")
    def test_result_datatype(self, settings):
        pass


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
