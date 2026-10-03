"""Spec: formal-semantics.md §4.5 "Merge — union of graphs"
Abstract: Sequence Graph → Graph
- Set union of triples: duplicate triples collapse.
- JSON: graphs: array of Graph or RDF data forms.
"""

from __future__ import annotations

from rdflib import Graph, Literal, URIRef

from web_algebra.operation import Operation


def _graph_with(triples):
    g = Graph()
    for t in triples:
        g.add(t)
    return g


class TestMergePure:
    def test_empty_sequence_returns_empty_graph(self, settings):
        op = Operation.get("Merge")(settings=settings)
        result = op.execute([])
        assert isinstance(result, Graph)
        assert len(result) == 0

    def test_single_graph_passthrough(self, settings):
        op = Operation.get("Merge")(settings=settings)
        triple = (URIRef("http://ex/s"), URIRef("http://ex/p"), Literal("o"))
        g = _graph_with([triple])
        result = op.execute([g])
        assert isinstance(result, Graph)
        assert triple in result

    def test_two_graphs_union(self, settings):
        op = Operation.get("Merge")(settings=settings)
        t1 = (URIRef("http://ex/s1"), URIRef("http://ex/p"), Literal("a"))
        t2 = (URIRef("http://ex/s2"), URIRef("http://ex/p"), Literal("b"))
        g1 = _graph_with([t1])
        g2 = _graph_with([t2])
        result = op.execute([g1, g2])
        assert isinstance(result, Graph)
        assert t1 in result
        assert t2 in result

    def test_duplicate_triples_deduplicated(self, settings):
        # §4.5: set union — duplicate triples collapse
        op = Operation.get("Merge")(settings=settings)
        triple = (URIRef("http://ex/s"), URIRef("http://ex/p"), Literal("o"))
        result = op.execute([_graph_with([triple]), _graph_with([triple])])
        assert len(result) == 1


class TestMergeJson:
    def test_json_dispatch(self, settings):
        # §4.5 JSON: graphs: array of Graph or RDF data forms
        op = Operation.get("Merge")(settings=settings)
        result = op.execute_json(
            {
                "graphs": [
                    {"@id": "http://ex/s1", "http://ex/p": "a"},
                    {"@id": "http://ex/s2", "http://ex/p": "b"},
                ]
            }
        )
        assert (URIRef("http://ex/s1"), URIRef("http://ex/p"), Literal("a")) in result
        assert (URIRef("http://ex/s2"), URIRef("http://ex/p"), Literal("b")) in result
