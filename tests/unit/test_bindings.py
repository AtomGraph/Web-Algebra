"""Spec: formal-semantics.md "Bindings - Extract binding sequence from SPARQL results"
Abstract: Result → Sequence ResultRow
Python:   def execute(self, table: rdflib.query.Result) -> List[Dict[str, Any]]

Note: the abstract signature says `Sequence ResultRow`, but the Python signature
returns `List[Dict[str, Any]]`. The spec is internally inconsistent here; tests
assert only the abstract sequence shape (length / non-empty / iterable).
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, URIRef

from web_algebra.operation import Operation


def _result_with_two_rows():
    g = Graph()
    g.add((URIRef("http://ex/a"), URIRef("http://ex/p"), Literal("v1")))
    g.add((URIRef("http://ex/b"), URIRef("http://ex/p"), Literal("v2")))
    return g.query("SELECT ?s ?o WHERE { ?s <http://ex/p> ?o }")


def _empty_result():
    g = Graph()
    return g.query("SELECT ?s WHERE { ?s ?p ?o }")


class TestBindingsPure:
    def test_returns_iterable(self, settings):
        op = Operation.get("Bindings")(settings=settings)
        result = op.execute(_result_with_two_rows())
        # Spec says "Sequence ResultRow" — assert it is iterable and has length.
        assert hasattr(result, "__iter__")
        assert len(list(result)) == 2

    def test_empty_result_yields_empty_sequence(self, settings):
        # Reasonable from the type signature, though spec doesn't state it.
        op = Operation.get("Bindings")(settings=settings)
        result = op.execute(_empty_result())
        assert len(list(result)) == 0

    def test_non_result_input_raises(self, settings):
        # Strict Type Checking property
        op = Operation.get("Bindings")(settings=settings)
        with pytest.raises(TypeError):
            op.execute([1, 2, 3])

    @pytest.mark.skip(reason="UNCLEAR(spec): order preservation not stated")
    def test_order_preserved(self, settings):
        pass


class TestBindingsJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): JSON arg key for Bindings not given by spec or existing fixtures")
    def test_json_dispatch(self, settings):
        pass
