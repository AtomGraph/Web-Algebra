"""Spec: formal-semantics.md §4.2 "Str — the lexical form of a Term, per
SPARQL 1.1 STR()": simple literal STR(literal ltrl) / simple literal STR(IRI rsrc)
- Returns the lexical form / codepoint representation as a simple literal
  (no datatype, no language tag).
- The language tag is not carried over.
- BNode raises TypeError (a SPARQL type error), as does any non-Term.
"""

from __future__ import annotations

import pytest
from rdflib import BNode, Literal, URIRef

from web_algebra.operation import Operation


def _is_simple_literal(value) -> bool:
    return (
        isinstance(value, Literal)
        and value.datatype is None
        and value.language is None
    )


class TestStrPure:
    def test_uri_yields_simple_literal_of_codepoints(self, settings):
        # §4.2: simple literal STR(IRI rsrc)
        op = Operation.get("Str")(settings=settings)
        result = op.execute(URIRef("http://example.org/foo"))
        assert _is_simple_literal(result)
        assert str(result) == "http://example.org/foo"

    def test_plain_literal_yields_simple_literal(self, settings):
        op = Operation.get("Str")(settings=settings)
        result = op.execute(Literal("hello"))
        assert _is_simple_literal(result)
        assert str(result) == "hello"

    def test_lang_tag_is_not_carried_over(self, settings):
        # §4.2: as in SPARQL, STR("hallo"@de) → "hallo" (simple literal)
        op = Operation.get("Str")(settings=settings)
        result = op.execute(Literal("hallo", lang="de"))
        assert _is_simple_literal(result)
        assert str(result) == "hallo"

    def test_typed_literal_yields_lexical_form(self, settings):
        # §4.2: STR(42) → "42" (simple literal)
        op = Operation.get("Str")(settings=settings)
        result = op.execute(Literal(42))
        assert _is_simple_literal(result)
        assert str(result) == "42"

    def test_bnode_raises_type_error(self, settings):
        # §4.2: STR accepts a literal or an IRI; a blank node is a type error
        op = Operation.get("Str")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(BNode("b1"))

    def test_non_term_raises_type_error(self, settings):
        # §3.7 strict typing
        op = Operation.get("Str")(settings=settings)
        with pytest.raises(TypeError):
            op.execute([1, 2, 3])


class TestStrJson:
    def test_string_input_via_json(self, settings):
        # §4.2 JSON: input: URI + Literal
        op = Operation.get("Str")(settings=settings)
        result = op.execute_json({"input": "hello"})
        assert _is_simple_literal(result)
        assert str(result) == "hello"

    def test_nested_uri_op(self, settings):
        op = Operation.get("Str")(settings=settings)
        result = op.execute_json(
            {"input": {"@op": "URI", "args": {"input": "http://example.org/x"}}}
        )
        assert _is_simple_literal(result)
        assert str(result) == "http://example.org/x"
