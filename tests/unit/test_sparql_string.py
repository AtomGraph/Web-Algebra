"""Spec: formal-semantics.md §4.3 "SPARQLString — write a SPARQL query for an
endpoint from a natural-language question, via an LLM"
Abstract: URI × Literal × Maybe (Sequence Literal) × Maybe (Sequence Value)
          → Literal
Python:   def execute(self, endpoint: URIRef, question: Literal,
                      projection: Optional[List[Literal]] = None,
                      context: Optional[List[Any]] = None) -> Literal
JSON:     endpoint: URI · question: string-compatible Literal
          · projection: Maybe (array of string Literals)
          · context: Maybe (array of forms)
- Non-deterministic; external service call. Types are checked before any
  effect (§3.7), so the type contract is testable offline.
- An empty `context` value (a Result with no rows, an empty Graph) is a
  ValueError: the query cannot be written from it.
- The projection / parse retry contract needs the model call stubbed; there
  is no infrastructure seam for that, so those cases are skipped.

The model is made unreachable (a dummy key and a base URL that refuses
connections), so a test that wrongly reaches the model fails with a
connection error rather than a spec exception.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import XSD

from web_algebra.json_result import JSONResult
from web_algebra.operation import Operation

ENDPOINT = URIRef("http://example.org/sparql")
QUESTION = Literal("Which cities are in Denmark?")


@pytest.fixture(autouse=True)
def _unreachable_model(monkeypatch, http_stub):
    # harness: keep the operation constructible offline and the model out of
    # reach; HTTP to the endpoint is stubbed by http_stub
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:9/v1")


def _empty_result() -> JSONResult:
    return JSONResult.from_json({"head": {"vars": ["p"]}, "results": {"bindings": []}})


class TestSPARQLStringPure:
    def test_endpoint_must_be_uri(self, settings):
        op = Operation.get("SPARQLString")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("http://example.org/sparql"), QUESTION)

    @pytest.mark.parametrize(
        "question",
        [URIRef("http://example.org/q"), Literal(42, datatype=XSD.integer)],
        ids=["uri", "integer"],
    )
    def test_question_must_be_string_compatible(self, settings, question):
        # §4.3: question is a string-compatible Literal (§4.2)
        op = Operation.get("SPARQLString")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(ENDPOINT, question)

    @pytest.mark.parametrize(
        "projection",
        [[URIRef("http://example.org/x")], [Literal(1, datatype=XSD.integer)]],
        ids=["uri-item", "integer-item"],
    )
    def test_projection_items_must_be_string_literals(self, settings, projection):
        # §4.3: projection is an array of string Literals (variable names)
        op = Operation.get("SPARQLString")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(ENDPOINT, QUESTION, projection)

    def test_empty_result_context_raises_value_error(self, settings):
        # §4.3/§3.7: a context value that is a Result with no rows → ValueError
        op = Operation.get("SPARQLString")(settings=settings)
        with pytest.raises(ValueError):
            op.execute(ENDPOINT, QUESTION, None, [_empty_result()])

    def test_empty_graph_context_raises_value_error(self, settings):
        # §4.3/§3.7: a context value that is an empty Graph → ValueError
        op = Operation.get("SPARQLString")(settings=settings)
        with pytest.raises(ValueError):
            op.execute(ENDPOINT, QUESTION, None, [Graph()])


class TestSPARQLStringJson:
    def test_missing_endpoint_raises_key_error(self, settings):
        # §3.7: missing required argument → KeyError
        op = Operation.get("SPARQLString")(settings=settings)
        with pytest.raises(KeyError):
            op.execute_json({"question": "Which cities are in Denmark?"})

    def test_missing_question_raises_key_error(self, settings):
        op = Operation.get("SPARQLString")(settings=settings)
        with pytest.raises(KeyError):
            op.execute_json({"endpoint": {"@id": str(ENDPOINT)}})

    def test_plain_string_endpoint_raises_type_error(self, settings):
        # §2.2: a plain string is a string Literal, never a URI
        op = Operation.get("SPARQLString")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {"endpoint": "http://example.org/sparql", "question": "Which cities?"}
            )

    def test_uri_question_raises_type_error(self, settings):
        op = Operation.get("SPARQLString")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "endpoint": {"@id": str(ENDPOINT)},
                    "question": {"@id": "http://example.org/q"},
                }
            )

    def test_non_string_projection_item_raises_type_error(self, settings):
        op = Operation.get("SPARQLString")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "endpoint": {"@id": str(ENDPOINT)},
                    "question": "Which cities?",
                    "projection": ["city", 7],
                }
            )

    def test_empty_context_value_raises_value_error(self, settings):
        # §4.3: context forms are evaluated eagerly; an empty Result → ValueError
        op = Operation.get("SPARQLString")(settings=settings)
        with pytest.raises(ValueError):
            op.execute_json(
                {
                    "endpoint": {"@id": str(ENDPOINT)},
                    "question": "Which cities?",
                    "context": [_empty_result()],
                }
            )


class TestSPARQLStringModelContract:
    @pytest.mark.skip(
        reason="§4.3: result is a simple literal holding a parseable SPARQL 1.1 "
        "query; needs the model call stubbed, and there is no infrastructure "
        "seam for SPARQLString's model call outside the operation module"
    )
    def test_result_is_parseable_simple_literal(self, settings):
        pass

    @pytest.mark.skip(
        reason="§4.3: with projection the query is a SELECT projecting every "
        "named variable; needs a stubbed model (no infrastructure seam)"
    )
    def test_projection_is_honoured(self, settings):
        pass

    @pytest.mark.skip(
        reason="§4.3: an unparseable / wrongly-projected answer goes back to "
        "the model a bounded number of times, then ValueError; needs a "
        "stubbed model (no infrastructure seam)"
    )
    def test_retry_then_value_error(self, settings):
        pass
