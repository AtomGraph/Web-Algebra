"""Spec: formal-semantics.md "PUT - Replace RDF data via HTTP PUT"
Abstract: URI × Graph → Result
Python:   def execute(self, url: rdflib.URIRef, data: rdflib.Graph) -> Result
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, URIRef

from web_algebra.operation import Operation


class TestPUTPure:
    def test_wrong_url_type_raises(self, settings):
        op = Operation.get("PUT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("http://example.org/x"), Graph())

    def test_wrong_data_type_raises(self, settings):
        op = Operation.get("PUT")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("http://example.org/x"), Literal("not-a-graph"))


@pytest.mark.network
class TestPUTLive:
    @pytest.mark.skip(reason="No safe public PUT endpoint; covered by integration LDH fixture instead")
    def test_returns_result(self, settings):
        pass


class TestPUTJson:
    def test_json_dispatch_arg_shape(self, settings):
        # JSON arg keys from existing fixture tests/fixtures/positive/linkeddatahub-put-test.json:
        # PUT takes {"url": <URI>, "data": <Graph-producing op>}.
        op = Operation.get("PUT")(settings=settings)
        # Exercise that the arg shape is recognized — execute_json processes args
        # before any HTTP call. We pass a malformed nested op so the call surfaces
        # the type/shape failure inside the dispatcher rather than KeyError.
        with pytest.raises(Exception) as exc_info:
            op.execute_json(
                {
                    "url": {"@op": "URI", "args": {"input": "http://127.0.0.1:1/__nope__"}},
                    "data": {"@op": "URI", "args": {"input": "http://example.org/not-a-graph"}},
                }
            )
        # KeyError on missing keys would mean the spec arg shape is wrong.
        assert not isinstance(exc_info.value, KeyError)
