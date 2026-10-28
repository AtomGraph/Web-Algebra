"""Spec: formal-semantics.md §4.4 — the contract shared by the writes POST, PUT
and PATCH, and §3.7's error table.
- A write returns a single-row Result with variables `status` (xsd:integer
  HTTP status) and `url`: the response's Location when it has one, otherwise
  the request URI. A 303 answered to a write reports success (url = its
  Location, not dereferenced); any other 3xx is an error and is not followed.
- A response outside 2xx is an error (ValueError, not urllib's HTTPError);
  transport failures (no response) propagate unwrapped.
- If-Match: the entity tag is read with HEAD, sending the same Accept as the
  write, and sent as If-Match; a resource that does not exist, or has no tag,
  is written unconditionally.
- `Filter(Filter(PUT(…), 1), "url")` is the URI a write reports (§4.1).

HTTP is stubbed at the urllib boundary (tests/http_stub.py); no network.
"""

from __future__ import annotations

import hashlib
import urllib.error

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import XSD
from rdflib.query import Result

from tests.http_stub import StubResponse, default_handler, request_header
from web_algebra.operation import Operation

EX = "http://example.org/"
DOC = EX + "doc"

WRITES = ["POST", "PUT", "PATCH"]


def _graph() -> Graph:
    g = Graph()
    g.add((URIRef(DOC), URIRef(EX + "p"), Literal("v")))
    return g


def _write(method: str, settings, url: str = DOC):
    op = Operation.get(method)(settings=settings)
    if method == "PATCH":
        return op.execute(
            URIRef(url), Literal(f"INSERT DATA {{ <{DOC}> <{EX}p> \"v\" }}")
        )
    return op.execute(URIRef(url), _graph())


def _writes_answered(method: str, response_factory, head=None):
    """A handler answering `method` with `response_factory()` and HEAD with
    `head()` (default: 200, no ETag)."""

    def handler(request):
        m = request.get_method()
        if m == method:
            return response_factory()
        if m == "HEAD":
            return head() if head else StubResponse(200)
        return default_handler(request)

    return handler


def _single_row(result):
    assert isinstance(result, Result)
    rows = list(result)
    assert len(rows) == 1
    return rows[0]


@pytest.mark.parametrize("method", WRITES)
class TestWriteResult:
    def test_returns_single_row_result_with_status_and_url(
        self, method, settings, http_stub
    ):
        # §4.4: a single-row Result, variables status (xsd:integer) and url
        http_stub.handler = _writes_answered(method, lambda: StubResponse(200))
        row = _single_row(_write(method, settings))
        status = row["status"]
        assert isinstance(status, Literal)
        assert status.datatype == XSD.integer
        assert int(status) == 200
        assert str(row["url"]) == DOC

    def test_status_is_the_response_status(self, method, settings, http_stub):
        http_stub.handler = _writes_answered(method, lambda: StubResponse(204))
        row = _single_row(_write(method, settings))
        assert int(row["status"]) == 204

    def test_url_is_location_when_present(self, method, settings, http_stub):
        # §4.4: url is the response's Location when it has one, as when a
        # POST to a container creates a child
        child = EX + "container/child"
        http_stub.handler = _writes_answered(
            method, lambda: StubResponse(201, {"Location": child})
        )
        row = _single_row(_write(method, settings, EX + "container/"))
        assert str(row["url"]) == child

    def test_url_is_the_request_uri_without_location(
        self, method, settings, http_stub
    ):
        # §4.4: without Location, url is the request URI
        http_stub.handler = _writes_answered(method, lambda: StubResponse(200))
        row = _single_row(_write(method, settings))
        assert str(row["url"]) == DOC

    def test_relative_location(self, method, settings, http_stub):
        # §4.4: a relative Location is resolved against the request URI
        # (RFC 3986 §5)
        http_stub.handler = _writes_answered(
            method, lambda: StubResponse(201, {"Location": "child"})
        )
        row = _single_row(_write(method, settings, EX + "container/"))
        assert str(row["url"]) == EX + "container/child"

    def test_relative_location_with_dot_segments(self, method, settings, http_stub):
        # §4.4: a relative Location is resolved against the request URI per
        # RFC 3986 §5, dot segments included
        http_stub.handler = _writes_answered(
            method, lambda: StubResponse(201, {"Location": "../sibling/"})
        )
        row = _single_row(_write(method, settings, EX + "container/doc/"))
        assert str(row["url"]) == EX + "container/sibling/"


