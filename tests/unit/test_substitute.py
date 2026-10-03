"""Spec: formal-semantics.md §4.3 "Substitute — textually substitute one
SPARQL variable with a Term"
Abstract: Literal × Literal × (URI + Literal) → Literal
- Matches both `?var` and `$var` at token boundaries.
- URI serializes as `<iri>`; Literal as a quoted literal with its language
  tag or datatype. BNode raises TypeError.
"""

from __future__ import annotations

import pytest
from rdflib import BNode, Literal, URIRef

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

    def test_question_mark_variable_replaced_with_iri(self, settings):
        # §4.3: `?var` matched; URI serializes as <iri>
        op = Operation.get("Substitute")(settings=settings)
        result = op.execute(
            Literal("DESCRIBE ?x"), Literal("x"), URIRef("http://example.org/foo")
        )
        assert "<http://example.org/foo>" in str(result)
        assert "?x" not in str(result)

    def test_dollar_variable_replaced(self, settings):
        # §4.3: `$var` matched too
        op = Operation.get("Substitute")(settings=settings)
        result = op.execute(
            Literal("DESCRIBE $x"), Literal("x"), URIRef("http://example.org/foo")
        )
        assert "<http://example.org/foo>" in str(result)
        assert "$x" not in str(result)

    def test_token_boundary_respected(self, settings):
        # §4.3: matches at token boundaries — ?xy must not be touched when
        # substituting ?x
        op = Operation.get("Substitute")(settings=settings)
        result = op.execute(
            Literal("SELECT ?xy WHERE { ?x ?p ?xy }"),
            Literal("x"),
            URIRef("http://example.org/foo"),
        )
        assert "?xy" in str(result)

    def test_literal_value_serialized_with_datatype(self, settings):
        # §4.3: Literal serializes as a quoted literal with its datatype
        op = Operation.get("Substitute")(settings=settings)
        result = op.execute(
            Literal("SELECT * WHERE { ?s ?p ?x }"),
            Literal("x"),
            Literal("42", datatype=URIRef("http://www.w3.org/2001/XMLSchema#integer")),
        )
        assert '"42"' in str(result)
        assert "http://www.w3.org/2001/XMLSchema#integer" in str(result)

    def test_bnode_value_raises_type_error(self, settings):
        # §4.3: a blank-node label in a query is a fresh variable, not a
        # reference — BNode raises TypeError
        op = Operation.get("Substitute")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("DESCRIBE ?x"), Literal("x"), BNode("b1"))


class TestSubstituteJson:
    def test_json_dispatch(self, settings):
        # §4.3 JSON: query · var · binding (Term or SPARQL JSON term form §2.4)
        op = Operation.get("Substitute")(settings=settings)
        result = op.execute_json(
            {
                "query": "DESCRIBE ?x",
                "var": "x",
                "binding": {"type": "uri", "value": "http://example.org/foo"},
            }
        )
        assert isinstance(result, Literal)
        assert "<http://example.org/foo>" in str(result)
