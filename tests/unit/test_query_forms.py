"""Spec: formal-semantics.md §4.3.
- Each of SELECT, CONSTRUCT, DESCRIBE takes a query of its own form; a query
  that does not parse, or is of another form, raises ValueError before any
  network I/O.
- An `endpoint` is used as given, a query string of its own included; the
  query is sent as one more parameter of the SPARQL 1.1 Protocol request.
"""

from __future__ import annotations

import urllib.parse

import pytest

from tests.http_stub import request_body_text, request_header
from web_algebra.operation import Operation

EX = "http://example.org/"
DATA = {"@id": EX + "s", EX + "p": "o"}

QUERIES = {
    "SELECT": "SELECT * WHERE { ?s ?p ?o }",
    "CONSTRUCT": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }",
    "DESCRIBE": f"DESCRIBE <{EX}s>",
    "ASK": "ASK { ?s ?p ?o }",
}

WRONG = [
    (op, form)
    for op in ("SELECT", "CONSTRUCT", "DESCRIBE")
    for form in QUERIES
    if form != op
]


@pytest.mark.parametrize("op, form", WRONG)
def test_a_query_of_another_form_over_a_graph_raises(settings, op, form):
    with pytest.raises(ValueError):
        Operation.process_json(
            settings, {"@op": op, "args": {"graph": DATA, "query": QUERIES[form]}}
        )


@pytest.mark.parametrize("op, form", WRONG)
def test_a_query_of_another_form_over_an_endpoint_raises_before_io(
    settings, http_stub, op, form
):
    with pytest.raises(ValueError):
        Operation.process_json(
            settings,
            {"@op": op, "args": {"endpoint": {"@id": EX + "sparql"}, "query": QUERIES[form]}},
        )
    assert http_stub.requests == []


@pytest.mark.parametrize("op", ["SELECT", "CONSTRUCT", "DESCRIBE"])
def test_a_query_that_does_not_parse_raises_before_io(settings, http_stub, op):
    with pytest.raises(ValueError):
        Operation.process_json(
            settings,
            {"@op": op, "args": {"endpoint": {"@id": EX + "sparql"}, "query": "SELEKT nonsense"}},
        )
    assert http_stub.requests == []


@pytest.mark.parametrize("op", ["SELECT", "CONSTRUCT", "DESCRIBE"])
def test_a_query_of_its_own_form_over_a_graph_runs(settings, op):
    Operation.process_json(
        settings, {"@op": op, "args": {"graph": DATA, "query": QUERIES[op]}}
    )


def _params(request) -> dict:
    """Every parameter a SPARQL Protocol request carries, URL and form body."""
    parsed = urllib.parse.urlparse(request.full_url)
    params = urllib.parse.parse_qs(parsed.query)
    content_type = (request_header(request, "Content-Type") or "").lower()
    if "application/x-www-form-urlencoded" in content_type:
        for key, values in urllib.parse.parse_qs(request_body_text(request)).items():
            params.setdefault(key, []).extend(values)
    if "application/sparql-query" in content_type:
        params.setdefault("query", []).append(request_body_text(request))
    return params


@pytest.mark.parametrize("op", ["SELECT", "CONSTRUCT", "DESCRIBE"])
def test_endpoint_with_its_own_query_string(settings, http_stub, op):
    graph_uri = EX + "g"
    endpoint = EX + "sparql?default-graph-uri=" + urllib.parse.quote(graph_uri, safe="")
    Operation.process_json(
        settings, {"@op": op, "args": {"endpoint": {"@id": endpoint}, "query": QUERIES[op]}}
    )
    [request] = http_stub.requests
    assert urllib.parse.urlparse(request.full_url).path == "/sparql"
    params = _params(request)
    assert params["default-graph-uri"] == [graph_uri]
    assert params["query"] == [QUERIES[op]]
