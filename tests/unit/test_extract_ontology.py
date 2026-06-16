"""Spec: formal-semantics.md "ExtractOntology - Extract a full ontology (classes
+ datatype + object properties) from a SPARQL endpoint as a single graph"
Abstract: URI → Graph
Python:   def execute(self, endpoint: URIRef) -> rdflib.Graph
"""

from __future__ import annotations

import pytest
from rdflib import Literal

from web_algebra.operation import Operation


class TestExtractOntologyPure:
    def test_wrong_input_type_raises(self, settings):
        op = Operation.get("ExtractOntology")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("not-a-uri"))

    @pytest.mark.skip(reason="UNCLEAR(spec): is the URI a SPARQL endpoint, document URL, or ontology IRI? — narrative omits this")
    def test_happy_path(self, settings):
        pass


class TestExtractOntologyJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): JSON arg key for ExtractOntology not given by spec or existing fixtures")
    def test_json_dispatch(self, settings):
        pass
