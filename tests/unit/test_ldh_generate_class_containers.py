"""Spec: formal-semantics.md "ldh-GenerateClassContainers - Create an LDH
container per `owl:Class` in an ontology graph (each with a SPARQL service and
instance-list view)"
Abstract: Graph × URI × URI → Result
Python:   def execute(self, ontology: rdflib.Graph, parent_container: URIRef, endpoint: URIRef) -> Result
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, URIRef

from web_algebra.operation import Operation


PARENT = URIRef("http://example.org/portal/")
ENDPOINT = URIRef("http://example.org/sparql")


class TestLDHGenerateClassContainersPure:
    def test_wrong_ontology_type_raises(self, settings):
        op = Operation.get("ldh-GenerateClassContainers")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("not-a-graph"), PARENT, ENDPOINT)

    def test_wrong_parent_container_type_raises(self, settings):
        op = Operation.get("ldh-GenerateClassContainers")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Graph(), Literal("not-a-uri"), ENDPOINT)

    def test_wrong_endpoint_type_raises(self, settings):
        op = Operation.get("ldh-GenerateClassContainers")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Graph(), PARENT, Literal("not-a-uri"))


@pytest.mark.ldh
class TestLDHGenerateClassContainersLive:
    @pytest.mark.skip(reason="UNCLEAR(spec): return type `Result` shape — what's a meaningful assertion for a side-effecting orchestration?")
    def test_basic(self, settings_with_auth):
        pass


class TestLDHGenerateClassContainersJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): JSON arg keys for ldh-GenerateClassContainers not given by spec or existing fixtures")
    def test_json_dispatch(self, settings):
        pass
