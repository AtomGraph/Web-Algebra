"""Spec: formal-semantics.md Appendix A (ldh-* family), §4.4.
- `fragment` names the created resource `url#fragment`, given with or without
  the leading `#`.
- `ldh-List` returns a Result with one row per child, variables `child` and
  `thing`, so it composes with ForEach like any Result.
- `ldh-AddFile`'s `url` is the uploaded file's URI: the resource the document
  describes after the upload with `foaf:sha1` equal to the hex SHA-1 of the
  bytes; a document that does not describe the upload after a 2xx raises
  ValueError.
"""

from __future__ import annotations

import hashlib
import json

import pytest
from rdflib import URIRef
from rdflib.query import Result

from tests.http_stub import StubResponse, default_handler, request_body_text, sparql_query_text
from web_algebra.operation import Operation

EX = "https://example.org/"
DOC = EX + "app/doc/"
FOAF_SHA1 = "http://xmlns.com/foaf/0.1/sha1"


# --- fragment


@pytest.mark.parametrize("fragment", ["q", "#q"])
@pytest.mark.parametrize(
    "op, args",
    [
        ("ldh-AddSelect", {"query": "SELECT * { ?s ?p ?o }", "title": "t"}),
        ("ldh-AddConstruct", {"query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }", "title": "t"}),
        ("ldh-AddObjectBlock", {"value": {"@id": EX + "thing"}}),
    ],
)
def test_fragment_with_or_without_hash_names_url_hash_fragment(
    settings, http_stub, op, args, fragment
):
    Operation.process_json(
        settings,
        {"@op": op, "args": {"url": {"@id": DOC}, "fragment": fragment, **args}},
    )
    body = "\n".join(request_body_text(r) for r in http_stub.with_method("POST"))
    assert f"<{DOC}#q>" in body
    assert "##" not in body


# --- ldh-List


def _children_answer(request):
    if sparql_query_text(request) is not None:
        rows = [
            {"child": {"type": "uri", "value": EX + "c/one/"}},
            {"child": {"type": "uri", "value": EX + "c/two/"}, "thing": {"type": "uri", "value": EX + "c/two/#this"}},
        ]
        return StubResponse(
            200,
            {"Content-Type": "application/sparql-results+json"},
            json.dumps({"head": {"vars": ["child", "thing"]}, "results": {"bindings": rows}}).encode(),
        )
    return default_handler(request)


LIST = {"@op": "ldh-List", "args": {"url": {"@id": EX + "c/"}, "endpoint": {"@id": EX + "sparql"}}}


def test_ldh_list_returns_a_result(settings, http_stub):
    http_stub.handler = _children_answer
    result = Operation.process_json(settings, LIST)
    assert isinstance(result, Result)
    assert {str(v) for v in result.vars} >= {"child", "thing"}
    assert [str(row["child"]) for row in result] == [EX + "c/one/", EX + "c/two/"]


def test_for_each_over_ldh_list(settings, http_stub):
    http_stub.handler = _children_answer
    children = Operation.process_json(
        settings,
        {"@op": "ForEach", "args": {"select": LIST, "operation": {"@op": "Value", "args": {"name": "child"}}}},
    )
    assert children == [URIRef(EX + "c/one/"), URIRef(EX + "c/two/")]


# --- ldh-AddFile


def _upload(tmp_path, data=b"file bytes"):
    path = tmp_path / "upload.txt"
    path.write_bytes(data)
    return path, hashlib.sha1(data).hexdigest()


def _document_describing(sha1, file_uri):
    triples = (
        f'<{file_uri}> <{FOAF_SHA1}> "{sha1}" .\n'
        f'<{file_uri}> <http://purl.org/dc/terms/title> "t" .\n'
        f'<{DOC}> <http://purl.org/dc/terms/title> "doc" .\n'
    )

    def handler(request):
        if request.get_method() == "GET" and request.full_url == DOC:
            return StubResponse(200, {"Content-Type": "application/n-triples"}, triples.encode())
        if request.get_method() == "POST":
            return StubResponse(200)
        return default_handler(request)

    return handler


def _add_file(settings, path):
    return Operation.process_json(
        settings, {"@op": "ldh-AddFile", "args": {"url": {"@id": DOC}, "file": str(path), "title": "t"}}
    )


def test_add_file_url_is_the_described_upload_under_an_app_base_with_a_path(
    settings, http_stub, tmp_path
):
    path, sha1 = _upload(tmp_path)
    file_uri = EX + "app/uploads/" + sha1
    http_stub.handler = _document_describing(sha1, file_uri)
    result = _add_file(settings, path)
    assert str(next(iter(result))["url"]) == file_uri


def test_add_file_url_is_the_described_upload_at_the_root(settings, http_stub, tmp_path):
    path, sha1 = _upload(tmp_path)
    file_uri = EX + "uploads/" + sha1
    http_stub.handler = _document_describing(sha1, file_uri)
    result = _add_file(settings, path)
    assert str(next(iter(result))["url"]) == file_uri


def test_add_file_raises_when_the_document_does_not_describe_the_upload(
    settings, http_stub, tmp_path
):
    path, _ = _upload(tmp_path)
    http_stub.handler = _document_describing("0" * 40, EX + "uploads/other")
    with pytest.raises(ValueError):
        _add_file(settings, path)
