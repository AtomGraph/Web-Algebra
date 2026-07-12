"""Spec: formal-semantics.md §4.1 "Filter — positional selection from a
sequence, XSLT-style"
Abstract: (Sequence α + Result) × Position → α
- 1-based; a Result input is treated as its row sequence (yields a Binding).
- Position < 1 or > length raises ValueError; a non-integer expression raises
  TypeError. Only positional expressions are defined in this version.
"""

from __future__ import annotations

import pytest
from rdflib import Literal
from rdflib.namespace import XSD

from web_algebra.json_result import JSONResult
from web_algebra.operation import Operation


def _result_of(*values: str) -> JSONResult:
    return JSONResult.from_json(
        {
            "head": {"vars": ["x"]},
            "results": {
                "bindings": [
                    {"x": {"type": "literal", "value": v}} for v in values
                ]
            },
        }
    )


class TestFilterPure:
    def test_positional_selection_returns_item(self, settings):
        # §4.1: 1-based positional selection yields the item itself
        op = Operation.get("Filter")(settings=settings)
        items = [Literal("a"), Literal("b"), Literal("c")]
        assert op.execute(items, 1) == Literal("a")
        assert op.execute(items, 3) == Literal("c")

    def test_result_input_yields_binding(self, settings):
        # §4.1: a Result input is treated as its row sequence
        op = Operation.get("Filter")(settings=settings)
        row = op.execute(_result_of("a", "b"), 2)
        assert row["x"] == Literal("b")

    def test_position_out_of_range_raises_value_error(self, settings):
        # §3.7: Filter position < 1 or > length → ValueError
        op = Operation.get("Filter")(settings=settings)
        items = [Literal("a")]
        with pytest.raises(ValueError):
            op.execute(items, 0)
        with pytest.raises(ValueError):
            op.execute(items, 2)

    def test_non_integer_expression_raises_type_error(self, settings):
        # §4.1: a non-integer expression raises TypeError
        op = Operation.get("Filter")(settings=settings)
        with pytest.raises(TypeError):
            op.execute([Literal("a")], "1")


class TestFilterJson:
    def test_json_dispatch(self, settings):
        # §4.1 JSON: input: Sequence + Result · expression: Position
        op = Operation.get("Filter")(settings=settings)
        result = op.execute_json({"input": ["a", "b", "c"], "expression": 2})
        # §2.2: the scalar "b" coerces to an xsd:string Literal
        assert result == Literal("b", datatype=XSD.string)

    def test_non_integer_expression_raises_type_error(self, settings):
        op = Operation.get("Filter")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json({"input": ["a"], "expression": "not-an-int"})
