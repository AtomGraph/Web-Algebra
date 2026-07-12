"""Spec: formal-semantics.md §4.1 "Position — the 1-based position of the
focus item, per XPath fn:position()"
Abstract: () → Literal
- An xsd:integer Literal; within a focus, 1 ≤ position ≤ size (§3.5).
- Raises ValueError when no focus is established.
"""

from __future__ import annotations

import pytest
from rdflib.namespace import XSD

from web_algebra.operation import Operation


class TestPositionJson:
    def test_positions_run_from_one_to_size(self, settings):
        # §3.5: ForEach establishes the focus (item i, i, n)
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {"select": ["a", "b", "c"], "operation": {"@op": "Position"}}
        )
        assert [int(v) for v in result] == [1, 2, 3]
        assert all(v.datatype == XSD.integer for v in result)

    def test_nested_for_each_shadows_the_focus(self, settings):
        # §3.5: a nested ForEach shadows the outer focus for its operand
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {
                "select": [["x", "y"]],
                "operation": {
                    "@op": "ForEach",
                    "args": {
                        "select": {"@op": "Current", "args": {}},
                        "operation": {"@op": "Position"},
                    },
                },
            }
        )
        assert [[int(v) for v in inner] for inner in result] == [[1, 2]]

    def test_no_focus_raises_value_error(self, settings):
        # §3.5/§3.7: no focus established → ValueError
        op = Operation.get("Position")(settings=settings)
        with pytest.raises(ValueError):
            op.execute_json({})