@pytest.mark.parametrize("method", WRITES)
@pytest.mark.parametrize("status", [301, 302, 307, 308])
class TestWriteRedirect:
    def test_a_redirect_answered_to_a_write_is_an_error(
        self, method, status, settings, http_wire
    ):
        # §4.4: a 3xx answered to a write is a non-2xx response - an error
        http_wire.handler = _writes_answered(
            method, lambda: StubResponse(status, {"Location": DOC + "/"})
        )
        with pytest.raises(ValueError):
            _write(method, settings)

    def test_a_redirect_answered_to_a_write_is_not_followed(
        self, method, status, settings, http_wire
    ):
        # §4.4: the body was written against the request URI; it is not resent
        # to the URI the redirect names
        http_wire.handler = _writes_answered(
            method, lambda: StubResponse(status, {"Location": DOC + "/"})
        )
        with pytest.raises(ValueError):
            _write(method, settings)
        assert all(r.full_url == DOC for r in http_wire.requests)
        assert len([r for r in http_wire.requests if r.get_method() not in ("HEAD", "GET")]) == 1


@pytest.mark.parametrize("method", WRITES)
class TestWriteSeeOther:
    def _see_other(self, method, http_wire, location):
        http_wire.handler = _writes_answered(
            method, lambda: StubResponse(303, {"Location": location})
        )

    def test_303_reports_success(self, method, settings, http_wire):
        # §4.4: a 303 See Other answered to a write reports success
        self._see_other(method, http_wire, EX + "result")
        row = _single_row(_write(method, settings))
        assert int(row["status"]) == 303

    def test_303_url_is_its_location(self, method, settings, http_wire):
        # §4.4: the url reported is the Location, resolved against the
        # request URI
        self._see_other(method, http_wire, "result/1")
        row = _single_row(_write(method, settings, EX + "container/"))
        assert str(row["url"]) == EX + "container/result/1"

    def test_303_location_is_not_dereferenced(self, method, settings, http_wire):
        # §4.4: the Location is reported, not dereferenced
        self._see_other(method, http_wire, EX + "result")
        _write(method, settings)
        assert all(r.full_url == DOC for r in http_wire.requests)
        assert [r.get_method() for r in http_wire.requests].count(method) == 1


class TestGetFollowsRedirects:
    def test_get_follows_a_redirect(self, settings, http_wire):
        # §4.4: a GET follows redirects
        moved = EX + "moved"

        def handler(request):
            if request.full_url == DOC:
                return StubResponse(308, {"Location": moved})
            return StubResponse(
                200,
                {"Content-Type": "application/n-triples"},
                f"<{moved}> <{EX}p> \"v\" .\n".encode(),
            )

        http_wire.handler = handler
        graph = Operation.get("GET")(settings=settings).execute(URIRef(DOC))
        assert (URIRef(moved), URIRef(EX + "p"), Literal("v")) in graph


