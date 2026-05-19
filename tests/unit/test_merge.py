"""Spec: formal-semantics.md "Merge - Merge multiple RDF graphs into one"
Abstract: Sequence Graph → Graph
Python:   def execute(self, graphs: List[rdflib.Graph]) -> rdflib.Graph
"""

from __future__ import annotations

import pytest
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

    @pytest.mark.skip(reason="UNCLEAR(spec): duplicate-triple semantics (set union vs multiset) not stated")
    def test_duplicate_triples_deduplicated(self, settings):
        pass


class TestMergeJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): JSON arg key for Merge ('graphs'? 'input'?) not given by spec or existing fixtures")
    def test_json_dispatch(self, settings):
        pass
