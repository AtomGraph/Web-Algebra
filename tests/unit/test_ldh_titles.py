"""Spec: formal-semantics.md Appendix A - the ldh-* `title` and `description`
arguments are Literals; per §4.2 a string-compatible Literal includes a
language-tagged one. Such a title or description is written as the
document's or resource's `dct:title` / `dct:description`, keeping its tag.

The language-tagged value comes from a SPARQL result, as it would in a plan:
a SELECT over a graph whose label is tagged `@fr`.
"""

from __future__ import annotations

import pytest

from tests.http_stub import request_body_text
from web_algebra.operation import Operation

EX = "https://example.org/"
DOC = EX + "doc/"
LABEL = {"@op": "Value", "args": {"name": "label"}}


def _over_a_french_label(settings, operation):
    """Run `operation` with the focus on a row whose ?label is "Copenhague"@fr."""
    return Operation.process_json(
        settings,
        {
            "@op": "ForEach",
            "args": {
                "select": {
                    "@op": "SELECT",
                    "args": {
                        "graph": {"@id": EX + "city", "http://www.w3.org/2000/01/rdf-schema#label": {"@value": "Copenhague", "@language": "fr"}},
                        "query": "SELECT ?label WHERE { ?city ?p ?label }",
                    },
                },
                "operation": operation,
            },
        },
    )


def _written(http_stub) -> str:
    return "\n".join(request_body_text(r) for r in http_stub.requests if r.get_method() in ("POST", "PUT"))


OPERATIONS = {
    "ldh-AddSelect": {"url": {"@id": DOC}, "query": "SELECT * { ?s ?p ?o }", "title": LABEL, "description": LABEL},
    "ldh-AddConstruct": {"url": {"@id": DOC}, "query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }", "title": LABEL, "description": LABEL},
    "ldh-AddView": {"url": {"@id": DOC}, "query": {"@id": DOC + "#q"}, "title": LABEL, "description": LABEL},
    "ldh-AddResultSetChart": {"url": {"@id": DOC}, "query": {"@id": DOC + "#q"}, "title": LABEL, "description": LABEL,
                              "chart_type": {"@id": "https://w3id.org/atomgraph/client#BarChart"},
                              "category_var_name": "a", "series_var_name": "b"},
    "ldh-AddGenericService": {"url": {"@id": DOC}, "endpoint": {"@id": EX + "sparql"}, "title": LABEL, "description": LABEL},
    "ldh-AddObjectBlock": {"url": {"@id": DOC}, "value": {"@id": EX + "thing"}, "title": LABEL, "description": LABEL},
    "ldh-AddXHTMLBlock": {"url": {"@id": DOC}, "value": '<div xmlns="http://www.w3.org/1999/xhtml">x</div>', "title": LABEL, "description": LABEL},
    "ldh-CreateContainer": {"parent": {"@id": EX}, "title": LABEL, "slug": "c", "description": LABEL},
    "ldh-CreateItem": {"container": {"@id": EX}, "title": LABEL, "slug": "i"},
}


@pytest.mark.parametrize("op", sorted(OPERATIONS))
def test_a_language_tagged_title_is_accepted_and_keeps_its_tag(settings, http_stub, op):
    _over_a_french_label(settings, {"@op": op, "args": OPERATIONS[op]})
    written = _written(http_stub)
    assert '<http://purl.org/dc/terms/title> "Copenhague"@fr' in written


@pytest.mark.parametrize("op", sorted(o for o, args in OPERATIONS.items() if "description" in args))
def test_a_language_tagged_description_keeps_its_tag(settings, http_stub, op):
    _over_a_french_label(settings, {"@op": op, "args": OPERATIONS[op]})
    assert '<http://purl.org/dc/terms/description> "Copenhague"@fr' in _written(http_stub)
