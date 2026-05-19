"""Spec: formal-semantics.md "ForEach - Map operation over sequence (sequence → sequence semantics)"
Abstract: Sequence α × Operation → Sequence β
Python:   def execute(self, select_data: Union[List[Any], rdflib.query.Result],
                      operation: Any) -> List[Any]
Plus Sequence Semantics property (lines 302-306).
"""

from __future__ import annotations

import pytest
from rdflib import Literal

from web_algebra.operation import Operation


class TestForEachPure:
    @pytest.mark.skip(reason="UNCLEAR(spec): ForEach pure execute() requires an Operation value plus dispatcher context — abstract signature is testable only via execute_json")
    def test_pure(self, settings):
        pass


class TestForEachJson:
    def test_empty_sequence(self, settings):
        # JSON arg keys derived from Python parameter names: select_data → "select" by convention.
        # The existing fixture set has no ForEach example; flagged in SPEC_GAPS for confirmation.
        op = Operation.get("ForEach")(settings=settings)
        # Use the JSON dispatcher: an inner Str on each item.
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
        # Strict Type Checking property: select must be a Sequence or Result.
        op = Operation.get("ForEach")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "select": "not-a-list-or-result",
                    "operation": {"@op": "Current", "args": {}},
                }
            )

    @pytest.mark.skip(reason="UNCLEAR(spec): output shape when inner op returns None or a sequence — flatten? filter Nones?")
    def test_inner_op_none_handling(self, settings):
        pass

    @pytest.mark.skip(reason="UNCLEAR(spec): SPARQL Result iteration order")
    def test_result_iteration_order(self, settings):
        pass
