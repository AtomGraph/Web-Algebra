"""Spec: formal-semantics.md "Variable - Set variables in current scope (XSLT-style)"
Abstract: String × Any × VariableStack → ⊥
Python:   def execute(self, name: str, value: Any, variable_stack: List[Dict[str, Any]]) -> None
Plus Variable System property (lines 308-311).
"""

from __future__ import annotations

import pytest
from rdflib import Literal

from web_algebra.operation import Operation


class TestVariablePure:
    def test_binds_into_current_scope(self, settings):
        # After binding, Value should resolve the same name to the bound value.
        var_op = Operation.get("Variable")(settings=settings)
        value_op = Operation.get("Value")(settings=settings)
        stack = [{}]
        var_op.execute("x", Literal("v"), stack)
        result = value_op.execute("$x", {}, stack)
        assert result == Literal("v")

    @pytest.mark.skip(reason="UNCLEAR(spec): `⊥` (bottom) return type — what does execute_json return on the JSON layer?")
    def test_return_value(self, settings):
        pass

    @pytest.mark.skip(reason="UNCLEAR(spec): line 311 self-contradiction — does Variable push a new scope or write into the current one?")
    def test_scope_management(self, settings):
        pass


class TestVariableJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): JSON arg keys for Variable not given by spec or existing fixtures")
    def test_json_dispatch(self, settings):
        pass
