"""Spec: formal-semantics.md §4.3 Substitute, §2.4 SPARQL JSON term form.
- Only the `?var`/`$var` occurrences change; a `var` that does not occur leaves
  the query unchanged.
- The value is written in SPARQL syntax and inserted as it is: a Literal is a
  quoted string with `\\`, `"`, LF and CR escaped (ECHAR), then its language
  tag or `^^<datatype>`; a URI is `<iri>`, and one containing a character an
  IRIREF excludes raises ValueError.
- `binding` accepts a Term or a SPARQL JSON term object.

A substituted query is checked by parsing it and running it over a graph that
holds the substituted term: one row means the term arrived intact.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import XSD
from rdflib.plugins.sparql import prepareQuery

from web_algebra.operation import Operation

EX = "http://example.org/"
QUERY = "SELECT * WHERE { ?s ?p ?x }"


def _substitute(settings, query, var, binding):
    result = Operation.process_json(
        settings,
        {"@op": "Substitute", "args": {"query": query, "var": var, "binding": binding}},
    )
    assert isinstance(result, Literal)
    return str(result)


def _matches(query: str, term) -> int:
    g = Graph()
    g.add((URIRef(EX + "s"), URIRef(EX + "p"), term))
    return len(list(g.query(prepareQuery(query))))


class TestOnlyTheVariableChanges:
    def test_uri_replaces_exactly_the_variable(self, settings):
        out = _substitute(settings, QUERY, "x", {"type": "uri", "value": EX + "a"})
        assert out == f"SELECT * WHERE {{ ?s ?p <{EX}a> }}"

    def test_dollar_occurrence_is_replaced_too(self, settings):
        out = _substitute(
            settings, "SELECT * WHERE { ?s ?p $x }", "x", {"type": "uri", "value": EX + "a"}
        )
        assert out == f"SELECT * WHERE {{ ?s ?p <{EX}a> }}"

    def test_var_given_with_question_mark(self, settings):
        out = _substitute(settings, QUERY, "?x", {"type": "uri", "value": EX + "a"})
        assert out == f"SELECT * WHERE {{ ?s ?p <{EX}a> }}"

    def test_var_that_does_not_occur_leaves_the_query_unchanged(self, settings):
        out = _substitute(settings, QUERY, "nope", {"type": "uri", "value": EX + "a"})
        assert out == QUERY

    def test_token_boundary(self, settings):
        # ?xy is another variable and is left alone
        q = "SELECT * WHERE { ?s ?x ?xy }"
        out = _substitute(settings, q, "x", {"type": "uri", "value": EX + "p"})
        assert out == f"SELECT * WHERE {{ ?s <{EX}p> ?xy }}"


@pytest.mark.parametrize(
    "value",
    [
        'a "b"',
        "back\\slash",
        "C:\\dir",
        "a\\1",
        "x\\",
        "line1\nline2",
        "cr\rhere",
        "tab\there",
        "dollar $1 and \\g<0>",
        "ünïcødé ✓",
    ],
)
class TestLiteralValuesArriveIntact:
    def test_simple_literal(self, settings, value):
        out = _substitute(settings, QUERY, "x", {"type": "literal", "value": value})
        assert _matches(out, Literal(value)) == 1

    def test_language_tagged_literal(self, settings, value):
        out = _substitute(
            settings, QUERY, "x", {"type": "literal", "value": value, "xml:lang": "fr"}
        )
        assert _matches(out, Literal(value, lang="fr")) == 1

    def test_typed_literal(self, settings, value):
        out = _substitute(
            settings,
            QUERY,
            "x",
            {"type": "literal", "value": value, "datatype": EX + "dt"},
        )
        assert _matches(out, Literal(value, datatype=URIRef(EX + "dt"))) == 1


class TestTerms:
    def test_language_tag_is_written(self, settings):
        out = _substitute(
            settings, QUERY, "x", {"type": "literal", "value": "chat", "xml:lang": "fr"}
        )
        assert out == 'SELECT * WHERE { ?s ?p "chat"@fr }'

    def test_datatype_is_written(self, settings):
        out = _substitute(
            settings,
            QUERY,
            "x",
            {"type": "literal", "value": "42", "datatype": str(XSD.integer)},
        )
        assert _matches(out, Literal("42", datatype=XSD.integer)) == 1

    def test_uri_term(self, settings):
        out = _substitute(settings, QUERY, "x", {"type": "uri", "value": EX + "a?b=c#d"})
        assert _matches(out, URIRef(EX + "a?b=c#d")) == 1

    @pytest.mark.parametrize("bad", [EX + "a b", EX + "a>b", EX + "a<b", EX + 'a"b', EX + "a{b", EX + "a|b", EX + "a^b", EX + "a`b", EX + "a\\b"])
    def test_uri_with_a_character_iriref_excludes_raises(self, settings, bad):
        with pytest.raises(ValueError):
            _substitute(settings, QUERY, "x", {"type": "uri", "value": bad})

    def test_bnode_raises_type_error(self, settings):
        with pytest.raises(TypeError):
            _substitute(settings, QUERY, "x", {"type": "bnode", "value": "b0"})
