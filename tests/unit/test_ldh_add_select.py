"""Spec: formal-semantics.md "ldh-AddSelect - Add SPARQL SELECT service to LinkedDataHub"
Abstract: URI × Literal × Literal × Maybe Literal × Maybe Literal × Maybe URI → Any
Python:   def execute(self, url: URIRef, query: Literal, title: Literal, description: Literal = None,
                      fragment: Literal = None, service: URIRef = None) -> Any
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestLDHAddSelectPure:
    def test_wrong_url_type_raises(self, settings):
        op = Operation.get("ldh-AddSelect")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                Literal("not-a-uri"),
                Literal("SELECT * WHERE { ?s ?p ?o }"),
                Literal("title"),
            )

    def test_wrong_query_type_raises(self, settings):
        op = Operation.get("ldh-AddSelect")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                URIRef("https://example.org/"),
                URIRef("not-a-literal"),
                Literal("title"),
            )


@pytest.mark.ldh
class TestLDHAddSelectLive:
    @pytest.mark.skip(reason="UNCLEAR(spec): return type `Any`. Covered by integration LDH composition fixture instead.")
    def test_basic(self, settings_with_auth):
        pass
