"""Spec: formal-semantics.md "PATCH - Update RDF data via HTTP PATCH with SPARQL Update"
Abstract: URI × Literal → Result
Python:   def execute(self, url: URIRef, update: Literal) -> Result
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestPATCHPure:
    def test_wrong_url_type_raises(self, settings):
        op = Operation.get("PATCH")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("http://example.org/x"), Literal("DELETE WHERE { ?s ?p ?o }"))

    def test_wrong_update_type_raises(self, settings):
        op = Operation.get("PATCH")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("http://example.org/x"), URIRef("not-a-literal"))


@pytest.mark.network
class TestPATCHLive:
    @pytest.mark.skip(reason="No safe public PATCH endpoint")
    def test_returns_result(self, settings):
        pass


class TestPATCHJson:
    @pytest.mark.skip(reason="UNCLEAR(spec): PATCH JSON arg shape not exemplified by existing fixtures (presumed `{url, update}`)")
    def test_json_dispatch(self, settings):
        pass
