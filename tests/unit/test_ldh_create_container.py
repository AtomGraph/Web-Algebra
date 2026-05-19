"""Spec: formal-semantics.md "ldh-CreateContainer - Create LinkedDataHub container document"
Abstract: URI × Literal × Maybe Literal × Maybe Literal → Result
Python:   def execute(self, parent_uri: URIRef, title: Literal, slug: Literal = None,
                      description: Literal = None) -> Result
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestLDHCreateContainerPure:
    def test_wrong_parent_uri_type_raises(self, settings):
        op = Operation.get("ldh-CreateContainer")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("not-a-uri"), Literal("title"))

    def test_wrong_title_type_raises(self, settings):
        op = Operation.get("ldh-CreateContainer")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("https://example.org/"), URIRef("https://example.org/title"))


@pytest.mark.ldh
class TestLDHCreateContainerLive:
    @pytest.mark.skip(reason="UNCLEAR(spec): meaningful assertion about the Result return is undefined; need live LDH")
    def test_returns_result(self, settings_with_auth):
        pass
