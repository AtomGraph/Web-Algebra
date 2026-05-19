"""Spec: formal-semantics.md "ldh-AddObjectBlock - Add object content block to LinkedDataHub document"
Abstract: URI × URI × Maybe Literal × Maybe Literal × Maybe Literal × Maybe URI → Any
Python:   def execute(self, url: URIRef, value: URIRef, title: Literal = None,
                      description: Literal = None, fragment: Literal = None, mode: URIRef = None) -> Any
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestLDHAddObjectBlockPure:
    def test_wrong_url_type_raises(self, settings):
        op = Operation.get("ldh-AddObjectBlock")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("not-a-uri"), URIRef("https://example.org/value"))

    def test_wrong_value_type_raises(self, settings):
        op = Operation.get("ldh-AddObjectBlock")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("https://example.org/"), Literal("not-a-uri"))


@pytest.mark.ldh
class TestLDHAddObjectBlockLive:
    @pytest.mark.skip(reason="UNCLEAR(spec): return type `Any`")
    def test_basic(self, settings_with_auth):
        pass
