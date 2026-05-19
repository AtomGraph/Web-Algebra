"""Spec: formal-semantics.md "Value - Access variables and context values"
Abstract: String × Context × VariableStack → Any
Python:   def execute(self, name: str, context: Any, variable_stack: List[Dict[str, Any]]) -> Any
Plus Variable System property (lines 308-311) and Context System property (lines 314-318).
"""

from __future__ import annotations

import pytest
from rdflib import Literal

from web_algebra.operation import Operation


class TestValuePure:
    def test_lookup_in_innermost_scope(self, settings):
        # Variable System property: lexical scoping, innermost-first.
        op = Operation.get("Value")(settings=settings)
        stack = [{"x": Literal("outer")}, {"x": Literal("inner")}]
        result = op.execute("$x", {}, stack)
        assert result == Literal("inner")

    def test_lookup_falls_back_to_outer_scope(self, settings):
        op = Operation.get("Value")(settings=settings)
        stack = [{"x": Literal("outer")}, {"y": Literal("inner-only")}]
        result = op.execute("$x", {}, stack)
        assert result == Literal("outer")

    @pytest.mark.skip(reason="UNCLEAR(spec): which context container shapes does Value support? Context type is `Any` (line 315) and the narrative names ResultRow but doesn't enumerate other shapes (dict? attribute-bearing object? both?)")
    def test_context_lookup(self, settings):
        pass

    @pytest.mark.skip(reason="UNCLEAR(spec): precedence when same name appears in both context and stack")
    def test_context_vs_stack_precedence(self, settings):
        pass

    @pytest.mark.skip(reason="UNCLEAR(spec): behavior on missing name — error class unspecified")
    def test_missing_name(self, settings):
        pass


class TestValueJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): JSON arg key for Value not given by spec or existing fixtures")
    def test_json_dispatch(self, settings):
        pass
