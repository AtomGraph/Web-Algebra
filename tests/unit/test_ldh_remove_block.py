"""Spec: formal-semantics.md "ldh-RemoveBlock - Remove content block from LinkedDataHub document"
Abstract: URI × Maybe URI → Any
Python:   def execute(self, url: URIRef, block: URIRef = None) -> Any
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestLDHRemoveBlockPure:
    def test_wrong_url_type_raises(self, settings):
        op = Operation.get("ldh-RemoveBlock")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("not-a-uri"))

    def test_wrong_block_type_raises(self, settings):
        op = Operation.get("ldh-RemoveBlock")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("https://example.org/"), Literal("not-a-uri"))


@pytest.mark.ldh
class TestLDHRemoveBlockLive:
    @pytest.mark.skip(reason="UNCLEAR(spec): return type `Any`")
    def test_basic(self, settings_with_auth):
        pass
