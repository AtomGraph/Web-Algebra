"""Spec: formal-semantics.md "Current - Return current context item"
Abstract: Any → Any
Python:   def execute(self, current_item: Any) -> Any
Plus Context System property: "Current Operation: Returns the current context item unchanged" (line 317).
"""

from __future__ import annotations

import pytest
from rdflib import Literal

from web_algebra.operation import Operation


class TestCurrentPure:
    def test_returns_argument_unchanged(self, settings):
        op = Operation.get("Current")(settings=settings)
        sentinel = Literal("ctx-value")
        result = op.execute(sentinel)
        assert result is sentinel or result == sentinel

    @pytest.mark.skip(reason="UNCLEAR(spec): behavior when context is unset (default `{}` per the abstract type signature)")
    def test_unset_context(self, settings):
        pass


class TestCurrentJson:
    def test_returns_context_value(self, settings):
        # Current's JSON form takes empty args and reads from context (set by ForEach).
        op_cls = Operation.get("Current")
        ctx_value = Literal("ctx-value")
        op = op_cls(settings=settings, context=ctx_value)
        result = op.execute_json({})
        assert result == ctx_value
