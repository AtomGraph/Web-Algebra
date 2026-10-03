"""Spec: formal-semantics.md Appendix A "ldh-AddConstruct" (informative)
JSON args: url: URI · query: Literal · title: Literal
           · description/fragment: Maybe Literal · service: Maybe URI
Python:   def execute(self, url: URIRef, query: Literal, title: Literal, description: Literal = None,
                      fragment: Literal = None, service: URIRef = None) -> Result
- Records a stored query (`sp:Construct`) in the document at `url`.
- An update operation: returns the single-row Result of §4.4 (status, url)
  and is subject to the same rules (§3.6, §4.4) — a non-2xx answer to its
  write is a ValueError.
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
from rdflib.query import Result

from tests.http_stub import StubResponse, default_handler, request_body_text
from web_algebra.operation import Operation

DOC = "https://example.org/doc/"
QUERY = "CONSTRUCT WHERE { ?s ?p ?o }"


class TestLDHAddConstructPure:
    def test_wrong_url_type_raises(self, settings):
        op = Operation.get("ldh-AddConstruct")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                Literal("not-a-uri"),
                Literal(QUERY),
                Literal("title"),
            )

    def test_wrong_query_type_raises(self, settings):
        op = Operation.get("ldh-AddConstruct")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                URIRef("https://example.org/"),
                URIRef("not-a-literal"),
                Literal("title"),
            )


class TestLDHAddConstructStubbed:
    def _run(self, settings):
        op = Operation.get("ldh-AddConstruct")(settings=settings)
        return op.execute_json(
            {"url": {"@id": DOC}, "query": QUERY, "title": "Stored query"}
        )

    def test_returns_single_row_write_result(self, settings, http_stub):
        # Appendix A: update operations return the single-row Result of §4.4
        result = self._run(settings)
        assert isinstance(result, Result)
        rows = list(result)
        assert len(rows) == 1
        assert rows[0]["status"].datatype == XSD.integer
        assert 200 <= int(rows[0]["status"]) < 300
        assert rows[0]["url"] is not None

    def test_records_a_stored_construct(self, settings, http_stub):
        # Appendix A: records an sp:Construct in the document
        self._run(settings)
        bodies = [
            request_body_text(r)
            for r in http_stub.requests
            if r.get_method() not in ("GET", "HEAD")
        ]
        assert bodies, "no write was made"
        assert any("Construct" in body for body in bodies)

    def test_non_2xx_write_raises_value_error(self, settings, http_stub):
        # Appendix A / §4.4 / §3.7: a write answered outside 2xx → ValueError
        def handler(request):
            if request.get_method() in ("POST", "PUT", "PATCH"):
                return StubResponse(403)
            return default_handler(request)

        http_stub.handler = handler
        with pytest.raises(ValueError):
            self._run(settings)


@pytest.mark.ldh
class TestLDHAddConstructLive:
    @pytest.mark.skip(reason="Live LinkedDataHub run; covered by integration LDH composition fixture instead.")
    def test_basic(self, settings_with_auth):
        pass
