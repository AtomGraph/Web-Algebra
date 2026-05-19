"""Spec: formal-semantics.md "EncodeForURI - URL-encode strings for URI usage"
Abstract: Literal → Literal
Python:   def execute(self, input_str: Literal) -> Literal
Plus Strict Type Checking property.
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestEncodeForURIPure:
    def test_space_to_percent20(self, settings):
        # Space → %20 is uncontroversial across RFC 3986 and SPARQL ENCODE_FOR_URI.
        op = Operation.get("EncodeForURI")(settings=settings)
        result = op.execute(Literal("hello world"))
        assert isinstance(result, Literal)
        assert str(result) == "hello%20world"

    def test_no_special_chars_passes_through(self, settings):
        op = Operation.get("EncodeForURI")(settings=settings)
        result = op.execute(Literal("abc123"))
        assert isinstance(result, Literal)
        assert str(result) == "abc123"

    def test_uri_input_raises(self, settings):
        op = Operation.get("EncodeForURI")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("http://example.org/x"))

    @pytest.mark.skip(reason="UNCLEAR(spec): which character set / RFC — `~`, `*`, `'`, etc. differ across RFC 3986 and SPARQL ENCODE_FOR_URI")
    def test_reserved_character_set(self, settings):
        pass


class TestEncodeForURIJson:
    def test_basic_via_json(self, settings):
        # JSON arg key from existing fixture tests/fixtures/positive/simple-composition-working.json
        op = Operation.get("EncodeForURI")(settings=settings)
        result = op.execute_json({"input": "hello world"})
        assert isinstance(result, Literal)
        assert str(result) == "hello%20world"
