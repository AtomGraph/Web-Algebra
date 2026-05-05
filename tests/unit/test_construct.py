"""Spec: formal-semantics.md "CONSTRUCT - Execute SPARQL CONSTRUCT query"
Abstract: URI × Literal → Graph
Python:   def execute(self, endpoint: rdflib.URIRef, query: rdflib.Literal) -> rdflib.Graph
"""

from __future__ import annotations

import os

import pytest
from rdflib import Graph, Literal, URIRef

from web_algebra.operation import Operation


class TestCONSTRUCTPure:
    def test_wrong_endpoint_type_raises(self, settings):
        op = Operation.get("CONSTRUCT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("http://example.org/sparql"), Literal("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"))

    def test_wrong_query_type_raises(self, settings):
        op = Operation.get("CONSTRUCT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("http://example.org/sparql"), URIRef("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"))


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
    def test_json_dispatch_arg_shape(self, settings):
        # JSON arg keys from existing fixture tests/fixtures/positive/linkeddatahub-put-test.json:
        # CONSTRUCT takes {"query": <literal>, "endpoint": <URI>}.
        # We can't dispatch live without an endpoint, but we can validate the call raises
        # something other than KeyError when the arg shape is correct.
        op = Operation.get("CONSTRUCT")(settings=settings)
        with pytest.raises(Exception) as exc_info:
            op.execute_json(
                {
                    "query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }",
                    "endpoint": {"@op": "URI", "args": {"input": "http://127.0.0.1:1/__nope__"}},
                }
            )
        # KeyError would mean the arg keys are wrong; any other exception is a plausible
        # "endpoint unreachable" path consistent with the spec arg shape.
        assert not isinstance(exc_info.value, KeyError)
