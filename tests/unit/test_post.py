"""Spec: formal-semantics.md "POST - Submit RDF data via HTTP POST"
Abstract: URI × Graph → Result
Python:   def execute(self, url: rdflib.URIRef, data: rdflib.Graph) -> Result
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, URIRef

from web_algebra.operation import Operation


class TestPOSTPure:
    def test_wrong_url_type_raises(self, settings):
        op = Operation.get("POST")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("http://example.org/x"), Graph())

    def test_wrong_data_type_raises(self, settings):
        op = Operation.get("POST")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("http://example.org/x"), Literal("not-a-graph"))


@pytest.mark.network
class TestPOSTLive:
    @pytest.mark.skip(reason="No safe public POST endpoint to test against")
    def test_returns_result(self, settings):
        pass


class TestPOSTJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): POST JSON arg shape not exemplified by existing fixtures (presumed `{url, data}`)")
    def test_json_dispatch(self, settings):
        pass
