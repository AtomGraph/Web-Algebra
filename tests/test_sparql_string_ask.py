"""SPARQLString's ASK check puts the query's WHERE pattern alone to the
endpoint (formal-semantics.md §4.3): with the query's FROM / FROM NAMED, and
without its projection, grouping, HAVING, ordering, LIMIT/OFFSET or trailing
VALUES - for every query form that has a pattern.

The operation's model call has no stub, so this tests the ASK it builds
directly; it is a test of the implementation and sits outside tests/unit/.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.plugins.sparql import prepareQuery

from web_algebra.operations.sparql_string import SPARQLString

EX = "http://example.org/"


def _ask(query):
    return SPARQLString._ask(query)


def _answers(ask: str, graph: Graph) -> bool:
    return bool(graph.query(prepareQuery(ask)).askAnswer)


@pytest.fixture
def graph():
    g = Graph()
    g.add((URIRef(EX + "a"), URIRef(EX + "p"), Literal(1)))
    g.add((URIRef(EX + "b"), URIRef(EX + "p"), Literal(2)))
    return g


@pytest.mark.parametrize(
    "query",
    [
        f"SELECT ?s WHERE {{ ?s <{EX}p> ?o }}",
        f"SELECT ?s WHERE {{ ?s <{EX}p> ?o }} ORDER BY ?s LIMIT 1 OFFSET 5",
        f"SELECT (COUNT(?s) AS ?n) WHERE {{ ?s <{EX}p> ?o }} GROUP BY ?o HAVING (COUNT(?s) > 100)",
        f"SELECT ?s WHERE {{ ?s <{EX}p> ?o }} VALUES ?s {{ <{EX}nope> }}",
        f"SELECT DISTINCT ?s {{ ?s <{EX}p> ?o }}",
        f"CONSTRUCT {{ ?s <{EX}q> ?o }} WHERE {{ ?s <{EX}p> ?o }}",
        f"CONSTRUCT WHERE {{ ?s <{EX}p> ?o }}",
        f"DESCRIBE ?s WHERE {{ ?s <{EX}p> ?o }}",
        f"ASK {{ ?s <{EX}p> ?o }}",
    ],
)
def test_the_pattern_alone_is_asked(query, graph):
    # every one of these patterns matches, whatever the modifiers would keep
    ask = _ask(query)
    assert ask is not None
    assert prepareQuery(ask).algebra.name == "AskQuery"
    assert _answers(ask, graph)


def test_a_pattern_that_matches_nothing_asks_false(graph):
    assert not _answers(_ask(f"SELECT ?s WHERE {{ ?s <{EX}nope> ?o }} LIMIT 10"), graph)


def test_the_prologue_is_kept(graph):
    ask = _ask(f"PREFIX ex: <{EX}> SELECT ?s WHERE {{ ?s ex:p ?o }}")
    assert _answers(ask, graph)


def test_the_dataset_clause_is_kept():
    ask = _ask(f"SELECT ?s FROM <{EX}g> FROM NAMED <{EX}h> WHERE {{ ?s ?p ?o }} LIMIT 1")
    assert f"FROM <{EX}g>" in ask and f"FROM NAMED <{EX}h>" in ask


def test_braces_and_keywords_inside_strings_and_iris_do_not_confuse_it(graph):
    query = f'SELECT ?s WHERE {{ ?s <{EX}p> ?o FILTER(STR(?s) != "}} WHERE {{ LIMIT") }} LIMIT 1'
    assert _answers(_ask(query), graph)


def test_a_subquery_stays_inside_the_pattern(graph):
    query = f"SELECT ?s WHERE {{ {{ SELECT ?s WHERE {{ ?s <{EX}p> ?o }} LIMIT 1 }} }} ORDER BY ?s"
    assert _answers(_ask(query), graph)


def test_a_describe_without_a_pattern_has_nothing_to_ask():
    assert _ask(f"DESCRIBE <{EX}a>") is None