@pytest.mark.parametrize("method", WRITES)
class TestWriteErrors:
    @pytest.mark.parametrize("status", [400, 403, 404, 409, 412, 428, 500])
    def test_non_2xx_raises_value_error_not_http_error(
        self, method, status, settings, http_stub
    ):
        # §4.4/§3.7: a write answered outside 2xx → ValueError; the
        # transport's HTTPError is not what surfaces
        http_stub.handler = _writes_answered(method, lambda: StubResponse(status))
        with pytest.raises(ValueError) as exc_info:
            _write(method, settings)
        assert not isinstance(exc_info.value, urllib.error.HTTPError)

    def test_transport_failure_propagates_unwrapped(self, method, settings, http_stub):
        # §3.7: no response → URLError, unwrapped
        def handler(request):
            if request.get_method() == method:
                raise urllib.error.URLError("connection refused")
            if request.get_method() == "HEAD":
                return StubResponse(404)
            return default_handler(request)

        http_stub.handler = handler
        with pytest.raises(urllib.error.URLError) as exc_info:
            _write(method, settings)
        assert not isinstance(exc_info.value, ValueError)


@pytest.mark.parametrize("method", WRITES)
class TestWriteIfMatch:
    def test_etag_from_head_is_sent_as_if_match(self, method, settings, http_stub):
        # §4.4: the entity tag is read with HEAD and sent as If-Match
        http_stub.handler = _writes_answered(
            method,
            lambda: StubResponse(200),
            head=lambda: StubResponse(200, {"ETag": '"abc123"'}),
        )
        _write(method, settings)
        writes = http_stub.with_method(method)
        assert len(writes) == 1
        assert request_header(writes[0], "If-Match") == '"abc123"'

    def test_head_precedes_write_on_the_same_uri_with_same_accept(
        self, method, settings, http_stub
    ):
        # §4.4: HEAD on the resource, with the same Accept as the write (the
        # tag names a negotiated variant), immediately before the write
        http_stub.handler = _writes_answered(
            method,
            lambda: StubResponse(200),
            head=lambda: StubResponse(200, {"ETag": '"abc123"'}),
        )
        _write(method, settings)
        methods = http_stub.methods()
        assert "HEAD" in methods
        head_index = methods.index("HEAD")
        write_index = methods.index(method)
        assert head_index < write_index
        head = http_stub.requests[head_index]
        write = http_stub.requests[write_index]
        assert head.full_url == write.full_url == DOC
        assert request_header(head, "Accept") == request_header(write, "Accept")

    def test_no_if_match_when_head_fails(self, method, settings, http_stub):
        # §4.4: a resource that does not exist is written unconditionally
        http_stub.handler = _writes_answered(
            method, lambda: StubResponse(201), head=lambda: StubResponse(404)
        )
        _write(method, settings)
        writes = http_stub.with_method(method)
        assert len(writes) == 1
        assert request_header(writes[0], "If-Match") is None

    def test_no_if_match_when_head_has_no_etag(self, method, settings, http_stub):
        # §4.4: a resource that has no tag is written unconditionally
        http_stub.handler = _writes_answered(
            method, lambda: StubResponse(200), head=lambda: StubResponse(200)
        )
        _write(method, settings)
        writes = http_stub.with_method(method)
        assert len(writes) == 1
        assert request_header(writes[0], "If-Match") is None

    def test_412_after_head_is_an_error(self, method, settings, http_stub):
        # §4.4: a write made by another client between HEAD and the write is
        # answered 412, an error like any other non-2xx answer
        http_stub.handler = _writes_answered(
            method,
            lambda: StubResponse(412),
            head=lambda: StubResponse(200, {"ETag": '"old"'}),
        )
        with pytest.raises(ValueError):
            _write(method, settings)


# Appendix A: the ldh-* updates "are subject to the same rules (§3.6, §4.4)".
# (operation, the HTTP method it writes with, its arguments, the URI written)
LDH_WRITES = {
    "ldh-AddFile": ("POST", lambda path: {"url": {"@id": DOC}, "file": str(path), "title": "t"}, DOC),
    "ldh-AddSelect": ("POST", lambda path: {"url": {"@id": DOC}, "query": "SELECT * { ?s ?p ?o }", "title": "t"}, DOC),
}
# ldh-CreateContainer and ldh-CreateItem quote no entity tag: they PUT with
# If-None-Match: * and only create (test_ldh_create_if_absent.py)


