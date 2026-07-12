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
    def test_wrong_url_type_raises_before_network(self, settings):
        # §4.4 JSON: url: URI · data: Graph or RDF data form.
        # §3.7: strict typing before any effect.
        op = Operation.get("POST")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "url": "http://example.org/x",
                    "data": {"@id": "http://ex/s", "@type": "http://ex/T"},
                }
            )
