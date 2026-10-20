"""Spec: formal-semantics.md §4.3 "Binding restriction" and "Substitute".

Substitute restricts one variable of a query or update to a term: the variable
stays a variable (still projected, still in templates, in every solution);
subqueries that do not project it get it renamed; assigning it (AS, VALUES)
raises ValueError; every group graph pattern gets the inline data; a variable
that does not occur leaves the query unchanged. Terms are written in SPARQL
syntax (IRIREF-excluded characters raise ValueError; ECHAR escaped); a BNode
raises TypeError.

Each restricted query is checked by what it answers over a small graph, not by
its text: that is what the spec promises.
"""

from __future__ import annotations

import pytest
from rdflib import Dataset, Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD
from rdflib.plugins.sparql import prepareQuery

from web_algebra.operation import Operation

EX = "http://example.org/"
C, D, M = URIRef(EX + "C"), URIRef(EX + "D"), URIRef(EX + "M")
CITY, MAYOR = URIRef(EX + "City"), URIRef(EX + "mayor")
P = f"PREFIX ex: <{EX}> PREFIX rdfs: <{RDFS}> "


@pytest.fixture
def graph():
    g = Graph()
    for city, label in ((C, "C"), (D, "D")):
        g.add((city, RDF.type, CITY))
        g.add((city, RDFS.label, Literal(label)))
    g.add((C, MAYOR, M))
    return g


def substitute(settings, query, var, binding):
    result = Operation.process_json(settings, {"@op": "Substitute", "args": {"query": query, "var": var, "binding": binding}})
    assert isinstance(result, Literal)
    return str(result)


def uri(u):
    return {"type": "uri", "value": str(u)}


def rows(query, graph):
    result = graph.query(prepareQuery(query))
    return sorted(tuple(str(v) if v is not None else None for v in row) for row in result)


# --- the variable stays a variable


def test_a_projected_variable_stays_projected(settings, graph):
    q = substitute(settings, P + "SELECT ?city ?label WHERE { ?city rdfs:label ?label }", "city", uri(C))
    assert rows(q, graph) == [(str(C), "C")]


def test_select_star_keeps_the_column(settings, graph):
    q = substitute(settings, P + "SELECT * WHERE { ?city rdfs:label ?label }", "city", uri(C))
    result = graph.query(q)
    assert [{str(k): str(v) for k, v in row.asdict().items()} for row in result] == [{"city": str(C), "label": "C"}]


def test_a_construct_template_keeps_the_variable(settings, graph):
    q = substitute(settings, P + "CONSTRUCT { ?city a ex:Selected } WHERE { ?city a ex:City }", "city", uri(C))
    assert set(graph.query(q).graph) == {(C, RDF.type, URIRef(EX + "Selected"))}


def test_ask(settings, graph):
    query = P + "ASK { ?city ex:mayor ?m }"
    assert graph.query(substitute(settings, query, "city", uri(C))).askAnswer is True
    assert graph.query(substitute(settings, query, "city", uri(D))).askAnswer is False


def test_a_describe_without_where_is_given_one(settings, graph):
    q = substitute(settings, "DESCRIBE ?city", "city", uri(C))
    described = {s for s, _, _ in graph.query(q).graph}
    assert described == {C}


def test_a_free_variable_takes_the_value(settings, graph):
    q = substitute(settings, "SELECT ?p WHERE { BIND(?parm AS ?p) }", "parm",
                   {"type": "literal", "value": "1", "datatype": str(XSD.integer)})
    assert rows(q, graph) == [("1",)]


# --- names


@pytest.mark.parametrize("var", ["city", "?city", "$city"])
def test_the_name_with_or_without_a_sigil(settings, graph, var):
    q = substitute(settings, P + "SELECT ?city WHERE { ?city a ex:City }", var, uri(D))
    assert rows(q, graph) == [(str(D),)]


def test_dollar_occurrences_are_the_same_variable(settings, graph):
    q = substitute(settings, P + "SELECT $city WHERE { $city a ex:City }", "city", uri(D))
    assert rows(q, graph) == [(str(D),)]


