"""Spec: formal-semantics.md "Execute - Execute nested operation"
Abstract: Operation → Any
Python:   def execute(self, operation: Any) -> Any

The spec entry has only a signature; no narrative description is given. All
behavioral cases are blocked until the spec adds one.
"""

from __future__ import annotations

import pytest

from web_algebra.operation import Operation


class TestExecutePure:
    @pytest.mark.skip(reason="UNCLEAR(spec): Execute has no narrative description in formal-semantics.md — what does it do that JSON dispatch doesn't already?")
    def test_basic(self, settings):
        pass


class TestExecuteJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): Execute has no narrative description in formal-semantics.md")
    def test_json_dispatch(self, settings):
        pass
