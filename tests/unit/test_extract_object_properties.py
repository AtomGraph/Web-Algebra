"""Spec: formal-semantics.md "ExtractObjectProperties - Extract object properties from graph"
Abstract: URI → Graph
Python:   def execute(self, endpoint: URIRef) -> rdflib.Graph
"""

from __future__ import annotations

import pytest
from rdflib import Literal

from web_algebra.operation import Operation


class TestExtractObjectPropertiesPure:
    def test_wrong_input_type_raises(self, settings):
        op = Operation.get("ExtractObjectProperties")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("not-a-uri"))

    # §4.6: the URI names a SPARQL endpoint; the happy path queries it and
    # is covered under the `sparql` marker via the live suite.


class TestExtractObjectPropertiesJson:
    def test_wrong_endpoint_type_raises_before_network(self, settings):
        # §4.6 JSON: endpoint: URI. §3.7: strict typing before any effect.
        op = Operation.get("ExtractObjectProperties")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json({"endpoint": "http://example.org/sparql"})
