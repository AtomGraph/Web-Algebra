"""Spec: formal-semantics.md Appendix A - ldh-CreateContainer and ldh-CreateItem
write the document at the parent's URI extended by `slug` and `/`; without a
`slug` the segment is a fresh lowercase UUID. The write is a `PUT`.
"""

from __future__ import annotations

import re

import pytest

UUID_SEGMENT = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)

PARENT = "https://localhost:4443/cities/"

# (operation, the argument naming the parent)
CREATES = [("ldh-CreateContainer", "parent"), ("ldh-CreateItem", "container")]


def _form(op: str, parent_arg: str, **args) -> dict:
    return {"@op": op, "args": {parent_arg: {"@id": PARENT}, "title": "Copenhagen", **args}}


@pytest.mark.parametrize("op, parent_arg", CREATES)
def test_without_a_slug_the_segment_is_a_lowercase_uuid(op, parent_arg, http_stub, run_op):
    run_op(_form(op, parent_arg))

    [put] = http_stub.with_method("PUT")
    assert put.full_url.startswith(PARENT)
    assert put.full_url.endswith("/")
    segment = put.full_url[len(PARENT):-1]
    assert UUID_SEGMENT.fullmatch(segment), segment


@pytest.mark.parametrize("op, parent_arg", CREATES)
def test_without_a_slug_the_title_does_not_name_the_document(op, parent_arg, http_stub, run_op):
    run_op(_form(op, parent_arg))
    run_op(_form(op, parent_arg))

    first, second = (put.full_url for put in http_stub.with_method("PUT"))
    assert first != second
    assert "Copenhagen" not in first


@pytest.mark.parametrize("op, parent_arg", CREATES)
def test_a_slug_is_the_segment(op, parent_arg, http_stub, run_op):
    run_op(_form(op, parent_arg, slug="copenhagen"))

    [put] = http_stub.with_method("PUT")
    assert put.full_url == PARENT + "copenhagen/"
