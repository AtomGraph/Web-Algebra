"""Spec: formal-semantics.md §4.3 "SPARQLString — generate a SPARQL query
string from natural language via an LLM"
Abstract: Literal → Literal
- Non-deterministic; only the type contract is normative (§4.3). Exercising
  it requires an OpenAI client, so behavior is covered by live runs only.
"""

from __future__ import annotations

import pytest



class TestSPARQLStringPure:
    @pytest.mark.skip(reason="§4.3: non-deterministic (LLM); type-only contract needs a live OpenAI client to exercise")
    def test_basic(self, settings):
        pass


class TestSPARQLStringJson:
    @pytest.mark.skip(reason="§4.3: same as TestSPARQLStringPure")
    def test_json_dispatch(self, settings):
        pass
