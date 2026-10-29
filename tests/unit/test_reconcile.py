"""Spec: formal-semantics.md §4.7 "Reconcile"
Abstract: URI × Literal × Maybe Literal × Maybe Literal → Result
Python:   def execute(self, endpoint, query, type=None, limit=None) -> Result
"""

from __future__ import annotations

import json
import urllib.parse

import pytest
from rdflib import Literal, URIRef
from rdflib.namespace import XSD

from tests.http_stub import StubResponse, request_body_text
from web_algebra.operation import Operation

ENDPOINT = URIRef("https://reconcile.example.org/en/api")
MANIFEST = {"name": "Test", "identifierSpace": "http://www.wikidata.org/entity/", "schemaSpace": "http://www.wikidata.org/prop/direct/"}
CANDIDATES = {"q0": {"result": [
    {"id": "Q25319", "name": "Aarhus", "description": "city in Denmark", "score": 100, "match": True},
    {"id": "Q1748", "name": "Copenhagen", "score": 42.5, "match": False},
]}}


def service(http_stub, manifest=MANIFEST, answer=CANDIDATES, status=200):
    def handler(request):
        body = manifest if request.get_method() == "GET" else answer
        return StubResponse(status, {"Content-Type": "application/json"}, json.dumps(body).encode())
    http_stub.handler = handler


def queries(http_stub) -> dict:
    post = [r for r in http_stub.requests if r.get_method() == "POST"][0]
    return json.loads(urllib.parse.parse_qs(request_body_text(post))["queries"][0])


class TestReconcile:
    def test_the_candidates_are_rows_with_their_ids_resolved_against_the_identifier_space(self, settings, http_stub):
        service(http_stub)
        result = Operation.get("Reconcile")(settings=settings).execute(ENDPOINT, Literal("Aarhus"))

        assert list(result.vars) == ["entity", "name", "description", "score", "match"]
        first, second = result.bindings
        assert first["entity"] == URIRef("http://www.wikidata.org/entity/Q25319")
        assert first["name"] == Literal("Aarhus")
        assert first["description"] == Literal("city in Denmark")
        assert first["score"] == Literal("100", datatype=XSD.decimal)
        assert first["match"] == Literal(True)
        assert second["entity"] == URIRef("http://www.wikidata.org/entity/Q1748")
        assert "description" not in second, "a candidate without a description binds none"
        assert second["score"] == Literal("42.5", datatype=XSD.decimal)
        assert second["match"] == Literal(False)

    def test_the_type_and_limit_go_with_the_query(self, settings, http_stub):
        service(http_stub)
        Operation.get("Reconcile")(settings=settings).execute(
            ENDPOINT, Literal("Aarhus"), Literal("Q515"), Literal(3, datatype=XSD.integer)
        )
        assert queries(http_stub) == {"q0": {"query": "Aarhus", "type": "Q515", "limit": 3}}

    def test_json_arguments(self, settings, http_stub):
        service(http_stub)
        result = Operation.get("Reconcile")(settings=settings).execute_json(
            {"endpoint": {"@op": "URI", "args": {"input": str(ENDPOINT)}}, "query": "Aarhus", "type": "Q515", "limit": 1}
        )
        assert result.bindings[0]["entity"] == URIRef("http://www.wikidata.org/entity/Q25319")
        assert queries(http_stub)["q0"]["limit"] == 1

    def test_a_name_nothing_reconciles_to_is_an_empty_result(self, settings, http_stub):
        service(http_stub, answer={"q0": {"result": []}})
        result = Operation.get("Reconcile")(settings=settings).execute(ENDPOINT, Literal("Xyzzy"))
        assert list(result.bindings) == []

    def test_a_service_without_an_identifier_space_is_an_error(self, settings, http_stub):
        service(http_stub, manifest={"name": "Test"})
        with pytest.raises(ValueError, match="identifierSpace"):
            Operation.get("Reconcile")(settings=settings).execute(ENDPOINT, Literal("Aarhus"))

    def test_the_endpoint_is_a_uri(self, settings):
        with pytest.raises(TypeError):
            Operation.get("Reconcile")(settings=settings).execute(Literal(str(ENDPOINT)), Literal("Aarhus"))

    def test_it_reads(self):
        assert Operation.get("Reconcile").kind.value == "read"
