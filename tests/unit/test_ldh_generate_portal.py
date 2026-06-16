"""Spec: formal-semantics.md "ldh-GeneratePortal - End-to-end portal generation;
composes `ExtractOntology`, `ldh-GenerateOntologyViews`, `POST`, and
`ldh-GenerateClassContainers`"
Abstract: URI × URI × URI → Result
Python:   def execute(self, endpoint: URIRef, ontology_namespace: URIRef, parent_container: URIRef) -> Result
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


ENDPOINT = URIRef("http://example.org/sparql")
ONTOLOGY_NS = URIRef("http://example.org/ontology/")
PARENT = URIRef("http://example.org/portal/")


class TestLDHGeneratePortalPure:
    def test_wrong_endpoint_type_raises(self, settings):
        op = Operation.get("ldh-GeneratePortal")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("not-a-uri"), ONTOLOGY_NS, PARENT)

    def test_wrong_ontology_namespace_type_raises(self, settings):
        op = Operation.get("ldh-GeneratePortal")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(ENDPOINT, Literal("not-a-uri"), PARENT)

    def test_wrong_parent_container_type_raises(self, settings):
        op = Operation.get("ldh-GeneratePortal")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(ENDPOINT, ONTOLOGY_NS, Literal("not-a-uri"))


@pytest.mark.ldh
class TestLDHGeneratePortalLive:
    @pytest.mark.skip(reason="UNCLEAR(spec): return type `Result` shape — what's a meaningful assertion for end-to-end portal generation?")
    def test_basic(self, settings_with_auth):
        pass


class TestLDHGeneratePortalJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): JSON arg keys for ldh-GeneratePortal not given by spec or existing fixtures")
    def test_json_dispatch(self, settings):
        pass