def test_a_longer_name_is_another_variable(settings, graph):
    q = substitute(settings, P + "SELECT ?city ?cityLabel WHERE { ?city a ex:City ; rdfs:label ?cityLabel }", "city", uri(C))
    assert rows(q, graph) == [(str(C), "C")]


def test_a_name_inside_a_string_is_not_the_variable(settings, graph):
    q = substitute(settings, P + 'SELECT ?city ?note WHERE { ?city a ex:City BIND("?city" AS ?note) }', "city", uri(C))
    assert rows(q, graph) == [(str(C), "?city")]


def test_a_variable_that_does_not_occur_leaves_the_query_unchanged(settings):
    query = P + "SELECT ?city WHERE { ?city a ex:City }"
    assert substitute(settings, query, "nope", uri(C)) == query


# --- scope


def test_a_subquery_that_does_not_project_it_is_independent(settings, graph):
    q = substitute(settings, P + "SELECT ?city ?n WHERE { ?city a ex:City "
                   "{ SELECT (COUNT(?city) AS ?n) WHERE { ?city a ex:City } } }", "city", uri(C))
    assert rows(q, graph) == [(str(C), "2")]


def test_a_subquery_that_projects_it_is_restricted(settings, graph):
    q = substitute(settings, P + "SELECT ?city WHERE { { SELECT ?city WHERE { ?city a ex:City } } }", "city", uri(C))
    assert rows(q, graph) == [(str(C),)]


def test_exists_is_correlated(settings, graph):
    query = P + "SELECT ?city WHERE { ?city a ex:City FILTER EXISTS { ?city ex:mayor ?m } }"
    assert rows(substitute(settings, query, "city", uri(C)), graph) == [(str(C),)]
    assert rows(substitute(settings, query, "city", uri(D)), graph) == []


def test_minus_keeps_the_variable(settings, graph):
    query = P + "SELECT ?city WHERE { ?city a ex:City MINUS { ?city ex:mayor ?m } }"
    assert rows(substitute(settings, query, "city", uri(C)), graph) == []
    assert rows(substitute(settings, query, "city", uri(D)), graph) == [(str(D),)]


def test_optional_is_restricted_too(settings, graph):
    q = substitute(settings, P + "SELECT ?city ?m WHERE { ?city a ex:City OPTIONAL { ?city ex:mayor ?m } }", "city", uri(C))
    assert rows(q, graph) == [(str(C), str(M))]


def test_union_branches_are_restricted(settings, graph):
    q = substitute(settings, P + "SELECT ?city WHERE { { ?city a ex:City } UNION { ?city ex:mayor ?m } }", "city", uri(D))
    assert rows(q, graph) == [(str(D),)]


def test_a_graph_variable_is_restricted(settings):
    ds = Dataset()
    ds.graph(URIRef(EX + "g1")).add((C, RDF.type, CITY))
    ds.graph(URIRef(EX + "g2")).add((D, RDF.type, CITY))
    q = substitute(settings, P + "SELECT ?g ?s WHERE { GRAPH ?g { ?s a ex:City } }", "g", uri(EX + "g1"))
    assert sorted((str(r[0]), str(r[1])) for r in ds.query(q)) == [(EX + "g1", str(C))]


# --- assignment


@pytest.mark.parametrize(
    "query",
    [
        P + "SELECT ?city WHERE { BIND(ex:C AS ?city) }",
        P + "SELECT (ex:C AS ?city) WHERE { }",
        P + "SELECT ?city WHERE { VALUES ?city { ex:C } }",
        P + "SELECT ?city WHERE { ?s a ex:City } GROUP BY (?s AS ?city)",
        P + "SELECT ?city WHERE { ?city a ex:City } VALUES ?city { ex:C }",
    ],
)
def test_assigning_the_variable_raises(settings, query):
    with pytest.raises(ValueError):
        substitute(settings, query, "city", uri(C))


