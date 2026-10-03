"""Spec: formal-semantics.md §4.1 "Bindings — project a SPARQL result to its
row sequence"
Abstract: Result → Sequence Binding
- Order-preserving; an empty result yields the empty sequence.
- A Binding is a partial mapping from variable names to Terms (§1.1).
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

    def test_order_preserved(self, settings):
        # §4.1: order-preserving
        from web_algebra.json_result import JSONResult

        op = Operation.get("Bindings")(settings=settings)
        table = JSONResult.from_json(
            {
                "head": {"vars": ["x"]},
                "results": {
                    "bindings": [
                        {"x": {"type": "literal", "value": v}}
                        for v in ("a", "b", "c")
                    ]
                },
            }
        )
        rows = op.execute(table)
        assert [str(row["x"]) for row in rows] == ["a", "b", "c"]


class TestBindingsJson:
    def test_json_dispatch(self, settings):
        # §4.1 JSON: table: Result
        from web_algebra.json_result import JSONResult

        op = Operation.get("Bindings")(settings=settings)
        table = JSONResult.from_json(
            {
                "head": {"vars": ["x"]},
                "results": {"bindings": [{"x": {"type": "literal", "value": "a"}}]},
            }
        )
        rows = op.execute_json({"table": table})
        assert len(rows) == 1
        assert rows[0]["x"] == Literal("a")
