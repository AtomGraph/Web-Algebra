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

    def test_rfc3986_unreserved_set_passes_through(self, settings):
        # §4.2: everything except A–Z a–z 0–9 - . _ ~ is percent-encoded
        op = Operation.get("EncodeForURI")(settings=settings)
        result = op.execute(Literal("AZaz09-._~"))
        assert str(result) == "AZaz09-._~"

    def test_reserved_characters_are_encoded(self, settings):
        # §4.2: reserved characters like / : * ' are encoded (UTF-8)
        op = Operation.get("EncodeForURI")(settings=settings)
        assert str(op.execute(Literal("a/b"))) == "a%2Fb"
        assert str(op.execute(Literal("a:b"))) == "a%3Ab"
        assert str(op.execute(Literal("a*b"))) == "a%2Ab"
        assert str(op.execute(Literal("a'b"))) == "a%27b"


class TestEncodeForURIJson:
    def test_basic_via_json(self, settings):
        # JSON arg key from existing fixture tests/fixtures/positive/simple-composition-working.json
        op = Operation.get("EncodeForURI")(settings=settings)
        result = op.execute_json({"input": "hello world"})
        assert isinstance(result, Literal)
        assert str(result) == "hello%20world"
