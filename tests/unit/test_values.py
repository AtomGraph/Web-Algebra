"""Spec: formal-semantics.md §4.3 "Binding restriction" and "Values".

Values restricts the variables of a query or update to the rows of a Result:
the set-valued Substitute. Columns default to the result's variables; `vars`
selects and orders them; a row that does not bind a column has UNDEF there;
a blank node raises ValueError; only columns that occur in the query are
restricted, and if none does the query is unchanged.

Checked by what the restricted query answers over a small graph.
"""

from __future__ import annotations

import pytest
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS
from rdflib.plugins.sparql import prepareQuery

from web_algebra.operation import Operation

EX = "http://example.org/"
A, B, C = (URIRef(EX + x) for x in "ABC")
CITY, MAYOR = URIRef(EX + "City"), URIRef(EX + "mayor")
P = f"PREFIX ex: <{EX}> PREFIX rdfs: <{RDFS}> "


@pytest.fixture
def graph():
    g = Graph()
    for city, label in ((A, "A"), (B, "B"), (C, "C")):
        g.add((city, RDF.type, CITY))
        g.add((city, RDFS.label, Literal(label)))
    g.add((A, MAYOR, URIRef(EX + "M")))
    return g


def data(query, graph=None):
    """A Result to restrict with, from a query over its own small graph."""
    g = graph if graph is not None else Graph()
    return g.query(query)


def values(settings, query, result, vars=None):
    out = Operation.get("Values")(settings=settings).execute(Literal(query), result, vars)
    assert isinstance(out, Literal)
    return str(out)


def rows(query, graph):
    return sorted(tuple(str(v) if v is not None else None for v in row) for row in graph.query(prepareQuery(query)))


def cities(*items):
    g = Graph()
    for i, city in enumerate(items):
        g.add((city, RDFS.label, Literal(f"x{i}")))
    return g


def test_the_query_is_restricted_to_the_rows(settings, graph):
    d = data("SELECT ?city WHERE { ?city ?p ?o }", cities(A, C))
    q = values(settings, P + "SELECT ?city ?label WHERE { ?city rdfs:label ?label }", d)
    assert rows(q, graph) == [(str(A), "A"), (str(C), "C")]


def test_several_columns_restrict_together(settings, graph):
    g = Graph()
    g.add((A, RDFS.label, Literal("A")))
    g.add((B, RDFS.label, Literal("nope")))
    d = data("SELECT ?city ?label WHERE { ?city ?p ?label }", g)
    q = values(settings, P + "SELECT ?city ?label WHERE { ?city rdfs:label ?label }", d)
    assert rows(q, graph) == [(str(A), "A")]


def test_a_row_that_does_not_bind_a_column_is_undef_there(settings, graph):
    g = Graph()
    g.add((A, URIRef(EX + "p"), Literal(1)))
    g.add((B, URIRef(EX + "p"), Literal(2)))
    g.add((A, URIRef(EX + "q"), Literal("A")))
    d = data(f"SELECT ?city ?label WHERE {{ ?city <{EX}p> ?o OPTIONAL {{ ?city <{EX}q> ?label }} }}", g)
    q = values(settings, P + "SELECT ?city ?label WHERE { ?city rdfs:label ?label }", d)
    # row A binds both; row B binds only ?city, so any label of B matches
    assert rows(q, graph) == [(str(A), "A"), (str(B), "B")]


def test_vars_selects_the_columns(settings, graph):
    g = Graph()
    g.add((A, RDFS.label, Literal("ignored")))
    d = data("SELECT ?city ?label WHERE { ?city ?p ?label }", g)
    q = values(settings, P + "SELECT ?city ?label WHERE { ?city rdfs:label ?label }", d, ["city"])
    assert rows(q, graph) == [(str(A), "A")]


def test_vars_with_a_sigil(settings, graph):
    d = data("SELECT ?city WHERE { ?city ?p ?o }", cities(B))
    q = values(settings, P + "SELECT ?city WHERE { ?city a ex:City }", d, ["?city"])
    assert rows(q, graph) == [(str(B),)]


def test_an_empty_result_restricts_to_nothing(settings, graph):
    d = data(f"SELECT ?city WHERE {{ ?city <{EX}none> ?o }}", Graph())
    q = values(settings, P + "SELECT ?city WHERE { ?city a ex:City }", d)
    assert rows(q, graph) == []


def test_columns_that_do_not_occur_leave_the_query_unchanged(settings):
    d = data("SELECT ?other WHERE { ?other ?p ?o }", cities(A))
    query = P + "SELECT ?city WHERE { ?city a ex:City }"
    assert values(settings, query, d) == query


def test_a_subquery_that_does_not_project_a_column_is_independent(settings, graph):
    d = data("SELECT ?city WHERE { ?city ?p ?o }", cities(B))
    q = values(settings, P + "SELECT ?city ?n WHERE { ?city a ex:City { SELECT (COUNT(?city) AS ?n) WHERE { ?city a ex:City } } }", d)
    assert rows(q, graph) == [(str(B), "3")]


def test_exists_is_correlated(settings, graph):
    d = data("SELECT ?city WHERE { ?city ?p ?o }", cities(A, B))
    q = values(settings, P + "SELECT ?city WHERE { ?city a ex:City FILTER EXISTS { ?city ex:mayor ?m } }", d)
    assert rows(q, graph) == [(str(A),)]


def test_assigning_a_column_raises(settings):
    d = data("SELECT ?city WHERE { ?city ?p ?o }", cities(A))
    with pytest.raises(ValueError):
        values(settings, P + "SELECT ?city WHERE { BIND(ex:A AS ?city) }", d)


def test_an_update_is_batched_over_the_rows(settings, graph):
    d = data("SELECT ?city WHERE { ?city ?p ?o }", cities(A, B))
    update = values(settings, P + "DELETE { ?city rdfs:label ?l } WHERE { ?city rdfs:label ?l }", d)
    graph.update(update)
    assert {str(s) for s in graph.subjects(RDFS.label)} == {str(C)}


def test_a_literal_with_a_quote_arrives_intact(settings):
    g = Graph()
    g.add((A, URIRef(EX + "p"), Literal('a"b\nc')))
    d = data(f"SELECT ?o WHERE {{ ?s <{EX}p> ?o }}", g)
    q = values(settings, "SELECT ?s WHERE { ?s ?p ?o }", d)
    assert rows(q, g) == [(str(A),)]


def test_a_bnode_raises(settings):
    g = Graph()
    g.add((A, URIRef(EX + "p"), BNode("b1")))
    d = data(f"SELECT ?o WHERE {{ ?s <{EX}p> ?o }}", g)
    with pytest.raises(ValueError):
        values(settings, "SELECT * WHERE { ?s ?p ?o }", d)


def test_wrong_query_type_raises(settings):
    with pytest.raises(TypeError):
        Operation.get("Values")(settings=settings).execute(URIRef("not-a-query"), data("SELECT ?s WHERE { ?s ?p ?o }"))


def test_wrong_data_type_raises(settings):
    with pytest.raises(TypeError):
        Operation.get("Values")(settings=settings).execute(Literal("SELECT * WHERE { ?s ?p ?o }"), [{"s": A}])
