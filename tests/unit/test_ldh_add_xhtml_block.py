"""Spec: formal-semantics.md "ldh-AddXHTMLBlock - Add XHTML content block to LinkedDataHub document"
Abstract: URI × Literal × Maybe Literal × Maybe Literal × Maybe Literal → Any
Python:   def execute(self, url: URIRef, value: Literal, title: Literal = None,
                      description: Literal = None, fragment: Literal = None) -> Any
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestLDHAddXHTMLBlockPure:
    def test_wrong_url_type_raises(self, settings):
        op = Operation.get("ldh-AddXHTMLBlock")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(Literal("not-a-uri"), Literal("<p>hello</p>"))

    def test_wrong_value_type_raises(self, settings):
        op = Operation.get("ldh-AddXHTMLBlock")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(URIRef("https://example.org/"), URIRef("not-a-literal"))


@pytest.mark.ldh
class TestLDHAddXHTMLBlockLive:
    @pytest.mark.skip(reason="UNCLEAR(spec): return type `Any`")
    def test_basic(self, settings_with_auth):
        pass
