"""Spec: formal-semantics.md §4.1 "Last — the size of the iterated sequence,
per XPath fn:last()"
Abstract: () → Literal
- An xsd:integer Literal (§3.5).
- Raises ValueError when no focus is established.
"""

from __future__ import annotations

import pytest
from rdflib.namespace import XSD

from web_algebra.operation import Operation


class TestLastJson:
    def test_last_is_the_iteration_size_in_every_iteration(self, settings):
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {"select": ["a", "b", "c"], "operation": {"@op": "Last"}}
        )
        assert [int(v) for v in result] == [3, 3, 3]
        assert all(v.datatype == XSD.integer for v in result)

    def test_empty_iteration_never_evaluates_last(self, settings):
        # ForEach over the empty sequence never evaluates the operand, so
        # Last (which would have no meaningful value) is never reached.
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json({"select": [], "operation": {"@op": "Last"}})
        assert result == []

    def test_no_focus_raises_value_error(self, settings):
        # §3.5/§3.7: no focus established → ValueError
        op = Operation.get("Last")(settings=settings)
        with pytest.raises(ValueError):
            op.execute_json({})
