"""Spec: formal-semantics.md Appendix A - the options the ldh-* operations share
with LinkedDataHub's CLI, written as the CLI writes them:

- ldh-CreateContainer's first content block, rdf:_1: an ldh:Object of
  ldh:ChildrenView, unless `children_view` is false, when there is none.
- `primary_topic` (CreateContainer, CreateItem): a URI reference resolved
  against the document's URI, the document's one foaf:primaryTopic.
- ldh-CreateItem's `description`: dct:description.
- ldh-AddObjectBlock's `graph`: the block's ldh:graph.
- ldh-AddResultSetChart's `series_var_name`: a name or a sequence of names,
  one ldh:seriesVarName each.
- ldh-AddView's `show_when_empty` (xsd:boolean): ldh:showWhenEmpty.

Checked offline: every write is recorded and its body read as RDF.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, RDF, XSD

from tests.http_stub import request_body_text, request_header
from web_algebra.operation import Operation

LDH = Namespace("https://w3id.org/atomgraph/linkeddatahub#")
EX = "https://example.org/"
DOC = EX + "doc/"
QUERY = DOC + "#q"
SEQ_1 = RDF["_1"]


def written(settings, http_stub, op, **args) -> Graph:
    """The graph `op` writes, read from the recorded request bodies."""
    Operation.process_json(settings, {"@op": op, "args": args})
    g = Graph()
    for r in http_stub.requests:
        if r.get_method() not in ("POST", "PUT"):
            continue
        content_type = (request_header(r, "Content-Type") or "").split(";")[0].strip()
        fmt = {"application/n-triples": "nt", "text/turtle": "turtle", "application/ld+json": "json-ld"}.get(content_type, "nt")
        g.parse(data=request_body_text(r), format=fmt, publicID=r.full_url)
    return g


def container(settings, http_stub, **args) -> tuple[Graph, URIRef]:
    g = written(settings, http_stub, "ldh-CreateContainer", parent={"@id": EX}, title="C", slug="c", **args)
    return g, URIRef(EX + "c/")


def item(settings, http_stub, **args) -> tuple[Graph, URIRef]:
    g = written(settings, http_stub, "ldh-CreateItem", container={"@id": EX}, title="I", slug="i", **args)
    return g, URIRef(EX + "i/")


# --- ldh-CreateContainer: the first content block


def test_a_container_shows_its_children_by_default(settings, http_stub):
    g, doc = container(settings, http_stub)
    (block,) = g.objects(doc, SEQ_1)
    assert (block, RDF.type, LDH.Object) in g
    assert (block, RDF.value, LDH.ChildrenView) in g


def test_a_container_shows_its_children_when_asked(settings, http_stub):
    g, doc = container(settings, http_stub, children_view=True)
    (block,) = g.objects(doc, SEQ_1)
    assert (block, RDF.value, LDH.ChildrenView) in g


def test_a_container_without_the_children_view_has_no_content(settings, http_stub):
    g, doc = container(settings, http_stub, children_view=False)
    assert list(g.objects(doc, SEQ_1)) == []
    assert (None, RDF.value, LDH.ChildrenView) not in g


# --- primary_topic


@pytest.mark.parametrize("make", [container, item])
@pytest.mark.parametrize(
    "reference, resolved",
    [("#this", "{doc}#this"), ("https://example.org/topic", "https://example.org/topic"), ("../topic#it", EX + "topic#it")],
)
def test_the_primary_topic_is_resolved_against_the_document(settings, http_stub, make, reference, resolved):
    g, doc = make(settings, http_stub, primary_topic=reference)
    assert list(g.objects(doc, FOAF.primaryTopic)) == [URIRef(resolved.format(doc=doc))]


@pytest.mark.parametrize("make", [container, item])
def test_no_primary_topic_unless_given(settings, http_stub, make):
    g, doc = make(settings, http_stub)
    assert list(g.objects(doc, FOAF.primaryTopic)) == []


# --- ldh-CreateItem: description


def test_an_item_has_its_description(settings, http_stub):
    g, doc = item(settings, http_stub, description="About the item")
    assert list(g.objects(doc, DCTERMS.description)) == [Literal("About the item")]


def test_an_item_has_no_description_unless_given(settings, http_stub):
    g, doc = item(settings, http_stub)
    assert list(g.objects(doc, DCTERMS.description)) == []


# --- ldh-AddObjectBlock: graph


def test_an_object_block_reads_its_value_from_the_graph(settings, http_stub):
    g = written(settings, http_stub, "ldh-AddObjectBlock", url={"@id": DOC}, value={"@id": EX + "thing"},
                fragment="ob", graph={"@id": EX + "things/thing/"})
    assert list(g.objects(URIRef(DOC + "#ob"), LDH.graph)) == [URIRef(EX + "things/thing/")]


def test_an_object_block_has_no_graph_unless_given(settings, http_stub):
    g = written(settings, http_stub, "ldh-AddObjectBlock", url={"@id": DOC}, value={"@id": EX + "thing"}, fragment="ob")
    assert list(g.objects(URIRef(DOC + "#ob"), LDH.graph)) == []


# --- ldh-AddResultSetChart: several series


def chart(settings, http_stub, series) -> Graph:
    return written(settings, http_stub, "ldh-AddResultSetChart", url={"@id": DOC}, query={"@id": QUERY}, title="Ch",
                   chart_type={"@id": "https://w3id.org/atomgraph/client#BarChart"}, category_var_name="year",
                   series_var_name=series, fragment="ch")


def test_one_series(settings, http_stub):
    g = chart(settings, http_stub, "sales")
    assert set(g.objects(URIRef(DOC + "#ch"), LDH.seriesVarName)) == {Literal("sales")}


def test_several_series(settings, http_stub):
    g = chart(settings, http_stub, ["sales", "returns", "profit"])
    assert set(g.objects(URIRef(DOC + "#ch"), LDH.seriesVarName)) == {Literal("sales"), Literal("returns"), Literal("profit")}


# --- ldh-AddView: show_when_empty


def view(settings, http_stub, **args) -> Graph:
    return written(settings, http_stub, "ldh-AddView", url={"@id": DOC}, query={"@id": QUERY}, title="V", fragment="v", **args)


@pytest.mark.parametrize("value", [False, True])
def test_show_when_empty(settings, http_stub, value):
    g = view(settings, http_stub, show_when_empty=value)
    assert list(g.objects(URIRef(DOC + "#v"), LDH.showWhenEmpty)) == [Literal(value, datatype=XSD.boolean)]


def test_no_show_when_empty_unless_given(settings, http_stub):
    g = view(settings, http_stub)
    assert list(g.objects(URIRef(DOC + "#v"), LDH.showWhenEmpty)) == []


def test_show_when_empty_is_a_boolean(settings, http_stub):
    with pytest.raises(TypeError):
        view(settings, http_stub, show_when_empty="sometimes")


# --- the schema names the options


@pytest.mark.parametrize(
    "op, options",
    [
        ("ldh-CreateContainer", {"children_view", "primary_topic"}),
        ("ldh-CreateItem", {"description", "primary_topic"}),
        ("ldh-AddObjectBlock", {"graph"}),
        ("ldh-AddView", {"show_when_empty"}),
    ],
)
def test_the_schema_has_the_options(op, options):
    schema = Operation.get(op).inputSchema()
    assert options <= set(schema["properties"])
    assert not options & set(schema.get("required", []))
