"""Spec: formal-semantics.md §4.3 "DESCRIBE — execute a SPARQL DESCRIBE query
over an endpoint or a graph"
Abstract: (URI + Graph) × Literal → Graph
Python:   def execute(self, source: URIRef | Graph, query: Literal) -> Graph
JSON:     endpoint: URI or graph: Graph (exactly one) · query: string Literal
- Exactly one of endpoint/graph: neither raises KeyError, both TypeError.
- With `graph` the operation is pure and local.
- What a description contains is the query processor's choice (SPARQL 1.1
  §16.4), so only the result type is asserted.
"""

from __future__ import annotations

import os

import pytest
from rdflib import Graph, Literal, URIRef

from web_algebra.operation import Operation

EX = "http://example.org/"


def _graph() -> Graph:
    g = Graph()
    g.add((URIRef(EX + "a"), URIRef(EX + "p"), Literal("1")))
    return g


def _no_network(request):
    raise AssertionError(f"unexpected network request: {request.get_method()} {request.full_url}")


class TestDESCRIBEPure:
    def test_wrong_source_type_raises(self, settings):
        op = Operation.get("DESCRIBE")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("http://example.org/sparql"), Literal("DESCRIBE <http://ex/x>"))

    def test_wrong_query_type_raises(self, settings):
        op = Operation.get("DESCRIBE")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("http://example.org/sparql"), URIRef("DESCRIBE <http://ex/x>"))

    def test_over_graph_returns_graph_without_network(self, settings, http_stub):
        # §4.3: with a Graph the query runs locally — pure, no network
        http_stub.handler = _no_network
        op = Operation.get("DESCRIBE")(settings=settings)
        result = op.execute(_graph(), Literal(f"DESCRIBE <{EX}a>"))
        assert isinstance(result, Graph)
        assert http_stub.requests == []


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
    def test_wrong_endpoint_type_raises_before_network(self, settings, http_stub):
        # §4.3 JSON: endpoint: URI · query: Literal (xsd:string).
        # §3.7: strict typing before any effect.
        http_stub.handler = _no_network
        op = Operation.get("DESCRIBE")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "endpoint": "http://example.org/sparql",
                    "query": "DESCRIBE <http://ex/x>",
                }
            )

    def test_neither_endpoint_nor_graph_raises_key_error(self, settings):
        op = Operation.get("DESCRIBE")(settings=settings)
        with pytest.raises(KeyError):
            op.execute_json({"query": "DESCRIBE <http://ex/x>"})

    def test_both_endpoint_and_graph_raise_type_error(self, settings, http_stub):
        http_stub.handler = _no_network
        op = Operation.get("DESCRIBE")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "endpoint": {"@id": "http://example.org/sparql"},
                    "graph": {"@id": EX + "a", EX + "p": "1"},
                    "query": f"DESCRIBE <{EX}a>",
                }
            )

    def test_graph_as_rdf_data_form(self, settings, http_stub):
        http_stub.handler = _no_network
        op = Operation.get("DESCRIBE")(settings=settings)
        result = op.execute_json(
            {"graph": {"@id": EX + "a", EX + "p": "1"}, "query": f"DESCRIBE <{EX}a>"}
        )
        assert isinstance(result, Graph)
        assert http_stub.requests == []
