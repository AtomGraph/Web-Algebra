"""Spec: formal-semantics.md "ldh-GenerateOntologyViews - Generate LDH views
(`ldh:view`) and SPIN `sp:Select` queries for each non-`owl:FunctionalProperty`
`owl:DatatypeProperty`/`owl:ObjectProperty` in an ontology graph"
Abstract: Graph × URI × URI → Graph
Python:   def execute(self, ontology: rdflib.Graph, base_uri: URIRef, service_uri: URIRef) -> rdflib.Graph
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF

from web_algebra.operation import Operation


LDH = Namespace("https://w3id.org/atomgraph/linkeddatahub#")
EX = Namespace("http://example.org/ns#")
BASE = URIRef("http://example.org/portal/")
SERVICE = URIRef("http://example.org/portal/#Service")


class TestLDHGenerateOntologyViewsPure:
    def test_wrong_ontology_type_raises(self, settings):
        op = Operation.get("ldh-GenerateOntologyViews")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("not-a-graph"), BASE, SERVICE)

    def test_wrong_base_uri_type_raises(self, settings):
        op = Operation.get("ldh-GenerateOntologyViews")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Graph(), Literal("not-a-uri"), SERVICE)

    def test_wrong_service_uri_type_raises(self, settings):
        op = Operation.get("ldh-GenerateOntologyViews")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Graph(), BASE, Literal("not-a-uri"))

    def test_emits_ldh_view_for_non_functional_property(self, settings):
        """Spec: emits a view per non-`owl:FunctionalProperty` object/datatype property."""
        ontology = Graph()
        ontology.add((EX.knows, RDF.type, OWL.ObjectProperty))

        op = Operation.get("ldh-GenerateOntologyViews")(settings=settings)
        out = op.execute(ontology, BASE, SERVICE)

        assert isinstance(out, Graph)
        views = list(out.triples((EX.knows, LDH.view, None)))
        assert len(views) == 1, f"expected one ldh:view triple for ex:knows, got {len(views)}"

    def test_skips_functional_property(self, settings):
        """Spec: properties declared `owl:FunctionalProperty` are excluded."""
        ontology = Graph()
        ontology.add((EX.ssn, RDF.type, OWL.DatatypeProperty))
        ontology.add((EX.ssn, RDF.type, OWL.FunctionalProperty))

        op = Operation.get("ldh-GenerateOntologyViews")(settings=settings)
        out = op.execute(ontology, BASE, SERVICE)

        views = list(out.triples((EX.ssn, LDH.view, None)))
        assert len(views) == 0, "functional property must not get a view"

    def test_no_ldh_template_in_output(self, settings):
        """Spec phrases the output predicate as `ldh:view` — `ldh:template` (the
        previous LDH vocabulary, since removed) must not appear."""
        ontology = Graph()
        ontology.add((EX.knows, RDF.type, OWL.ObjectProperty))
        ontology.add((EX.name, RDF.type, OWL.DatatypeProperty))

        op = Operation.get("ldh-GenerateOntologyViews")(settings=settings)
        out = op.execute(ontology, BASE, SERVICE)

        legacy = list(out.triples((None, LDH.template, None)))
        assert legacy == [], "output must contain no `ldh:template` triples"


class TestLDHGenerateOntologyViewsJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): JSON arg keys for ldh-GenerateOntologyViews not given by spec or existing fixtures")
    def test_json_dispatch(self, settings):
        pass
