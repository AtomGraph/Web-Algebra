"""Spec: formal-semantics.md §4.6 "Schema operations" — the optional
`bindings` argument shared by ExtractClasses, ExtractDatatypeProperties,
ExtractObjectProperties and ExtractOntology.
Abstract: URI × Maybe Result → Graph
Python:   def execute(self, endpoint: URIRef,
                      bindings: Optional[Result] = None) -> Graph
JSON:     endpoint: URI · bindings: Maybe Result
- Without `bindings` an extraction describes the whole endpoint.
- With `bindings` it describes only the subjects in the result's `subject`
  column, put into the extraction query as a VALUES block.
- `bindings` without the variable `subject`, or with no rows → ValueError;
  a non-Result → TypeError (before any effect, §3.7).

The endpoint is stubbed at the urllib boundary (tests/http_stub.py) and
answers every query with an empty result of the query's form.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, URIRef

from web_algebra.json_result import JSONResult
from web_algebra.operation import Operation

EX = "http://example.org/"
ENDPOINT = EX + "sparql"
S1, S2 = EX + "s1", EX + "s2"

EXTRACTIONS = [
    "ExtractClasses",
    "ExtractDatatypeProperties",
    "ExtractObjectProperties",
    "ExtractOntology",
]


def _subjects(*iris: str, var: str = "subject") -> JSONResult:
    return JSONResult.from_json(
        {
            "head": {"vars": [var]},
            "results": {
                "bindings": [{var: {"type": "uri", "value": iri}} for iri in iris]
            },
        }
    )


def _assert_values_block(queries: list) -> None:
    scoped = [
        q for q in queries if "VALUES" in q.upper() and f"<{S1}>" in q and f"<{S2}>" in q
    ]
    assert scoped, f"no query carries a VALUES block of the subjects: {queries!r}"


@pytest.mark.parametrize("name", EXTRACTIONS)
class TestExtractionWithBindings:
    def test_without_bindings_returns_graph(self, name, settings, http_stub):
        # §4.6: without bindings, the whole endpoint is described
        op = Operation.get(name)(settings=settings)
        result = op.execute(URIRef(ENDPOINT))
        assert isinstance(result, Graph)
        assert http_stub.queries()

    def test_subjects_appear_as_values_block(self, name, settings, http_stub):
        # §4.6: the subjects are put into the extraction query as VALUES
        op = Operation.get(name)(settings=settings)
        result = op.execute(URIRef(ENDPOINT), _subjects(S1, S2))
        assert isinstance(result, Graph)
        _assert_values_block(http_stub.queries())

    def test_json_subjects_appear_as_values_block(self, name, settings, http_stub):
        op = Operation.get(name)(settings=settings)
        result = op.execute_json(
            {"endpoint": {"@id": ENDPOINT}, "bindings": _subjects(S1, S2)}
        )
        assert isinstance(result, Graph)
        _assert_values_block(http_stub.queries())

    def test_other_columns_are_allowed(self, name, settings, http_stub):
        # §4.6: only the `subject` column is read
        table = JSONResult.from_json(
            {
                "head": {"vars": ["subject", "label"]},
                "results": {
                    "bindings": [
                        {
                            "subject": {"type": "uri", "value": iri},
                            "label": {"type": "literal", "value": "x"},
                        }
                        for iri in (S1, S2)
                    ]
                },
            }
        )
        op = Operation.get(name)(settings=settings)
        assert isinstance(op.execute(URIRef(ENDPOINT), table), Graph)
        _assert_values_block(http_stub.queries())

    def test_bindings_without_subject_variable_raise_value_error(
        self, name, settings, http_stub
    ):
        # §4.6/§3.7: bindings that do not bind `subject` → ValueError
        op = Operation.get(name)(settings=settings)
        with pytest.raises(ValueError):
            op.execute(URIRef(ENDPOINT), _subjects(S1, var="s"))

    def test_json_bindings_without_subject_variable_raise_value_error(
        self, name, settings, http_stub
    ):
        op = Operation.get(name)(settings=settings)
        with pytest.raises(ValueError):
            op.execute_json(
                {"endpoint": {"@id": ENDPOINT}, "bindings": _subjects(S1, var="s")}
            )

    def test_bindings_with_no_rows_raise_value_error(self, name, settings, http_stub):
        # §4.6/§3.7: bindings with no rows → ValueError
        op = Operation.get(name)(settings=settings)
        with pytest.raises(ValueError):
            op.execute(URIRef(ENDPOINT), _subjects())

    def test_json_bindings_with_no_rows_raise_value_error(
        self, name, settings, http_stub
    ):
        op = Operation.get(name)(settings=settings)
        with pytest.raises(ValueError):
            op.execute_json({"endpoint": {"@id": ENDPOINT}, "bindings": _subjects()})

    @pytest.mark.parametrize(
        "bindings",
        [Literal("not a result"), URIRef(EX + "x"), [URIRef(S1)]],
        ids=["literal", "uri", "list"],
    )
    def test_non_result_bindings_raise_type_error(
        self, name, bindings, settings, http_stub
    ):
        # §4.6: a non-Result raises TypeError — before any effect (§3.7)
        op = Operation.get(name)(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef(ENDPOINT), bindings)
        assert http_stub.requests == []

    def test_json_non_result_bindings_raise_type_error(
        self, name, settings, http_stub
    ):
        op = Operation.get(name)(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json({"endpoint": {"@id": ENDPOINT}, "bindings": "not a result"})
        assert http_stub.requests == []
