"""Spec: formal-semantics.md "ExtractClasses - Extract RDF classes from graph"
Abstract: URI → Graph
Python:   def execute(self, endpoint: URIRef) -> rdflib.Graph
"""

from __future__ import annotations

import pytest
from rdflib import Literal

from web_algebra.operation import Operation


class TestExtractClassesPure:
    def test_wrong_input_type_raises(self, settings):
        op = Operation.get("ExtractClasses")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("not-a-uri"))

    @pytest.mark.skip(reason="UNCLEAR(spec): is the URI a SPARQL endpoint, document URL, or ontology IRI? — narrative omits this")
    def test_happy_path(self, settings):
        pass


class TestExtractClassesJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): JSON arg key for ExtractClasses not given by spec or existing fixtures")
    def test_json_dispatch(self, settings):
        pass