def test_an_assignment_inside_a_subquery_that_does_not_project_it_is_its_own(settings, graph):
    q = substitute(settings, P + "SELECT ?x WHERE { ?city a ex:City { SELECT ?x WHERE { BIND(1 AS ?city) BIND(?city AS ?x) } } }",
                   "city", uri(C))
    assert rows(q, graph) == [("1",)]


# --- updates


def test_an_update_where_is_restricted(settings, graph):
    update = P + "DELETE { ?city rdfs:label ?old } INSERT { ?city rdfs:label ?new } WHERE { ?city rdfs:label ?old }"
    update = substitute(settings, update, "city", uri(C))
    update = substitute(settings, update, "new", {"type": "literal", "value": "Copenhagen"})
    graph.update(update)
    assert {(str(s), str(o)) for s, o in graph.subject_objects(RDFS.label)} == {(str(C), "Copenhagen"), (str(D), "D")}


def test_delete_where_is_written_long_and_restricted(settings, graph):
    graph.add((D, MAYOR, M))
    graph.update(substitute(settings, P + "DELETE WHERE { ?city ex:mayor ?m }", "city", uri(C)))
    assert set(graph.subjects(MAYOR, M)) == {D}


def test_construct_where_is_written_long_and_restricted(settings, graph):
    q = substitute(settings, P + "CONSTRUCT WHERE { ?city ex:mayor ?m }", "city", uri(D))
    assert set(graph.query(q).graph) == set()
    q = substitute(settings, P + "CONSTRUCT WHERE { ?city ex:mayor ?m }", "city", uri(C))
    assert set(graph.query(q).graph) == {(C, MAYOR, M)}


def test_a_query_that_does_not_parse_raises(settings):
    with pytest.raises(ValueError):
        substitute(settings, "SELEKT ?city WHERE { ?city ?p ?o }", "city", uri(C))


# --- terms


@pytest.mark.parametrize(
    "value",
    ['a "b"', "back\\slash", "C:\\dir", "a\\1", "x\\", "line1\nline2", "cr\rhere", "tab\there",
     "dollar $1 and \\g<0>", "ünïcødé ✓", "?city in text"],
)
@pytest.mark.parametrize("kind", ["simple", "lang", "typed"])
def test_a_literal_value_arrives_intact(settings, value, kind):
    g = Graph()
    term = {"simple": Literal(value), "lang": Literal(value, lang="fr"), "typed": Literal(value, datatype=URIRef(EX + "dt"))}[kind]
    g.add((C, URIRef(EX + "p"), term))
    binding = {"type": "literal", "value": value}
    if kind == "lang":
        binding["xml:lang"] = "fr"
    if kind == "typed":
        binding["datatype"] = EX + "dt"
    q = substitute(settings, "SELECT * WHERE { ?s ?p ?x }", "x", binding)
    assert len(list(g.query(q))) == 1


@pytest.mark.parametrize("bad", ["a b", "a>b", "a<b", 'a"b', "a{b", "a|b", "a^b", "a`b", "a\\b"])
def test_a_uri_with_a_character_iriref_excludes_raises(settings, bad):
    with pytest.raises(ValueError):
        substitute(settings, "SELECT * WHERE { ?s ?p ?x }", "x", uri(EX + bad))


def test_a_uri_with_query_and_fragment(settings):
    g = Graph()
    g.add((C, URIRef(EX + "p"), URIRef(EX + "a?b=c#d")))
    q = substitute(settings, "SELECT * WHERE { ?s ?p ?x }", "x", uri(EX + "a?b=c#d"))
    assert len(list(g.query(q))) == 1


def test_a_bnode_raises_type_error(settings):
    with pytest.raises(TypeError):
        substitute(settings, "DESCRIBE ?x WHERE { ?x ?p ?o }", "x", {"type": "bnode", "value": "b0"})


def test_wrong_argument_types_raise(settings):
    op = Operation.get("Substitute")(settings=settings)
    with pytest.raises(TypeError):
        op.execute(URIRef("not-a-query"), Literal("x"), C)
