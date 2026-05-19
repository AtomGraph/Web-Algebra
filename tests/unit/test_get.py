"""Spec: formal-semantics.md "GET - Retrieve RDF data via HTTP GET"
Abstract: URI → Graph
Python:   def execute(self, url: rdflib.URIRef) -> Graph
"""

from __future__ import annotations

import os

import pytest
from rdflib import Graph, Literal, URIRef

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
    @pytest.mark.skip(reason="UNCLEAR(spec): GET JSON arg shape not exemplified by existing fixtures (presumed `{url}`)")
    def test_json_dispatch(self, settings):
        pass
