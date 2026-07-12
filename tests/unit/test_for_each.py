"""Spec: formal-semantics.md §4.1 "ForEach — evaluate an operation once per
item of a sequence or per row of a SPARQL result"
Abstract: (Sequence α + Result) × Operation⟨quoted⟩ → Sequence β
- Interpreter-level special form: execute_json only, no pure layer (§4.1).
- Iterates a Sequence item-by-item, a Result row-by-row in result order.
- Each iteration runs in a fresh variable scope with the item as context.
- Operation arrays evaluate in order; the iteration's value is the last
  non-Unit result. Unit-valued iterations are dropped; sequence-valued
  results stay nested (no flattening).
"""

from __future__ import annotations

import pytest
from rdflib import Literal
from rdflib.namespace import XSD

from web_algebra.json_result import JSONResult
from web_algebra.operation import Operation


class TestForEachJson:
    def test_empty_sequence(self, settings):
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {
                "select": [],
                "operation": {"@op": "Str", "args": {"input": {"@op": "Current", "args": {}}}},
            }
        )
        assert result == []

    def test_length_matches_input(self, settings):
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {
                "select": ["a", "b", "c"],
                "operation": {"@op": "Str", "args": {"input": {"@op": "Current", "args": {}}}},
            }
        )
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(item, Literal) for item in result)
        assert [str(item) for item in result] == ["a", "b", "c"]

    def test_non_iterable_select_raises(self, settings):
        # §4.1: any other `select` value raises TypeError
        op = Operation.get("ForEach")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "select": "not-a-list-or-result",
                    "operation": {"@op": "Current", "args": {}},
                }
            )

    def test_unit_valued_iterations_are_dropped(self, settings):
        # §4.1: iteration values that are Unit (None) are dropped — Variable
        # returns Unit, so an all-Variable operation yields the empty sequence.
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {
                "select": ["a", "b"],
                "operation": {
                    "@op": "Variable",
                    "args": {"name": "x", "value": {"@op": "Current", "args": {}}},
                },
            }
        )
        assert result == []

    def test_sequence_results_stay_nested(self, settings):
        # §4.1: sequence-valued iteration results are kept nested (no
        # flattening) — a nested ForEach yields a sequence per outer item.
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {
                "select": [["a", "b"]],
                "operation": {
                    "@op": "ForEach",
                    "args": {
                        "select": {"@op": "Current", "args": {}},
                        "operation": {
                            "@op": "Str",
                            "args": {"input": {"@op": "Current", "args": {}}},
                        },
                    },
                },
            }
        )
        # §2.2: scalars coerce to xsd:string Literals
        assert result == [
            [Literal("a", datatype=XSD.string), Literal("b", datatype=XSD.string)]
        ]

    def test_operation_array_yields_last_non_unit(self, settings):
        # §4.1: operation arrays evaluate in order within the iteration's
        # scope; the iteration's value is the last non-Unit result.
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {
                "select": ["a"],
                "operation": [
                    {
                        "@op": "Variable",
                        "args": {"name": "x", "value": {"@op": "Current", "args": {}}},
                    },
                    {"@op": "Str", "args": {"input": {"@op": "Value", "args": {"name": "$x"}}}},
                ],
            }
        )
        assert result == [Literal("a", datatype=XSD.string)]

    def test_iteration_scope_does_not_leak(self, settings):
        # §3.4: each iteration runs in a fresh scope — bindings made inside
        # do not survive the ForEach.
        op = Operation.get("ForEach")(settings=settings)
        stack = [{}]
        op.execute_json(
            {
                "select": ["a"],
                "operation": [
                    {"@op": "Variable", "args": {"name": "x", "value": "v"}},
                    {"@op": "Current", "args": {}},
                ],
            },
            stack,
        )
        assert stack == [{}]

    def test_result_rows_iterate_in_result_order(self, settings):
        # §4.1: a Result iterates row-by-row in result order
        op = Operation.get("ForEach")(settings=settings)
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
        result = op.execute_json(
            {
                "select": table,
                "operation": {"@op": "Value", "args": {"name": "x"}},
            }
        )
        assert [str(v) for v in result] == ["a", "b", "c"]
