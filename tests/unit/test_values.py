"""Spec: formal-semantics.md "Values - Append a VALUES data block to a SPARQL query"
Abstract: Literal × Result × Maybe (Sequence Literal) → Literal
Python:   def execute(self, query: Literal, data: Result, vars: Optional[List[str]] = None) -> Literal

Values renders a trailing SPARQL VALUES block from a result set and appends it to a
query. Tests build a Result with rdflib's Graph.query and assert on the produced
query string. ORDER BY is used wherever row order is asserted, since SPARQL is
otherwise unordered.
"""

from __future__ import annotations

import pytest
from rdflib import BNode, Graph, Literal, URIRef

from web_algebra.operation import Operation

EX_A = "http://ex/a"
EX_B = "http://ex/b"
EX_P = "http://ex/p"
EX_Q = "http://ex/q"


def _op(settings):
    return Operation.get("Values")(settings=settings)


def _one_var_two_rows():
    g = Graph()
    g.add((URIRef(EX_A), URIRef(EX_P), Literal("v1")))
    g.add((URIRef(EX_B), URIRef(EX_P), Literal("v2")))
    return g.query(f"SELECT ?s WHERE {{ ?s <{EX_P}> ?o }} ORDER BY ?s")


def _two_var_two_rows():
    g = Graph()
    g.add((URIRef(EX_A), URIRef(EX_P), Literal("v1")))
    g.add((URIRef(EX_B), URIRef(EX_P), Literal("v2")))
    return g.query(f"SELECT ?s ?o WHERE {{ ?s <{EX_P}> ?o }} ORDER BY ?s")


def _ragged_two_rows():
    # row a has ?x via the OPTIONAL; row b does not -> UNDEF
    g = Graph()
    g.add((URIRef(EX_A), URIRef(EX_P), Literal("v1")))
    g.add((URIRef(EX_A), URIRef(EX_Q), Literal("x1")))
    g.add((URIRef(EX_B), URIRef(EX_P), Literal("v2")))
    return g.query(
        f"SELECT ?s ?x WHERE {{ ?s <{EX_P}> ?o . OPTIONAL {{ ?s <{EX_Q}> ?x }} }} ORDER BY ?s"
    )


def _empty():
    g = Graph()
    return g.query(f"SELECT ?s WHERE {{ ?s <{EX_P}> ?o }}")


def _bnode_value():
    g = Graph()
    g.add((URIRef(EX_A), URIRef(EX_P), BNode("b1")))
    return g.query(f"SELECT ?o WHERE {{ <{EX_A}> <{EX_P}> ?o }}")


class TestValuesPure:
    def test_returns_literal(self, settings):
        result = _op(settings).execute(Literal("DESCRIBE ?s WHERE { ?s ?p ?o }"), _one_var_two_rows())
        assert isinstance(result, Literal)

    def test_single_var_short_form(self, settings):
        q = "DESCRIBE ?s WHERE { ?s ?p ?o }"
        result = str(_op(settings).execute(Literal(q), _one_var_two_rows()))
        assert result.startswith(q + " ")
        assert result.endswith(f"VALUES ?s {{ <{EX_A}> <{EX_B}> }}")

    def test_multi_var_long_form(self, settings):
        result = str(_op(settings).execute(Literal("SELECT * WHERE { ?s ?p ?o }"), _two_var_two_rows()))
        assert "VALUES (?s ?o) {" in result
        assert f'( <{EX_A}> "v1" )' in result
        assert f'( <{EX_B}> "v2" )' in result

    def test_unbound_cell_becomes_undef(self, settings):
        result = str(_op(settings).execute(Literal("SELECT * WHERE { ?s ?p ?o }"), _ragged_two_rows()))
        assert "VALUES (?s ?x) {" in result
        assert f'( <{EX_A}> "x1" )' in result
        assert f"( <{EX_B}> UNDEF )" in result

    def test_empty_result_renders_empty_block(self, settings):
        result = str(_op(settings).execute(Literal("DESCRIBE ?s WHERE { ?s ?p ?o }"), _empty()))
        assert result.endswith("VALUES ?s {  }")

    def test_vars_override_selects_and_orders_columns(self, settings):
        result = str(
            _op(settings).execute(Literal("SELECT * WHERE { ?s ?p ?o }"), _two_var_two_rows(), ["o", "s"])
        )
        assert "VALUES (?o ?s) {" in result
        assert f'( "v1" <{EX_A}> )' in result

    def test_bnode_value_raises(self, settings):
        # Blank nodes are not permitted in a SPARQL VALUES data block.
        with pytest.raises(ValueError):
            _op(settings).execute(Literal("SELECT * WHERE { ?s ?p ?o }"), _bnode_value())

    def test_literal_with_quote_is_escaped(self, settings):
        # The whole point over Concat: a literal containing a quote must be escaped.
        g = Graph()
        g.add((URIRef(EX_A), URIRef(EX_P), Literal('a"b')))
        data = g.query(f"SELECT ?o WHERE {{ ?s <{EX_P}> ?o }}")
        result = str(_op(settings).execute(Literal("SELECT * WHERE { ?o ?p ?x }"), data))
        assert r"\"" in result  # the embedded quote is backslash-escaped

    def test_wrong_query_type_raises(self, settings):
        with pytest.raises(TypeError):
            _op(settings).execute(URIRef("not-a-query"), _one_var_two_rows())

    def test_wrong_data_type_raises(self, settings):
        with pytest.raises(TypeError):
            _op(settings).execute(Literal("SELECT * WHERE { ?s ?p ?o }"), [{"s": URIRef(EX_A)}])


class TestValuesJson:
    @pytest.mark.skip(
        reason="execute_json resolves `data` from a nested SELECT, which requires a live endpoint (network-marked)"
    )
    def test_json_dispatch(self, settings):
        pass
