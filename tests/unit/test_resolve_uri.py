"""Spec: formal-semantics.md "ResolveURI - Resolve relative URI against base URI"
Abstract: URI × Literal → URI
Python:   def execute(self, base: URIRef, relative: Literal) -> URIRef
Plus the URI Resolution property (lines 320-325) and Strict Type Checking.
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestResolveURIPure:
    def test_relative_appends_to_base(self, settings):
        op = Operation.get("ResolveURI")(settings=settings)
        result = op.execute(URIRef("http://example.org/base/"), Literal("foo"))
        assert isinstance(result, URIRef)
        assert str(result) == "http://example.org/base/foo"

    def test_relative_uplevel(self, settings):
        # RFC 3986-style resolution: "../up" relative to "http://example.org/base/" → "http://example.org/up"
        op = Operation.get("ResolveURI")(settings=settings)
        result = op.execute(URIRef("http://example.org/base/"), Literal("../up"))
        assert isinstance(result, URIRef)
        assert str(result) == "http://example.org/up"

    def test_fragment_relative(self, settings):
        # URI Resolution property line 322: "Fragment URIs ... resolve against target document URI"
        op = Operation.get("ResolveURI")(settings=settings)
        result = op.execute(URIRef("http://example.org/doc"), Literal("#frag"))
        assert isinstance(result, URIRef)
        assert str(result) == "http://example.org/doc#frag"

    def test_wrong_base_type_raises(self, settings):
        op = Operation.get("ResolveURI")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("http://example.org/base/"), Literal("foo"))

    def test_wrong_relative_type_raises(self, settings):
        op = Operation.get("ResolveURI")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("http://example.org/base/"), URIRef("foo"))

    @pytest.mark.skip(reason="UNCLEAR(spec): behavior when relative is itself an absolute URI")
    def test_absolute_relative(self, settings):
        pass


class TestResolveURIJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): JSON arg key names for ResolveURI not given by spec or existing fixtures")
    def test_json_dispatch(self, settings):
        pass
