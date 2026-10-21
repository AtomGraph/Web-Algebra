"""Spec: formal-semantics.md Appendix A, `ldh-GenerateOntologyViews`.
JSON:     ontology: Graph · base_uri: URI · service_uri: URI
Python:   def execute(self, ontology: rdflib.Graph, base_uri: URIRef, service_uri: URIRef) -> rdflib.Graph

The views of the object properties of `ontology`, as LinkedDataHub's client
looks them up: for an `owl:ObjectProperty` p with local name n,
- with an rdfs:domain and not functional: `p ldh:view B#n_View`, an ldh:View
  (dct:title n, ac:mode ac:TableMode) with spin:query `B#n_Query`, an
  sp:Select (dct:title "Select n", ldh:service S) whose text is
  `SELECT DISTINCT ?related WHERE { GRAPH ?g { $about <p> ?related } }`;
- with an rdfs:range and not inverse-functional: `p ldh:inverseView
  B#n_InverseView` (dct:title "n (inverse)"), query `B#n_InverseQuery`
  (dct:title "Select n (inverse)") with `?related <p> $about`;
- every view hidden while its query matches nothing (ldh:showWhenEmpty false);
- the rdfs:domain and rdfs:range triples of every p given a view;
- no view for a property with neither; a shared local name is suffixed `_`
  and the first 6 hex digits of the SHA-1 of the property's URI.
"""

from __future__ import annotations

import hashlib

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS
from rdflib.plugins.sparql import prepareQuery

from web_algebra.operation import Operation

LDH = Namespace("https://w3id.org/atomgraph/linkeddatahub#")
AC = Namespace("https://w3id.org/atomgraph/client#")
SP = Namespace("http://spinrdf.org/sp#")
SPIN = Namespace("http://spinrdf.org/spin#")
EX = Namespace("http://example.org/ns#")
OTHER = Namespace("http://example.org/other#")
BASE = URIRef("http://example.org/portal/")
SERVICE = URIRef("http://example.org/portal/#Service")


def node(name: str) -> URIRef:
    return URIRef(f"{BASE}#{name}")


def generate(settings, *triples) -> Graph:
    ontology = Graph()
    for t in triples:
        ontology.add(t)
    return Operation.get("ldh-GenerateOntologyViews")(settings=settings).execute(ontology, BASE, SERVICE)


def evaluate(query_text: str, data: Graph, about: URIRef) -> set:
    """What the client's view shows: the query with $about bound to the resource."""
    return {str(row[0]) for row in data.query(prepareQuery(query_text), initBindings={"about": about})}


KNOWS = (
    (EX.knows, RDF.type, OWL.ObjectProperty),
    (EX.knows, RDFS.domain, EX.Person),
    (EX.knows, RDFS.range, EX.Person),
)


class TestTypes:
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

    def test_returns_a_graph(self, settings):
        assert isinstance(generate(settings, *KNOWS), Graph)


class TestForwardView:
    def test_the_property_has_its_view(self, settings):
        out = generate(settings, *KNOWS)
        assert set(out.objects(EX.knows, LDH.view)) == {node("knows_View")}

    def test_the_view(self, settings):
        out = generate(settings, *KNOWS)
        view = node("knows_View")
        assert (view, RDF.type, LDH.View) in out
        assert (view, DCTERMS.title, Literal("knows")) in out
        assert (view, AC.mode, AC.TableMode) in out
        assert (view, SPIN.query, node("knows_Query")) in out
        assert list(out.objects(view, LDH.showWhenEmpty)) == [Literal(False)]

    def test_the_query(self, settings):
        out = generate(settings, *KNOWS)
        query = node("knows_Query")
        assert (query, RDF.type, SP.Select) in out
        assert (query, DCTERMS.title, Literal("Select knows")) in out
        assert (query, LDH.service, SERVICE) in out
        texts = [str(t) for t in out.objects(query, SP.text)]
        assert texts == [f"SELECT DISTINCT ?related WHERE {{ GRAPH ?g {{ $about <{EX.knows}> ?related }} }}"]

    def test_the_query_selects_what_the_resource_points_to(self, settings):
        out = generate(settings, *KNOWS)
        text = str(next(out.objects(node("knows_Query"), SP.text)))
        from rdflib import Dataset

        data = Dataset()
        doc = data.graph(URIRef("http://example.org/doc/alice/"))
        doc.add((EX.alice, EX.knows, EX.bob))
        doc.add((EX.carol, EX.knows, EX.alice))
        assert evaluate(text, data, EX.alice) == {str(EX.bob)}

    def test_no_view_without_a_domain(self, settings):
        out = generate(settings, (EX.p, RDF.type, OWL.ObjectProperty), (EX.p, RDFS.range, EX.Thing))
        assert list(out.objects(EX.p, LDH.view)) == []

    def test_no_view_for_a_functional_property(self, settings):
        out = generate(settings, *KNOWS, (EX.knows, RDF.type, OWL.FunctionalProperty))
        assert list(out.objects(EX.knows, LDH.view)) == []


