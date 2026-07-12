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
    def test_wrong_endpoint_type_raises_before_network(self, settings):
        # §4.3 JSON: endpoint: URI · query: Literal (xsd:string).
        # §3.7: TypeError raised before any effect — a plain string is a
        # string Literal (§2.2), not a URI.
        op = Operation.get("SELECT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "endpoint": "http://example.org/sparql",
                    "query": "SELECT * WHERE { ?s ?p ?o }",
                }
            )

    def test_wrong_query_type_raises_before_network(self, settings):
        op = Operation.get("SELECT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "endpoint": {"@id": "http://example.org/sparql"},
                    "query": {"@id": "http://example.org/not-a-query"},
                }
            )
