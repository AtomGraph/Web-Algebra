"""Spec: formal-semantics.md §4.1 "Current — the context item itself"
Abstract: () → Context
- Yields the context item; raises ValueError when no context is
  established (§3.5: only ForEach establishes one).
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

    def test_unset_context_raises_value_error(self, settings):
        # §3.5/§3.7: no context established → ValueError
        op = Operation.get("Current")(settings=settings)
        with pytest.raises(ValueError):
            op.execute_json({})


class TestCurrentJson:
    def test_returns_context_value(self, settings):
        # Current's JSON form takes empty args and reads from context (set by ForEach).
        op_cls = Operation.get("Current")
        ctx_value = Literal("ctx-value")
        op = op_cls(settings=settings, context=ctx_value)
        result = op.execute_json({})
        assert result == ctx_value
