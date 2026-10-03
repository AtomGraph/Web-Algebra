"""Stub HTTP plumbing for the unit suite (harness, not test cases).

The HTTP-backed operations talk to the network through ``urllib.request``
openers. Tests replace ``OpenerDirector.open`` with a ``StubWeb``, so every
client an operation builds (including the clients of operations nested
inside a ``ForEach``) is answered offline, and every request is recorded for
assertions on method, URL, headers and body.

A real opener raises ``urllib.error.HTTPError`` for a non-2xx answer (its
``HTTPErrorProcessor`` does), so the stub does the same: a handler returning a
non-2xx ``StubResponse`` makes ``open`` raise exactly what urllib would.
"""

from __future__ import annotations

import http.client
import io
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, List, Optional


class StubResponse:
    """A minimal stand-in for ``http.client.HTTPResponse``."""

    def __init__(
        self,
        status: int = 200,
        headers: Optional[dict] = None,
        body: bytes = b"",
        url: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        self.status = status
        self.code = status
        self.reason = reason or http.client.responses.get(status, "")
        self.msg = self.reason
        self.headers = http.client.HTTPMessage()
        for key, value in (headers or {}).items():
            self.headers[key] = value
        self._body = body
        self.url = url

    def read(self, *args) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self.status

    def geturl(self) -> Optional[str]:
        return self.url

    def info(self):
        return self.headers

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def getheaders(self):
        return list(self.headers.items())

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        return False


def request_header(request: urllib.request.Request, name: str) -> Optional[str]:
    """Case-insensitive header lookup (urllib capitalizes header names)."""
    for key, value in request.header_items():
        if key.lower() == name.lower():
            return value
    return None


def request_body_text(request: urllib.request.Request) -> str:
    data = request.data
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    if isinstance(data, str):
        return data
    try:
        return b"".join(data).decode("utf-8", errors="replace")
    except TypeError:
        return str(data)


def sparql_query_text(request: urllib.request.Request) -> Optional[str]:
    """The SPARQL query a request carries — by GET, by POST form, or as a
    direct ``application/sparql-query`` POST body — or None."""
    parsed = urllib.parse.urlparse(request.full_url)
    params = urllib.parse.parse_qs(parsed.query)
    if "query" in params:
        return params["query"][0]
    if request.get_method() == "POST":
        content_type = (request_header(request, "Content-Type") or "").lower()
        body = request_body_text(request)
        if "application/sparql-query" in content_type:
            return body
        if "application/x-www-form-urlencoded" in content_type:
            form = urllib.parse.parse_qs(body)
            if "query" in form:
                return form["query"][0]
    return None


_PROLOGUE = re.compile(
    r"^\s*(?:(?:PREFIX\s+[^\s:]*:\s*<[^>]*>|BASE\s+<[^>]*>)\s*)*", re.IGNORECASE
)


def query_form(query: str) -> str:
    """SELECT / CONSTRUCT / DESCRIBE / ASK — the first keyword after the
    prologue (comments are not handled; the harness does not need them)."""
    rest = _PROLOGUE.sub("", query, count=1)
    match = re.match(r"\s*([A-Za-z]+)", rest)
    return match.group(1).upper() if match else ""


EMPTY_SELECT = json.dumps({"head": {"vars": []}, "results": {"bindings": []}}).encode()


def empty_sparql_answer(request: urllib.request.Request) -> StubResponse:
    """An empty, well-formed answer of the query's own form."""
    form = query_form(sparql_query_text(request) or "")
    if form == "SELECT":
        return StubResponse(
            200, {"Content-Type": "application/sparql-results+json"}, EMPTY_SELECT
        )
    if form == "ASK":
        return StubResponse(
            200,
            {"Content-Type": "application/sparql-results+json"},
            json.dumps({"head": {}, "boolean": False}).encode(),
        )
    return StubResponse(200, {"Content-Type": "application/n-triples"}, b"")


def default_handler(request: urllib.request.Request) -> StubResponse:
    """HEAD: 200, no ETag. SPARQL query: an empty answer of its form.
    GET: an empty Turtle graph. Writes: 200, no Location."""
    method = request.get_method()
    if sparql_query_text(request) is not None:
        return empty_sparql_answer(request)
    if method == "HEAD":
        return StubResponse(200)
    if method == "GET":
        return StubResponse(200, {"Content-Type": "text/turtle"}, b"")
    return StubResponse(200)


class StubWeb:
    """Records every request and answers it with ``handler(request)``."""

    def __init__(self, handler: Optional[Callable] = None):
        self.handler: Callable = handler or default_handler
        self.requests: List[urllib.request.Request] = []

    def open(self, request, data=None, *args, **kwargs):
        if isinstance(request, str):
            request = urllib.request.Request(request, data=data)
        self.requests.append(request)
        response = self.handler(request)
        if response.url is None:
            response.url = request.full_url
        if not 200 <= response.status < 300:
            raise urllib.error.HTTPError(
                request.full_url,
                response.status,
                response.reason,
                response.headers,
                io.BytesIO(response._body),
            )
        return response

    def methods(self) -> List[str]:
        return [r.get_method() for r in self.requests]

    def with_method(self, method: str) -> List[urllib.request.Request]:
        return [r for r in self.requests if r.get_method() == method]

    def queries(self) -> List[str]:
        return [q for q in (sparql_query_text(r) for r in self.requests) if q]
