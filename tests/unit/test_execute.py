"""Spec: formal-semantics.md §4.1 "Execute — evaluate a quoted operation form
in the current context and environment"
Abstract: Operation⟨quoted⟩ → Any
- The operand must be an operation-call form (TypeError otherwise).
- It is evaluated in the current context AND the current variable environment.
"""

from __future__ import annotations

import pytest
from rdflib import Literal
from rdflib.namespace import XSD

from web_algebra.operation import Operation


class TestExecutePure:
    def test_evaluates_operation_form(self, settings):
        op = Operation.get("Execute")(settings=settings)
        result = op.execute({"@op": "Str", "args": {"input": "hi"}})
        # §2.2: the scalar "hi" coerces to an xsd:string Literal
        assert result == Literal("hi", datatype=XSD.string)

    def test_non_operation_form_raises_type_error(self, settings):
        # §4.1: the operand must be an operation-call form
        op = Operation.get("Execute")(settings=settings)
        with pytest.raises(TypeError):
            op.execute({"not-an-op": 1})
        with pytest.raises(TypeError):
            op.execute("just a string")


class TestExecuteJson:
    def test_json_dispatch(self, settings):
        # §4.1 JSON: operation⟨quoted⟩: an operation-call form
        op = Operation.get("Execute")(settings=settings)
        result = op.execute_json(
            {"operation": {"@op": "Str", "args": {"input": "hi"}}}
        )
        assert result == Literal("hi", datatype=XSD.string)

    def test_operand_sees_current_environment(self, settings):
        # §4.1/§3.3: the quoted operand evaluates in the current variable
        # environment — a variable bound outside Execute is visible inside.
        op = Operation.get("Execute")(settings=settings)
        stack = [{"x": Literal("bound")}]
        result = op.execute_json(
            {"operation": {"@op": "Value", "args": {"name": "$x"}}}, stack
        )
        assert result == Literal("bound")

    def test_operand_sees_current_context(self, settings):
        # §4.1/§3.3: the quoted operand evaluates in the current context.
        ctx = Literal("ctx-item")
        op = Operation.get("Execute")(settings=settings, context=ctx)
        result = op.execute_json({"operation": {"@op": "Current", "args": {}}})
        assert result == ctx
