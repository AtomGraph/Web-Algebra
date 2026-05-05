"""Spec: formal-semantics.md "SPARQLString - Generate SPARQL queries from natural language"
Abstract: Literal → Literal
Python:   def execute(self, question: Literal) -> Literal

This operation calls an LLM and is non-deterministic — there is no testable
invariant beyond return type, and even that requires an OpenAI client.
"""

from __future__ import annotations

import pytest

from web_algebra.operation import Operation


class TestSPARQLStringPure:
    @pytest.mark.skip(reason="UNCLEAR(spec): operation depends on an LLM; no deterministic testable invariant in spec")
    def test_basic(self, settings):
        pass


class TestSPARQLStringJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): same as TestSPARQLStringPure")
    def test_json_dispatch(self, settings):
        pass
