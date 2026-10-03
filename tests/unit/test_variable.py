"""Spec: formal-semantics.md §4.1 "Variable — bind a name in the current scope"
Abstract: String × Any → Unit
- Binds in the innermost scope; rebinding the same name overwrites (§3.4).
- The JSON layer returns Unit (None).
- Scope creation belongs to sequences and ForEach iterations, not to Variable.
"""

from __future__ import annotations

from rdflib import Literal
from rdflib.namespace import XSD

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

    def test_returns_unit(self, settings):
        # §4.1: Abstract String × Any → Unit; JSON layer returns None
        op = Operation.get("Variable")(settings=settings)
        assert op.execute("x", Literal("v"), [{}]) is None

    def test_binds_into_innermost_scope_only(self, settings):
        # §3.4: Variable binds in the innermost scope; it does not push or
        # pop scopes itself.
        op = Operation.get("Variable")(settings=settings)
        stack = [{}, {}]
        op.execute("x", Literal("v"), stack)
        assert len(stack) == 2
        assert "x" not in stack[0]
        assert stack[1]["x"] == Literal("v")

    def test_rebinding_overwrites(self, settings):
        # §3.4: rebinding a name in the same scope overwrites it
        op = Operation.get("Variable")(settings=settings)
        stack = [{}]
        op.execute("x", Literal("first"), stack)
        op.execute("x", Literal("second"), stack)
        assert stack[0]["x"] == Literal("second")


class TestVariableJson:
    def test_json_dispatch(self, settings):
        # §4.1 JSON: name: String · value: any form; returns Unit (None)
        op = Operation.get("Variable")(settings=settings)
        stack = [{}]
        result = op.execute_json({"name": "x", "value": "v"}, stack)
        assert result is None
        value_op = Operation.get("Value")(settings=settings)
        # §2.2: the scalar "v" coerces to an xsd:string Literal
        assert value_op.execute_json({"name": "$x"}, stack) == Literal(
            "v", datatype=XSD.string
        )
