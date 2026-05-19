"""Spec: formal-semantics.md "ldh-AddGenericService - Add generic SPARQL service to LinkedDataHub"
Abstract: URI × URI × Literal × Maybe Literal × Maybe Literal × Maybe URI × Maybe Literal × Maybe Literal → Any
Python:   def execute(self, url: URIRef, endpoint: URIRef, title: Literal,
                      description: Literal = None, fragment: Literal = None, graph_store: URIRef = None,
                      auth_user: Literal = None, auth_pwd: Literal = None) -> Any
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestLDHAddGenericServicePure:
    def test_wrong_url_type_raises(self, settings):
        op = Operation.get("ldh-AddGenericService")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                Literal("not-a-uri"),
                URIRef("https://example.org/sparql"),
                Literal("title"),
            )

    def test_wrong_endpoint_type_raises(self, settings):
        op = Operation.get("ldh-AddGenericService")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                URIRef("https://example.org/"),
                Literal("not-a-uri"),
                Literal("title"),
            )


@pytest.mark.ldh
class TestLDHAddGenericServiceLive:
    @pytest.mark.skip(reason="UNCLEAR(spec): return type `Any`")
    def test_basic(self, settings_with_auth):
        pass
