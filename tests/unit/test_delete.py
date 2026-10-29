"""Spec: formal-semantics.md "DELETE - remove a resource"
Abstract: URI → Result
Python:   def execute(self, url: URIRef) -> Result
- §4.4: returns a single-row Result (status, url); the shared write
  contract (url from Location, non-2xx → ValueError, If-Match via HEAD) is
  covered for POST, PUT, PATCH and DELETE in test_write_contract.py.
- §4.4: a resource that does not exist is answered 404, an error (§3.7).
- §3.6: a DELETE is a write to its URI; two iterations of one ForEach that
  delete, or delete and write, the same URI are an error.

HTTP is stubbed at the urllib boundary (tests/http_stub.py); no network.
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from tests.http_stub import StubResponse, default_handler
from web_algebra.operation import Operation

DOC = "http://example.org/doc"


def _delete(url):
    return {"@op": "DELETE", "args": {"url": url}}


class TestDELETEPure:
    def test_wrong_url_type_raises(self, settings):
        op = Operation.get("DELETE")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal(DOC))

    def test_url_is_the_removed_uri(self, settings, http_stub):
        # §4.4: url is the URI of the resource the write removed
        result = Operation.get("DELETE")(settings=settings).execute(URIRef(DOC))
        [row] = list(result)
        assert row["url"] == URIRef(DOC)
        assert [r.full_url for r in http_stub.with_method("DELETE")] == [DOC]

    def test_sends_no_body(self, settings, http_stub):
        # §4.4: DELETE takes a URI only, no graph or update
        Operation.get("DELETE")(settings=settings).execute(URIRef(DOC))
        [request] = http_stub.with_method("DELETE")
        assert not request.data


class TestDELETEMissing:
    def test_404_is_an_error(self, settings, http_stub):
        # §4.4/§3.7: a resource that does not exist is answered 404, a
        # non-2xx answer, so an error
        def handler(request):
            if request.get_method() in ("HEAD", "DELETE"):
                return StubResponse(404)
            return default_handler(request)

        http_stub.handler = handler
        with pytest.raises(ValueError):
            Operation.get("DELETE")(settings=settings).execute(URIRef(DOC))


class TestDELETEJson:
    def test_url_is_a_uri(self, settings, http_stub):
        # §4.4 JSON: url: URI
        result = Operation.process_json(settings, _delete({"@id": DOC}))
        [row] = list(result)
        assert row["url"] == URIRef(DOC)

    def test_a_string_url_is_a_type_error(self, settings, http_stub):
        # §2.2: a plain string is a literal, never a URI
        with pytest.raises(TypeError):
            Operation.process_json(settings, _delete(DOC))
        assert http_stub.with_method("DELETE") == []

    def test_missing_url_is_a_key_error(self, settings):
        # §3.7: missing required argument key → KeyError
        with pytest.raises(KeyError):
            Operation.process_json(settings, {"@op": "DELETE", "args": {}})


class TestDELETEInForEach:
    def test_two_iterations_deleting_the_same_uri_raise(self, settings, http_stub):
        # §3.6/§3.7: a DELETE is a write to its URI
        with pytest.raises(ValueError):
            Operation.process_json(
                settings,
                {"@op": "ForEach", "args": {"select": ["a", "b"], "operation": _delete({"@id": DOC})}},
            )

    def test_delete_and_put_of_the_same_uri_in_two_iterations_raise(self, settings, http_stub):
        # §3.6: the rule is stated on targets, not methods. Row 1 deletes DOC,
        # row 2 puts DOC, each iteration writing a distinct URI otherwise.
        rows = {
            "@op": "SELECT",
            "args": {
                "graph": {"@id": "http://example.org/x", "http://example.org/p": "v"},
                "query": f"SELECT ?del ?put {{ VALUES (?del ?put) {{ (<{DOC}> <{DOC}/b>) (<{DOC}/c> <{DOC}>) }} }}",
            },
        }
        operation = [
            _delete({"@op": "Value", "args": {"name": "del"}}),
            {
                "@op": "PUT",
                "args": {
                    "url": {"@op": "Value", "args": {"name": "put"}},
                    "data": {"@id": DOC, "http://example.org/p": "v"},
                },
            },
        ]
        with pytest.raises(ValueError):
            Operation.process_json(
                settings, {"@op": "ForEach", "args": {"select": rows, "operation": operation}}
            )

    def test_a_put_then_delete_in_one_iteration_is_allowed(self, settings, http_stub):
        # §3.6: within one iteration the sequence form orders the writes
        result = Operation.process_json(
            settings,
            {
                "@op": "ForEach",
                "args": {
                    "select": ["a"],
                    "operation": [
                        {"@op": "PUT", "args": {"url": {"@id": DOC}, "data": {"@id": DOC, "http://example.org/p": "v"}}},
                        _delete({"@id": DOC}),
                    ],
                },
            },
        )
        assert len(result) == 2
        assert [r.get_method() for r in http_stub.requests if r.get_method() != "HEAD"] == ["PUT", "DELETE"]
