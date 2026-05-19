"""Spec: formal-semantics.md "ldh-List - List LinkedDataHub resources"
Abstract: URI × URI → List[Dict]
Python:   def execute(self, url: URIRef, endpoint: URIRef) -> list[dict]
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestLDHListPure:
    def test_wrong_url_type_raises(self, settings):
        op = Operation.get("ldh-List")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("not-a-uri"), URIRef("https://example.org/sparql"))

    def test_wrong_endpoint_type_raises(self, settings):
        op = Operation.get("ldh-List")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("https://example.org/"), Literal("not-a-uri"))


@pytest.mark.ldh
class TestLDHListLive:
    @pytest.mark.skip(reason="Need live LDH for end-to-end happy path")
    def test_returns_list(self, settings_with_auth):
        pass
