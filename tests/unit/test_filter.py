"""Spec: formal-semantics.md §4.1 "Filter — selection by position from a
sequence, or by name from a row, XPath-style"
Abstract: (Sequence α + Result + Binding) × (Position + Literal) → α
- With a Position (xsd:integer Literal): 1-based; a Result input is treated
  as its row sequence (yields a Binding). Position < 1 or > length raises
  ValueError.
- With a string Literal on a Binding: the term bound to that variable name,
  given bare or with `?`/`$`; a miss raises ValueError.
- Any other pairing — a Literal on a sequence or result, a Position on a
  Binding, an expression neither integer nor string — raises TypeError.
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef
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


def _pos(n: int) -> Literal:
    return Literal(n, datatype=XSD.integer)


class TestFilterPositional:
    def test_positional_selection_returns_item(self, settings):
        # §4.1: 1-based positional selection yields the item itself
        op = Operation.get("Filter")(settings=settings)
        items = [Literal("a"), Literal("b"), Literal("c")]
        assert op.execute(items, _pos(1)) == Literal("a")
        assert op.execute(items, _pos(3)) == Literal("c")

    def test_result_input_yields_binding(self, settings):
        # §4.1: a Result input is treated as its row sequence
        op = Operation.get("Filter")(settings=settings)
        row = op.execute(_result_of("a", "b"), _pos(2))
        assert row["x"] == Literal("b")

    def test_position_out_of_range_raises_value_error(self, settings):
        # §3.7: Filter position < 1 or > length → ValueError
        op = Operation.get("Filter")(settings=settings)
        items = [Literal("a")]
        with pytest.raises(ValueError):
            op.execute(items, _pos(0))
        with pytest.raises(ValueError):
            op.execute(items, _pos(2))

    def test_position_out_of_range_on_result_raises_value_error(self, settings):
        op = Operation.get("Filter")(settings=settings)
        with pytest.raises(ValueError):
            op.execute(_result_of("a"), _pos(2))
        with pytest.raises(ValueError):
            op.execute(_result_of("a"), _pos(0))

    def test_position_on_binding_raises_type_error(self, settings):
        # §4.1: a Position on a Binding is not a defined pairing
        op = Operation.get("Filter")(settings=settings)
        row = op.execute(_result_of("a"), _pos(1))
        with pytest.raises(TypeError):
            op.execute(row, _pos(1))


class TestFilterByName:
    @pytest.mark.parametrize("name", ["x", "?x", "$x"])
    def test_name_lookup_on_binding(self, settings, name):
        # §4.1: a string Literal on a Binding yields the term bound to that
        # variable name, bare or with either SPARQL sigil
        op = Operation.get("Filter")(settings=settings)
        row = op.execute(_result_of("a", "b"), _pos(2))
        assert op.execute(row, Literal(name, datatype=XSD.string)) == Literal("b")

    def test_simple_literal_name_lookup(self, settings):
        # §4.2 preamble: a simple literal denotes the same value as xsd:string
        op = Operation.get("Filter")(settings=settings)
        row = op.execute(_result_of("a"), _pos(1))
        assert op.execute(row, Literal("x")) == Literal("a")

    def test_name_lookup_on_bindings_row(self, settings):
        # §1.2: a Binding is a ResultRow or a Dict via Bindings
        rows = Operation.get("Bindings")(settings=settings).execute(_result_of("a", "b"))
        op = Operation.get("Filter")(settings=settings)
        row = op.execute(rows, _pos(1))
        assert op.execute(row, Literal("x")) == Literal("a")

    def test_name_miss_raises_value_error(self, settings):
        # §4.1: a miss raises ValueError, as the focus lookup of §3.5 does
        op = Operation.get("Filter")(settings=settings)
        row = op.execute(_result_of("a"), _pos(1))
        with pytest.raises(ValueError):
            op.execute(row, Literal("nope"))

    def test_literal_on_sequence_raises_type_error(self, settings):
        op = Operation.get("Filter")(settings=settings)
        with pytest.raises(TypeError):
            op.execute([Literal("a")], Literal("x"))

    def test_literal_on_result_raises_type_error(self, settings):
        op = Operation.get("Filter")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(_result_of("a"), Literal("x"))

    def test_digit_string_is_a_name_not_a_position(self, settings):
        # §2.2: "1" is a string Literal, so on a sequence it is a Literal on a
        # sequence → TypeError (only the XML serialization reads it as a
        # position, §5)
        op = Operation.get("Filter")(settings=settings)
        with pytest.raises(TypeError):
            op.execute([Literal("a")], Literal("1", datatype=XSD.string))


class TestFilterOtherExpressions:
    @pytest.mark.parametrize(
        "expression",
        [
            URIRef("http://example.org/x"),
            Literal(1.0, datatype=XSD.double),
            Literal(True, datatype=XSD.boolean),
        ],
        ids=["uri", "double", "boolean"],
    )
    def test_other_expression_raises_type_error(self, settings, expression):
        # §4.1: an expression that is neither integer nor string → TypeError
        op = Operation.get("Filter")(settings=settings)
        with pytest.raises(TypeError):
            op.execute([Literal("a")], expression)
        row = op.execute(_result_of("a"), _pos(1))
        with pytest.raises(TypeError):
            op.execute(row, expression)


class TestFilterJson:
    def test_json_dispatch(self, settings):
        # §4.1 JSON: a JSON integer coerces to xsd:integer (§2.2), a Position
        op = Operation.get("Filter")(settings=settings)
        result = op.execute_json({"input": ["a", "b", "c"], "expression": 2})
        # §2.2: the scalar "b" coerces to an xsd:string Literal
        assert result == Literal("b", datatype=XSD.string)

    def test_json_position_on_result(self, settings):
        op = Operation.get("Filter")(settings=settings)
        row = op.execute_json({"input": _result_of("a", "b"), "expression": 1})
        assert row["x"] == Literal("a")

    def test_json_lookup_by_name(self, settings):
        # §4.1: Filter(Filter(R, 1), "x") — the first row, then its x
        op = Operation.get("Filter")(settings=settings)
        result = op.execute_json(
            {
                "input": {
                    "@op": "Filter",
                    "args": {"input": _result_of("a", "b"), "expression": 1},
                },
                "expression": "?x",
            }
        )
        assert result == Literal("a")

    def test_json_string_on_sequence_raises_type_error(self, settings):
        op = Operation.get("Filter")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json({"input": ["a"], "expression": "not-an-int"})

    def test_json_out_of_range_raises_value_error(self, settings):
        op = Operation.get("Filter")(settings=settings)
        with pytest.raises(ValueError):
            op.execute_json({"input": ["a"], "expression": 5})

    def test_json_name_miss_raises_value_error(self, settings):
        op = Operation.get("Filter")(settings=settings)
        with pytest.raises(ValueError):
            op.execute_json(
                {
                    "input": {
                        "@op": "Filter",
                        "args": {"input": _result_of("a"), "expression": 1},
                    },
                    "expression": "y",
                }
            )
