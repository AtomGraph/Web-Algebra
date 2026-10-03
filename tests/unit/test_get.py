"""Spec: formal-semantics.md "GET - Retrieve RDF data via HTTP GET"
Abstract: URI → Graph
Python:   def execute(self, url: rdflib.URIRef) -> Graph
"""

from __future__ import annotations

import os
import urllib.error

import pytest
from rdflib import Graph, Literal, URIRef

from tests.http_stub import StubResponse
from web_algebra.operation import Operation


class TestGETPure:
    def test_wrong_url_type_raises(self, settings):
        op = Operation.get("GET")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("http://example.org/x"))


@pytest.mark.network
class TestGETLive:
    def test_returns_graph(self, settings):
        url = os.getenv("HTTP_GET_URL")
        if not url:
            pytest.skip("HTTP_GET_URL env var not set")
        op = Operation.get("GET")(settings=settings)
        result = op.execute(URIRef(url))
        assert isinstance(result, Graph)


class TestGETJson:
    def test_wrong_url_type_raises_before_network(self, settings):
        # §4.4 JSON: url: URI. §3.7: strict typing before any effect —
        # a plain string coerces to a string Literal, not a URI.
        op = Operation.get("GET")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json({"url": "http://example.org/x"})


class TestGETStubbed:
    def test_returns_graph(self, settings, http_stub):
        http_stub.handler = lambda request: StubResponse(
            200,
            {"Content-Type": "text/turtle"},
            b"<http://example.org/s> <http://example.org/p> <http://example.org/o> .",
        )
        op = Operation.get("GET")(settings=settings)
        result = op.execute(URIRef("http://example.org/doc"))
        assert isinstance(result, Graph)
        assert len(result) == 1
        assert http_stub.methods() == ["GET"]

    @pytest.mark.parametrize("status", [404, 500])
    def test_read_answered_non_2xx_propagates_http_error(
        self, settings, http_stub, status
    ):
        # §3.7: a read (GET) answered outside 2xx → urllib HTTPError,
        # unwrapped — unlike a write, which raises ValueError (§4.4)
        http_stub.handler = lambda request: StubResponse(status)
        op = Operation.get("GET")(settings=settings)
        with pytest.raises(urllib.error.HTTPError):
            op.execute(URIRef("http://example.org/doc"))