@pytest.mark.parametrize("op", sorted(LDH_WRITES))
class TestLdhWriteIfMatch:
    def _run(self, op, settings, http_stub, tmp_path):
        path = tmp_path / "upload.txt"
        path.write_bytes(b"bytes")
        _, args, _ = LDH_WRITES[op]
        writes = http_stub.handler
        sha1 = hashlib.sha1(b"bytes").hexdigest()

        def handler(request):
            # Appendix A: after an upload the document describes the file with
            # foaf:sha1, which is how ldh-AddFile finds the file's URI
            if request.get_method() == "GET" and request.full_url == DOC:
                return StubResponse(
                    200,
                    {"Content-Type": "application/n-triples"},
                    f'<{EX}uploads/{sha1}> <http://xmlns.com/foaf/0.1/sha1> "{sha1}" .\n'.encode(),
                )
            return writes(request)

        http_stub.handler = handler
        Operation.process_json(settings, {"@op": op, "args": args(path)})

    def test_etag_from_head_is_sent_as_if_match(self, op, settings, http_stub, tmp_path):
        # Appendix A, §4.4: the entity tag is read with HEAD, with the write's
        # Accept, on the URI written, and sent as If-Match
        method, _, url = LDH_WRITES[op]
        http_stub.handler = _writes_answered(
            method,
            lambda: StubResponse(200),
            head=lambda: StubResponse(200, {"ETag": '"abc123"'}),
        )
        self._run(op, settings, http_stub, tmp_path)
        [write] = http_stub.with_method(method)
        [head] = http_stub.with_method("HEAD")
        assert write.full_url == head.full_url == url
        assert request_header(write, "If-Match") == '"abc123"'
        assert request_header(head, "Accept") == request_header(write, "Accept")

    def test_no_if_match_when_head_fails(self, op, settings, http_stub, tmp_path):
        # Appendix A, §4.4: a resource that does not exist is written unconditionally
        method, _, _ = LDH_WRITES[op]
        http_stub.handler = _writes_answered(
            method, lambda: StubResponse(201), head=lambda: StubResponse(404)
        )
        self._run(op, settings, http_stub, tmp_path)
        [write] = http_stub.with_method(method)
        assert request_header(write, "If-Match") is None


class TestReportedUrlLookup:
    def test_filter_filter_put_url_is_the_reported_uri(self, settings, http_stub):
        # §4.4/§4.1: Filter(Filter(PUT(…), 1), "url") is the URI a write
        # reports
        result = Operation.process_json(
            settings,
            {
                "@op": "Filter",
                "args": {
                    "input": {
                        "@op": "Filter",
                        "args": {
                            "input": {
                                "@op": "PUT",
                                "args": {
                                    "url": {"@id": DOC},
                                    "data": {"@id": DOC, EX + "p": "v"},
                                },
                            },
                            "expression": 1,
                        },
                    },
                    "expression": "url",
                },
            },
        )
        assert result == URIRef(DOC)

    def test_for_each_over_write_makes_the_row_the_focus(self, settings, http_stub):
        # §4.4: ForEach(select: PUT(…), operation: GET(url: Value(url)))
        # dereferences the written document
        def handler(request):
            if request.get_method() == "GET":
                return StubResponse(
                    200,
                    {"Content-Type": "text/turtle"},
                    f"<{DOC}> <{EX}p> \"v\" .".encode(),
                )
            return default_handler(request)

        http_stub.handler = handler
        result = Operation.process_json(
            settings,
            {
                "@op": "ForEach",
                "args": {
                    "select": {
                        "@op": "PUT",
                        "args": {
                            "url": {"@id": DOC},
                            "data": {"@id": DOC, EX + "p": "v"},
                        },
                    },
                    "operation": {
                        "@op": "GET",
                        "args": {"url": {"@op": "Value", "args": {"name": "url"}}},
                    },
                },
            },
        )
        assert len(result) == 1
        assert isinstance(result[0], Graph)
        assert [r.full_url for r in http_stub.with_method("GET")] == [DOC]
