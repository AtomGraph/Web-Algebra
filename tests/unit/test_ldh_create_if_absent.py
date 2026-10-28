"""Spec: formal-semantics.md Appendix A, ldh-CreateContainer and ldh-CreateItem:
they only create. The PUT carries `If-None-Match: *` and no `If-Match`, so a
document already at the URI is refused 412 and left as it is; that is the
operation's error unless `if_absent` is true, when the existing document is
the result. `PUT` still replaces, quoting the document's entity tag (§4.4).

Checked offline: the stub tags every resource, so a create that read the tag
and quoted it - which would let it replace the document - shows.
"""

from __future__ import annotations

import pytest
from rdflib import URIRef

from tests.http_stub import StubResponse, request_header
from web_algebra.exceptions import WriteRefusedError
from web_algebra.operation import Operation, OperationKind

EX = "https://example.org/"

CREATES = [
    ("ldh-CreateContainer", {"parent": {"@id": EX}}),
    ("ldh-CreateItem", {"container": {"@id": EX}}),
]


def existing(request):
    """A server where every document exists: tagged, and a create is refused."""
    if request.get_method() == "HEAD":
        return StubResponse(200, {"ETag": '"v1"'})
    if request_header(request, "If-None-Match") == "*":
        return StubResponse(412)
    return StubResponse(204)


def absent(request):
    """A server where no document exists yet."""
    if request.get_method() == "HEAD":
        return StubResponse(404)
    return StubResponse(201)


def run(settings, op, args, **extra):
    return Operation.process_json(settings, {"@op": op, "args": {**args, "title": "T", "slug": "t", **extra}})


@pytest.mark.parametrize("op, args", CREATES)
def test_a_create_says_it_creates_and_quotes_no_state(settings, http_stub, op, args):
    http_stub.handler = absent
    result = run(settings, op, args)

    assert http_stub.methods() == ["PUT"], "a create reads no entity tag first"
    put = http_stub.requests[0]
    assert request_header(put, "If-None-Match") == "*"
    assert request_header(put, "If-Match") is None
    assert result.bindings[0]["url"] == URIRef(EX + "t/")
    assert int(result.bindings[0]["status"]) == 201


@pytest.mark.parametrize("op, args", CREATES)
def test_a_create_over_an_existing_document_fails(settings, http_stub, op, args):
    http_stub.handler = existing
    with pytest.raises(WriteRefusedError) as refused:
        run(settings, op, args)

    assert refused.value.status == 412
    assert "already exists" in refused.value.reason
    assert http_stub.methods() == ["PUT"], "nothing but the refused create was sent"


@pytest.mark.parametrize("op, args", CREATES)
def test_if_absent_accepts_an_existing_document(settings, http_stub, op, args):
    http_stub.handler = existing
    result = run(settings, op, args, if_absent=True)

    assert http_stub.methods() == ["PUT"], "the existing document is not written to"
    assert result.bindings[0]["url"] == URIRef(EX + "t/")
    assert int(result.bindings[0]["status"]) == 412


@pytest.mark.parametrize("op, args", CREATES)
def test_if_absent_creates_a_document_that_is_not_there(settings, http_stub, op, args):
    http_stub.handler = absent
    result = run(settings, op, args, if_absent=True)

    assert int(result.bindings[0]["status"]) == 201


@pytest.mark.parametrize("op, args", CREATES)
def test_if_absent_still_fails_on_any_other_refusal(settings, http_stub, op, args):
    http_stub.handler = lambda request: StubResponse(403)
    with pytest.raises(WriteRefusedError) as refused:
        run(settings, op, args, if_absent=True)

    assert refused.value.status == 403


@pytest.mark.parametrize("op, args", CREATES)
def test_if_absent_is_a_boolean(settings, http_stub, op, args):
    http_stub.handler = absent
    with pytest.raises(TypeError):
        run(settings, op, args, if_absent="sometimes")


def test_put_still_replaces_quoting_the_documents_state(settings, http_stub):
    http_stub.handler = existing
    Operation.process_json(settings, {"@op": "PUT", "args": {"url": {"@id": EX + "t/"}, "data": {"@id": EX + "t/", "http://purl.org/dc/terms/title": "T"}}})

    assert http_stub.methods() == ["HEAD", "PUT"]
    put = http_stub.requests[1]
    assert request_header(put, "If-Match") == '"v1"'
    assert request_header(put, "If-None-Match") is None


def test_a_foreach_may_make_sure_of_the_same_document_on_every_iteration(settings, http_stub):
    # an existing document if_absent accepts was not written, so the iteration
    # gate (§3.6), which refuses a URL another iteration wrote, does not count it
    http_stub.handler = existing
    Operation.process_json(settings, {
        "@op": "ForEach",
        "args": {
            "select": ["first", "second"],
            "operation": {"@op": "ldh-CreateContainer", "args": {"parent": {"@id": EX}, "title": "T", "slug": "t", "if_absent": True}},
        },
    })

    assert http_stub.methods() == ["PUT", "PUT"]


@pytest.mark.parametrize("op", ["ldh-CreateContainer", "ldh-CreateItem"])
def test_a_create_removes_nothing(op):
    assert Operation.get(op).kind is OperationKind.WRITE
    schema = Operation.get(op).inputSchema()
    assert "if_absent" in schema["properties"]
    assert "if_absent" not in schema.get("required", [])
