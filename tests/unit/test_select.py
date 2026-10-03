"""Spec: formal-semantics.md §4.3 "SELECT — execute a SPARQL SELECT query over
an endpoint or a graph"
Abstract: (URI + Graph) × Literal → Result
Python:   def execute(self, source: URIRef | Graph, query: Literal) -> Result
JSON:     endpoint: URI or graph: Graph (exactly one) · query: string Literal
- Exactly one of endpoint/graph: neither raises KeyError, both TypeError.
- With `graph` the operation is pure and local; with `endpoint` it is a query
  effect. Types are validated before any network I/O (§3.7).
- In JSON, `graph` takes a Graph value or an RDF data form (no base IRI).
- A read answered outside 2xx propagates urllib's HTTPError (§3.7).
"""

from __future__ import annotations

import json
import os
import urllib.error

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import XSD
from rdflib.query import Result

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


class TestSELECTPure:
    def test_wrong_source_type_raises(self, settings):
        op = Operation.get("SELECT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("http://example.org/sparql"), Literal("SELECT * WHERE { ?s ?p ?o }"))

    def test_wrong_query_type_raises(self, settings):
        op = Operation.get("SELECT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("http://example.org/sparql"), URIRef("SELECT * WHERE { ?s ?p ?o }"))

    def test_wrong_query_type_over_graph_raises(self, settings):
        op = Operation.get("SELECT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(_graph(), URIRef("SELECT * WHERE { ?s ?p ?o }"))

    def test_over_graph_returns_result(self, settings, http_stub):
        # §4.3: with a Graph the query runs locally — pure, no network
        http_stub.handler = _no_network
        op = Operation.get("SELECT")(settings=settings)
        result = op.execute(
            _graph(),
            Literal(f"SELECT ?s ?o WHERE {{ ?s <{EX}p> ?o }} ORDER BY ?s"),
        )
        assert isinstance(result, Result)
        rows = list(result)
        assert [str(r["s"]) for r in rows] == [EX + "a", EX + "b"]
        assert [str(r["o"]) for r in rows] == ["1", "2"]
        assert http_stub.requests == []

    def test_over_graph_accepts_xsd_string_query(self, settings, http_stub):
        # §4.3: query is a string Literal, simple or xsd:string
        http_stub.handler = _no_network
        op = Operation.get("SELECT")(settings=settings)
        result = op.execute(
            _graph(),
            Literal("SELECT ?s WHERE { ?s ?p ?o }", datatype=XSD.string),
        )
        assert len(list(result)) == 2

    def test_over_empty_graph_yields_no_rows(self, settings, http_stub):
        http_stub.handler = _no_network
        op = Operation.get("SELECT")(settings=settings)
        result = op.execute(Graph(), Literal("SELECT ?s WHERE { ?s ?p ?o }"))
        assert isinstance(result, Result)
        assert len(list(result)) == 0


class TestSELECTEndpointStubbed:
    def test_over_endpoint_returns_result(self, settings, http_stub):
        # §4.3: with an endpoint, the response is negotiated as SPARQL Results
        body = json.dumps(
            {
                "head": {"vars": ["s"]},
                "results": {"bindings": [{"s": {"type": "uri", "value": EX + "a"}}]},
            }
        ).encode()
        http_stub.handler = lambda request: StubResponse(
            200, {"Content-Type": "application/sparql-results+json"}, body
        )
        op = Operation.get("SELECT")(settings=settings)
        result = op.execute(URIRef(EX + "sparql"), Literal("SELECT ?s WHERE { ?s ?p ?o }"))
        assert isinstance(result, Result)
        assert [r["s"] for r in result] == [URIRef(EX + "a")]
        assert len(http_stub.queries()) == 1
        assert "SELECT ?s WHERE { ?s ?p ?o }" in http_stub.queries()[0]

    def test_read_answered_non_2xx_propagates_http_error(self, settings, http_stub):
        # §3.7: a read (a SPARQL query) answered outside 2xx → HTTPError,
        # unwrapped
        http_stub.handler = lambda request: StubResponse(500)
        op = Operation.get("SELECT")(settings=settings)
        with pytest.raises(urllib.error.HTTPError):
            op.execute(URIRef(EX + "sparql"), Literal("SELECT * WHERE { ?s ?p ?o }"))


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
    def test_wrong_endpoint_type_raises_before_network(self, settings, http_stub):
        # §4.3 JSON: endpoint: URI · query: Literal (xsd:string).
        # §3.7: TypeError raised before any effect — a plain string is a
        # string Literal (§2.2), not a URI.
        http_stub.handler = _no_network
        op = Operation.get("SELECT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "endpoint": "http://example.org/sparql",
                    "query": "SELECT * WHERE { ?s ?p ?o }",
                }
            )

    def test_wrong_query_type_raises_before_network(self, settings, http_stub):
        http_stub.handler = _no_network
        op = Operation.get("SELECT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "endpoint": {"@id": "http://example.org/sparql"},
                    "query": {"@id": "http://example.org/not-a-query"},
                }
            )

    def test_neither_endpoint_nor_graph_raises_key_error(self, settings):
        # §4.3: exactly one of endpoint/graph — neither raises KeyError
        op = Operation.get("SELECT")(settings=settings)
        with pytest.raises(KeyError):
            op.execute_json({"query": "SELECT * WHERE { ?s ?p ?o }"})

    def test_both_endpoint_and_graph_raise_type_error(self, settings, http_stub):
        # §4.3: exactly one of endpoint/graph — both raise TypeError
        http_stub.handler = _no_network
        op = Operation.get("SELECT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "endpoint": {"@id": "http://example.org/sparql"},
                    "graph": {"@id": EX + "a", EX + "p": "1"},
                    "query": "SELECT * WHERE { ?s ?p ?o }",
                }
            )

    def test_graph_as_rdf_data_form(self, settings, http_stub):
        # §4.3: in JSON, `graph` takes an RDF data form, parsed with no base
        http_stub.handler = _no_network
        op = Operation.get("SELECT")(settings=settings)
        result = op.execute_json(
            {
                "graph": {"@id": EX + "a", EX + "p": "1"},
                "query": f"SELECT ?o WHERE {{ <{EX}a> <{EX}p> ?o }}",
            }
        )
        assert isinstance(result, Result)
        assert [str(r["o"]) for r in result] == ["1"]
        assert http_stub.requests == []

    def test_graph_as_graph_value(self, settings, http_stub):
        # §4.3: `graph` takes a Graph value, e.g. the output of Merge
        http_stub.handler = _no_network
        op = Operation.get("SELECT")(settings=settings)
        result = op.execute_json(
            {
                "graph": {
                    "@op": "Merge",
                    "args": {
                        "graphs": [
                            {"@id": EX + "a", EX + "p": "1"},
                            {"@id": EX + "b", EX + "p": "2"},
                        ]
                    },
                },
                "query": f"SELECT ?s WHERE {{ ?s <{EX}p> ?o }} ORDER BY ?s",
            }
        )
        assert [str(r["s"]) for r in result] == [EX + "a", EX + "b"]

    def test_graph_of_wrong_type_raises_type_error(self, settings, http_stub):
        # §3.7: graph must be a Graph or RDF data form — a string Literal is
        # neither
        http_stub.handler = _no_network
        op = Operation.get("SELECT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {"graph": "not a graph", "query": "SELECT * WHERE { ?s ?p ?o }"}
            )

    def test_relative_iri_in_graph_form(self, settings):
        pytest.skip(
            "UNCLEAR(spec): §4.3 says a `graph` data form is parsed with no "
            "base IRI so its IRIs must be absolute, but not what a relative "
            "IRI does (error, dropped triple, or left relative)"
        )
