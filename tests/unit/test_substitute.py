"""Spec: formal-semantics.md "Substitute - Replace variables in SPARQL queries"
Abstract: Literal × Literal × Term → Literal
Python:   def execute(self, query: Literal, var: Literal, binding_value: Any) -> Literal
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestSubstitutePure:
    def test_returns_literal(self, settings):
        # Most modest assertion derivable from the type signature alone.
        op = Operation.get("Substitute")(settings=settings)
        result = op.execute(
            Literal("SELECT ?x WHERE { ?x ?p ?o }"),
            Literal("x"),
            URIRef("http://example.org/foo"),
        )
        assert isinstance(result, Literal)

    def test_wrong_query_type_raises(self, settings):
        op = Operation.get("Substitute")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("not-a-query"), Literal("x"), URIRef("http://example.org/foo"))

    @pytest.mark.skip(reason="UNCLEAR(spec): SPARQL variable syntax — `?var`, `$var`, or both? How are URIRef/Literal binding values serialized into the query?")
    def test_replacement_form(self, settings):
        pass


class TestSubstituteJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): JSON arg keys for Substitute not given by spec or existing fixtures")
    def test_json_dispatch(self, settings):
        pass
