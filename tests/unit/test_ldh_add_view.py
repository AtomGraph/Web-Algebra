"""Spec: formal-semantics.md "ldh-AddView - Add view to LinkedDataHub document"
Abstract: URI × URI × Literal × Maybe Literal × Maybe Literal × Maybe URI → Any
Python:   def execute(self, url: URIRef, query: URIRef, title: Literal, description: Literal = None,
                      fragment: Literal = None, mode: URIRef = None) -> Any
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestLDHAddViewPure:
    def test_wrong_url_type_raises(self, settings):
        op = Operation.get("ldh-AddView")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                Literal("not-a-uri"),
                URIRef("https://example.org/q"),
                Literal("title"),
            )

    def test_wrong_query_type_raises(self, settings):
        op = Operation.get("ldh-AddView")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                URIRef("https://example.org/"),
                Literal("not-a-uri"),
                Literal("title"),
            )

    def test_wrong_title_type_raises(self, settings):
        op = Operation.get("ldh-AddView")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                URIRef("https://example.org/"),
                URIRef("https://example.org/q"),
                URIRef("not-a-literal"),
            )


@pytest.mark.ldh
class TestLDHAddViewLive:
    @pytest.mark.skip(reason="UNCLEAR(spec): return type `Any` — what's a meaningful assertion?")
    def test_basic(self, settings_with_auth):
        pass
