"""Spec: formal-semantics.md §4.3 "CONSTRUCT — execute a SPARQL CONSTRUCT
query over an endpoint or a graph"
Abstract: (URI + Graph) × Literal → Graph
Python:   def execute(self, source: URIRef | Graph, query: Literal) -> Graph
JSON:     endpoint: URI or graph: Graph (exactly one) · query: string Literal
- Exactly one of endpoint/graph: neither raises KeyError, both TypeError.
- With `graph` the operation is pure and local; with `endpoint` it is a query
  effect, the response negotiated as an RDF serialization.
- In JSON, `graph` takes a Graph value or an RDF data form (no base IRI).
"""

from __future__ import annotations

import os
import urllib.error

import pytest
from rdflib import Graph, Literal, URIRef

from tests.http_stub import StubResponse
from web_algebra.operation import Operation

EX = "http://example.org/"


def _graph() -> Graph:
    g = Graph()
    g.add((URIRef(EX + "a"), URIRef(EX + "p"), Literal("1")))
    g.add((URIRef(EX + "b"), URIRef(EX + "p"), Literal("2")))
    return g


def _no_network(request):
    raise AssertionError(f"unexpected network request: {request.get_method()} {request.full_url}")


class TestCONSTRUCTPure:
    def test_wrong_source_type_raises(self, settings):
        op = Operation.get("CONSTRUCT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("http://example.org/sparql"), Literal("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"))

    def test_wrong_query_type_raises(self, settings):
        op = Operation.get("CONSTRUCT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("http://example.org/sparql"), URIRef("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"))

    def test_over_graph_returns_constructed_graph(self, settings, http_stub):
        # §4.3: with a Graph the query runs locally — pure, no network
        http_stub.handler = _no_network
        op = Operation.get("CONSTRUCT")(settings=settings)
        result = op.execute(
            _graph(),
            Literal(f"CONSTRUCT {{ ?s <{EX}q> ?o }} WHERE {{ ?s <{EX}p> ?o }}"),
        )
        assert isinstance(result, Graph)
        assert len(result) == 2
        assert (URIRef(EX + "a"), URIRef(EX + "q"), Literal("1")) in result
        assert (URIRef(EX + "b"), URIRef(EX + "q"), Literal("2")) in result
        assert http_stub.requests == []

    def test_wrong_query_type_over_graph_raises(self, settings):
        op = Operation.get("CONSTRUCT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(_graph(), URIRef("CONSTRUCT WHERE { ?s ?p ?o }"))


class TestCONSTRUCTEndpointStubbed:
    def test_over_endpoint_returns_graph(self, settings, http_stub):
        http_stub.handler = lambda request: StubResponse(
            200,
            {"Content-Type": "application/n-triples"},
            f"<{EX}a> <{EX}p> \"1\" .\n".encode(),
        )
        op = Operation.get("CONSTRUCT")(settings=settings)
        result = op.execute(
            URIRef(EX + "sparql"), Literal("CONSTRUCT WHERE { ?s ?p ?o }")
        )
        assert isinstance(result, Graph)
        assert (URIRef(EX + "a"), URIRef(EX + "p"), Literal("1")) in result

    def test_read_answered_non_2xx_propagates_http_error(self, settings, http_stub):
        # §3.7: a read answered outside 2xx → HTTPError, unwrapped
        http_stub.handler = lambda request: StubResponse(503)
        op = Operation.get("CONSTRUCT")(settings=settings)
        with pytest.raises(urllib.error.HTTPError):
            op.execute(URIRef(EX + "sparql"), Literal("CONSTRUCT WHERE { ?s ?p ?o }"))


@pytest.mark.sparql
class TestCONSTRUCTLive:
    def test_returns_graph(self, settings):
        endpoint = os.getenv("SPARQL_ENDPOINT")
        if not endpoint:
            pytest.skip("SPARQL_ENDPOINT env var not set")
        op = Operation.get("CONSTRUCT")(settings=settings)
        result = op.execute(
            URIRef(endpoint),
            Literal("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 1"),
        )
        assert isinstance(result, Graph)


class TestCONSTRUCTJson:
    def test_wrong_endpoint_type_raises_before_network(self, settings, http_stub):
        # §3.7: a plain string is a string Literal (§2.2), not a URI
        http_stub.handler = _no_network
        op = Operation.get("CONSTRUCT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "endpoint": "http://example.org/sparql",
                    "query": "CONSTRUCT WHERE { ?s ?p ?o }",
                }
            )

    def test_neither_endpoint_nor_graph_raises_key_error(self, settings):
        # §4.3: neither raises KeyError
        op = Operation.get("CONSTRUCT")(settings=settings)
        with pytest.raises(KeyError):
            op.execute_json({"query": "CONSTRUCT WHERE { ?s ?p ?o }"})

    def test_both_endpoint_and_graph_raise_type_error(self, settings, http_stub):
        # §4.3: both raise TypeError
        http_stub.handler = _no_network
        op = Operation.get("CONSTRUCT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "endpoint": {"@id": "http://example.org/sparql"},
                    "graph": {"@id": EX + "a", EX + "p": "1"},
                    "query": "CONSTRUCT WHERE { ?s ?p ?o }",
                }
            )

    def test_graph_as_rdf_data_form(self, settings, http_stub):
        # §4.3: in JSON, `graph` takes an RDF data form
        http_stub.handler = _no_network
        op = Operation.get("CONSTRUCT")(settings=settings)
        result = op.execute_json(
            {
                "graph": {"@id": EX + "a", EX + "p": "1"},
                "query": f"CONSTRUCT {{ ?s <{EX}q> ?o }} WHERE {{ ?s <{EX}p> ?o }}",
            }
        )
        assert isinstance(result, Graph)
        assert set(result) == {(URIRef(EX + "a"), URIRef(EX + "q"), Literal("1"))}

    def test_graph_from_upstream_construct(self, settings, http_stub):
        # §4.3: `graph` takes a Graph value — here CONSTRUCT over CONSTRUCT
        http_stub.handler = _no_network
        op = Operation.get("CONSTRUCT")(settings=settings)
        result = op.execute_json(
            {
                "graph": {
                    "@op": "CONSTRUCT",
                    "args": {
                        "graph": {"@id": EX + "a", EX + "p": "1"},
                        "query": f"CONSTRUCT {{ ?s <{EX}q> ?o }} WHERE {{ ?s <{EX}p> ?o }}",
                    },
                },
                "query": f"CONSTRUCT {{ ?s <{EX}r> ?o }} WHERE {{ ?s <{EX}q> ?o }}",
            }
        )
        assert set(result) == {(URIRef(EX + "a"), URIRef(EX + "r"), Literal("1"))}
