"""Spec: formal-semantics.md "DESCRIBE - Execute SPARQL DESCRIBE query"
Abstract: URI × Literal → Graph
Python:   def execute(self, endpoint: rdflib.URIRef, query: rdflib.Literal) -> rdflib.Graph
"""

from __future__ import annotations

import os

import pytest
from rdflib import Graph, Literal, URIRef

from web_algebra.operation import Operation


class TestDESCRIBEPure:
    def test_wrong_endpoint_type_raises(self, settings):
        op = Operation.get("DESCRIBE")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("http://example.org/sparql"), Literal("DESCRIBE <http://ex/x>"))

    def test_wrong_query_type_raises(self, settings):
        op = Operation.get("DESCRIBE")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("http://example.org/sparql"), URIRef("DESCRIBE <http://ex/x>"))


@pytest.mark.sparql
class TestDESCRIBELive:
    def test_returns_graph(self, settings):
        endpoint = os.getenv("SPARQL_ENDPOINT")
        if not endpoint:
            pytest.skip("SPARQL_ENDPOINT env var not set")
        op = Operation.get("DESCRIBE")(settings=settings)
        result = op.execute(URIRef(endpoint), Literal("DESCRIBE <http://example.org/foo>"))
        assert isinstance(result, Graph)


class TestDESCRIBEJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): DESCRIBE JSON arg shape not exemplified by existing fixtures")
    def test_json_dispatch(self, settings):
        pass
