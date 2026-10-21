"""Spec: formal-semantics.md Appendix A, `ldh-GeneratePortal`.
JSON:     endpoint: URI · ontology_namespace: URI · parent_container: URI
Python:   def execute(self, endpoint: URIRef, ontology_namespace: URIRef, parent_container: URIRef) -> Result

Writes an sd:Service for `endpoint` at `ontology_namespace#Service`, extracts
the ontology of `endpoint`, POSTs its views (`ldh-GenerateOntologyViews`, with
that service) to `ontology_namespace`, and generates the class containers.
The views carry the properties' rdfs:domain and rdfs:range, which the client
needs to find them. Checked offline: the endpoint answers the extraction with
a small ontology, and the writes are recorded.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from tests.http_stub import StubResponse, default_handler, query_form, request_body_text, request_header, sparql_query_text

from web_algebra.operation import Operation


ENDPOINT = URIRef("http://example.org/sparql")
ONTOLOGY_NS = URIRef("http://example.org/ontology/")
PARENT = URIRef("http://example.org/portal/")
LDH = Namespace("https://w3id.org/atomgraph/linkeddatahub#")
SD = Namespace("http://www.w3.org/ns/sparql-service-description#")
SP = Namespace("http://spinrdf.org/sp#")
EX = Namespace("http://example.org/ns#")
SERVICE = URIRef(f"{ONTOLOGY_NS}#Service")

ONTOLOGY = f"""
@prefix owl: <{OWL}> . @prefix rdfs: <{RDFS}> . @prefix ex: <{EX}> .
ex:Person a owl:Class .
ex:knows a owl:ObjectProperty ; rdfs:domain ex:Person ; rdfs:range ex:Person .
""".encode()


def endpoint_with_ontology(request):
    """The endpoint answers every CONSTRUCT with the ontology; the rest as the default stub."""
    query = sparql_query_text(request)
    if query is not None and query_form(query) == "CONSTRUCT":
        # in the format the client asks for (its Accept), N-Triples
        body = Graph().parse(data=ONTOLOGY, format="turtle").serialize(format="nt").encode()
        return StubResponse(200, {"Content-Type": "application/n-triples"}, body)
    if request.get_method() == "HEAD":
        return StubResponse(404)
    return default_handler(request)


def body_graph(request) -> Graph:
    content_type = (request_header(request, "Content-Type") or "").split(";")[0].strip()
    fmt = {"text/turtle": "turtle", "application/n-triples": "nt", "application/ld+json": "json-ld",
           "application/rdf+xml": "xml"}.get(content_type, "turtle")
    return Graph().parse(data=request_body_text(request), format=fmt, publicID=request.full_url)


def run_portal(settings, http_stub):
    http_stub.handler = endpoint_with_ontology
    result = Operation.get("ldh-GeneratePortal")(settings=settings).execute(ENDPOINT, ONTOLOGY_NS, PARENT)
    writes = [r for r in http_stub.requests if r.get_method() in ("POST", "PUT", "PATCH")
              and r.full_url.split("#")[0] == str(ONTOLOGY_NS) and sparql_query_text(r) is None]
    graph = Graph()
    for r in writes:
        graph += body_graph(r)
    return result, graph


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


class TestLDHGeneratePortalWrites:
    def test_returns_a_result(self, settings, http_stub):
        from rdflib.query import Result

        result, _ = run_portal(settings, http_stub)
        assert isinstance(result, Result)

    def test_the_service_is_written_in_the_namespace(self, settings, http_stub):
        _, written = run_portal(settings, http_stub)
        assert (SERVICE, RDF.type, SD.Service) in written
        assert (SERVICE, SD.endpoint, ENDPOINT) in written

    def test_the_views_are_written_to_the_namespace(self, settings, http_stub):
        _, written = run_portal(settings, http_stub)
        assert list(written.objects(EX.knows, LDH.view))
        assert list(written.objects(EX.knows, LDH.inverseView))

    def test_the_views_carry_domain_and_range(self, settings, http_stub):
        _, written = run_portal(settings, http_stub)
        assert (EX.knows, RDFS.domain, EX.Person) in written
        assert (EX.knows, RDFS.range, EX.Person) in written

    def test_the_view_queries_use_the_service(self, settings, http_stub):
        _, written = run_portal(settings, http_stub)
        queries = set(written.subjects(RDF.type, SP.Select))
        assert queries and all((q, LDH.service, SERVICE) in written for q in queries)


class TestLDHGeneratePortalJson:
    def test_json_dispatch(self, settings, http_stub):
        http_stub.handler = endpoint_with_ontology
        from rdflib.query import Result

        result = Operation.process_json(settings, {"@op": "ldh-GeneratePortal", "args": {
            "endpoint": {"@id": str(ENDPOINT)},
            "ontology_namespace": {"@id": str(ONTOLOGY_NS)},
            "parent_container": {"@id": str(PARENT)},
        }})
        assert isinstance(result, Result)
        assert any(r.full_url.split("#")[0] == str(ONTOLOGY_NS) and r.get_method() == "POST" for r in http_stub.requests)
