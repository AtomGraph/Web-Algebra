"""Spec: formal-semantics.md "Filter - Filter sequences or select from results"
Abstract: (Sequence α × Expression → α) + (Result × Expression → Result)
Python:   def execute(self, input_data: Any, expression: Any) -> Union[list, Any]

The sequence case in the abstract signature has a typo (returns `α`, a single
item, instead of `Sequence α`). Until the spec is corrected and the Expression
semantics are defined (line 27 declares `Expression = Operation + Literal +
Integer` but doesn't define how each kind acts as a predicate), tests are
blocked.
"""

from __future__ import annotations

import pytest

from web_algebra.operation import Operation


class TestFilterPure:
    @pytest.mark.skip(reason="UNCLEAR(spec): line 99 sequence case has typo (`→ α` should be `→ Sequence α`) and Expression evaluation is undefined")
    def test_basic(self, settings):
        pass


class TestFilterJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): see TestFilterPure")
    def test_json_dispatch(self, settings):
        pass
