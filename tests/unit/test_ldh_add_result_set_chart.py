"""Spec: formal-semantics.md "ldh-AddResultSetChart - Add result set chart to LinkedDataHub document"
Abstract: URI × URI × Literal × URI × Literal × Literal × Maybe Literal × Maybe Literal → Any
Python:   def execute(self, url: URIRef, query: URIRef, title: Literal, chart_type: URIRef,
                      category_var_name: Literal, series_var_name: Literal,
                      description: Literal = None, fragment: Literal = None) -> Any
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestLDHAddResultSetChartPure:
    def test_wrong_url_type_raises(self, settings):
        op = Operation.get("ldh-AddResultSetChart")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                Literal("not-a-uri"),
                URIRef("https://example.org/q"),
                Literal("title"),
                URIRef("https://example.org/Bar"),
                Literal("cat"),
                Literal("series"),
            )

    def test_wrong_chart_type_raises(self, settings):
        op = Operation.get("ldh-AddResultSetChart")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                URIRef("https://example.org/"),
                URIRef("https://example.org/q"),
                Literal("title"),
                Literal("not-a-uri"),
                Literal("cat"),
                Literal("series"),
            )


@pytest.mark.ldh
class TestLDHAddResultSetChartLive:
    @pytest.mark.skip(reason="UNCLEAR(spec): return type `Any`")
    def test_basic(self, settings_with_auth):
        pass
