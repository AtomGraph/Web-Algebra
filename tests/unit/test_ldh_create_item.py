"""Spec: formal-semantics.md "ldh-CreateItem - Create LinkedDataHub item document"
Abstract: URI × Literal × Maybe Literal → Result
Python:   def execute(self, container_uri: URIRef, title: Literal, slug: Literal = None) -> Result
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestLDHCreateItemPure:
    def test_wrong_container_uri_type_raises(self, settings):
        op = Operation.get("ldh-CreateItem")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("not-a-uri"), Literal("title"))

    def test_wrong_title_type_raises(self, settings):
        op = Operation.get("ldh-CreateItem")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("https://example.org/"), URIRef("not-a-literal"))


@pytest.mark.ldh
class TestLDHCreateItemLive:
    @pytest.mark.skip(reason="Need live LDH for end-to-end happy path")
    def test_returns_result(self, settings_with_auth):
        pass