class TestInverseView:
    def test_the_property_has_its_inverse_view(self, settings):
        out = generate(settings, *KNOWS)
        assert set(out.objects(EX.knows, LDH.inverseView)) == {node("knows_InverseView")}

    def test_the_inverse_view(self, settings):
        out = generate(settings, *KNOWS)
        view = node("knows_InverseView")
        assert (view, RDF.type, LDH.View) in out
        assert (view, DCTERMS.title, Literal("knows (inverse)")) in out
        assert (view, AC.mode, AC.TableMode) in out
        assert (view, SPIN.query, node("knows_InverseQuery")) in out
        assert list(out.objects(view, LDH.showWhenEmpty)) == [Literal(False)]

    def test_the_inverse_query(self, settings):
        out = generate(settings, *KNOWS)
        query = node("knows_InverseQuery")
        assert (query, RDF.type, SP.Select) in out
        assert (query, DCTERMS.title, Literal("Select knows (inverse)")) in out
        assert (query, LDH.service, SERVICE) in out
        texts = [str(t) for t in out.objects(query, SP.text)]
        assert texts == [f"SELECT DISTINCT ?related WHERE {{ GRAPH ?g {{ ?related <{EX.knows}> $about }} }}"]

    def test_the_inverse_query_selects_what_points_to_the_resource(self, settings):
        out = generate(settings, *KNOWS)
        text = str(next(out.objects(node("knows_InverseQuery"), SP.text)))
        from rdflib import Dataset

        data = Dataset()
        doc = data.graph(URIRef("http://example.org/doc/carol/"))
        doc.add((EX.alice, EX.knows, EX.bob))
        doc.add((EX.carol, EX.knows, EX.alice))
        assert evaluate(text, data, EX.alice) == {str(EX.carol)}

    def test_no_inverse_view_without_a_range(self, settings):
        out = generate(settings, (EX.p, RDF.type, OWL.ObjectProperty), (EX.p, RDFS.domain, EX.Thing))
        assert list(out.objects(EX.p, LDH.inverseView)) == []
        assert list(out.objects(EX.p, LDH.view)) == [node("p_View")]

    def test_no_inverse_view_for_an_inverse_functional_property(self, settings):
        out = generate(settings, *KNOWS, (EX.knows, RDF.type, OWL.InverseFunctionalProperty))
        assert list(out.objects(EX.knows, LDH.inverseView)) == []
        assert list(out.objects(EX.knows, LDH.view)) == [node("knows_View")]

    def test_a_functional_property_keeps_its_inverse_view(self, settings):
        out = generate(settings, *KNOWS, (EX.knows, RDF.type, OWL.FunctionalProperty))
        assert list(out.objects(EX.knows, LDH.inverseView)) == [node("knows_InverseView")]


class TestDomainAndRange:
    def test_domain_and_range_are_carried(self, settings):
        out = generate(settings, *KNOWS)
        assert (EX.knows, RDFS.domain, EX.Person) in out
        assert (EX.knows, RDFS.range, EX.Person) in out

    def test_every_domain_and_range(self, settings):
        out = generate(settings, *KNOWS, (EX.knows, RDFS.domain, EX.Agent), (EX.knows, RDFS.range, EX.Agent))
        assert set(out.objects(EX.knows, RDFS.domain)) == {EX.Person, EX.Agent}
        assert set(out.objects(EX.knows, RDFS.range)) == {EX.Person, EX.Agent}

    def test_the_range_of_a_property_with_only_an_inverse_view(self, settings):
        out = generate(settings, *KNOWS, (EX.knows, RDF.type, OWL.FunctionalProperty))
        assert (EX.knows, RDFS.domain, EX.Person) in out
        assert (EX.knows, RDFS.range, EX.Person) in out

    def test_nothing_for_a_property_without_a_view(self, settings):
        out = generate(settings, (EX.p, RDF.type, OWL.ObjectProperty))
        assert len(out) == 0

    def test_datatype_properties_get_no_view(self, settings):
        out = generate(settings, (EX.name, RDF.type, OWL.DatatypeProperty), (EX.name, RDFS.domain, EX.Person))
        assert list(out.objects(EX.name, LDH.view)) == []
        assert (EX.name, RDFS.domain, EX.Person) not in out


class TestNames:
    def test_a_shared_local_name_is_suffixed(self, settings):
        out = generate(
            settings,
            *KNOWS,
            (OTHER.knows, RDF.type, OWL.ObjectProperty),
            (OTHER.knows, RDFS.domain, EX.Person),
        )
        views = set(out.objects(EX.knows, LDH.view)) | set(out.objects(OTHER.knows, LDH.view))
        suffixed = {
            node(f"knows_{hashlib.sha1(str(p).encode()).hexdigest()[:6]}_View") for p in (EX.knows, OTHER.knows)
        }
        assert node("knows_View") in views
        assert len(views) == 2 and len(views & suffixed) == 1

    def test_no_ldh_template_in_output(self, settings):
        """`ldh:template`, the vocabulary before `ldh:view`, must not appear."""
        out = generate(settings, *KNOWS)
        assert list(out.triples((None, LDH.template, None))) == []


class TestJson:
    def test_json_dispatch(self, settings):
        ontology = {
            "@context": {"rdfs": str(RDFS), "owl": str(OWL)},
            "@id": str(EX.knows),
            "@type": "owl:ObjectProperty",
            "rdfs:domain": {"@id": str(EX.Person)},
            "rdfs:range": {"@id": str(EX.Person)},
        }
        out = Operation.process_json(
            settings,
            {
                "@op": "ldh-GenerateOntologyViews",
                "args": {"ontology": ontology, "base_uri": {"@id": str(BASE)}, "service_uri": {"@id": str(SERVICE)}},
            },
        )
        assert isinstance(out, Graph)
        assert set(out.objects(EX.knows, LDH.view)) == {node("knows_View")}
        assert set(out.objects(EX.knows, LDH.inverseView)) == {node("knows_InverseView")}


class TestEffect:
    """Appendix A: `ldh-GenerateOntologyViews` *(pure)* - it builds the graph and
    sends no request."""

    def test_no_request(self, settings, http_stub):
        generate(settings, *KNOWS)
        assert http_stub.requests == []

    def test_its_kind_is_read(self, settings):
        from web_algebra.operation import OperationKind

        assert Operation.get("ldh-GenerateOntologyViews").kind == OperationKind.READ
