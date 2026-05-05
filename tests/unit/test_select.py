"""Spec: formal-semantics.md "SELECT - Execute SPARQL SELECT query"
Abstract: URI × Literal → Result
Python:   def execute(self, endpoint: rdflib.URIRef, query: rdflib.Literal) -> rdflib.query.Result
"""

from __future__ import annotations

import os

import pytest
from rdflib import Literal, URIRef
from rdflib.query import Result

from web_algebra.operation import Operation


class TestSELECTPure:
    def test_wrong_endpoint_type_raises(self, settings):
        op = Operation.get("SELECT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("http://example.org/sparql"), Literal("ASK { ?s ?p ?o }"))

    def test_wrong_query_type_raises(self, settings):
        op = Operation.get("SELECT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("http://example.org/sparql"), URIRef("ASK { ?s ?p ?o }"))


@pytest.mark.sparql
class TestSELECTLive:
    def test_returns_result(self, settings):
        endpoint = os.getenv("SPARQL_ENDPOINT")
        if not endpoint:
            pytest.skip("SPARQL_ENDPOINT env var not set")
        op = Operation.get("SELECT")(settings=settings)
        result = op.execute(URIRef(endpoint), Literal("SELECT * WHERE { ?s ?p ?o } LIMIT 1"))
        assert isinstance(result, Result)


class TestSELECTJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): SELECT JSON arg shape — existing fixtures show `{query, endpoint}` for CONSTRUCT but SELECT is not exemplified")
    def test_json_dispatch(self, settings):
        pass
