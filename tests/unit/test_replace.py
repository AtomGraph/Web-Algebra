"""Spec: formal-semantics.md "Replace - Replace patterns in strings using regex"
Abstract: Literal × Literal × Literal → Literal
Python:   def execute(self, input_str: rdflib.Literal, pattern: rdflib.Literal,
                      replacement: rdflib.Literal) -> rdflib.Literal
Plus Strict Type Checking property.
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestReplacePure:
    def test_basic_replace(self, settings):
        # Pattern that's identical as literal or regex — robust against the regex/literal ambiguity
        op = Operation.get("Replace")(settings=settings)
        result = op.execute(Literal("Hello World"), Literal("World"), Literal("Universe"))
        assert isinstance(result, Literal)
        assert str(result) == "Hello Universe"

    def test_uri_input_raises_type_error(self, settings):
        # Strict Type Checking property: TypeError on mismatched input.
        # Same as existing fixture tests/fixtures/negative/error-case-type-mismatch-uri-to-string.json
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

    def test_pattern_is_a_regular_expression(self, settings):
        # §4.2: the pattern is a regular expression (Python re dialect)
        op = Operation.get("Replace")(settings=settings)
        result = op.execute(Literal("a1b2c3"), Literal("[0-9]"), Literal("#"))
        assert str(result) == "a#b#c#"


class TestReplaceJson:
    def test_basic_via_json(self, settings):
        # JSON arg keys from existing fixture tests/fixtures/positive/complex-operation.json
        op = Operation.get("Replace")(settings=settings)
        result = op.execute_json(
            {"input": "Hello World", "pattern": "World", "replacement": "Universe"}
        )
        assert isinstance(result, Literal)
        assert str(result) == "Hello Universe"

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
