"""Spec: formal-semantics.md "ldh-AddFile - Add file (binary) to LinkedDataHub document via multipart RDF/POST"
Abstract: URI × Literal × Literal × Maybe Literal × Maybe Literal → Any
Python:   def execute(self, url: URIRef, file_path: Literal, title: Literal,
                      description: Literal = None, content_type: Literal = None) -> Any
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef

from web_algebra.operation import Operation


class TestLDHAddFilePure:
    def test_wrong_url_type_raises(self, settings):
        op = Operation.get("ldh-AddFile")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                Literal("not-a-uri"),
                Literal("/abs/path.png"),
                Literal("Title"),
            )

    def test_wrong_file_path_type_raises(self, settings):
        op = Operation.get("ldh-AddFile")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                URIRef("https://example.org/"),
                URIRef("not-a-literal"),
                Literal("Title"),
            )

    def test_wrong_title_type_raises(self, settings):
        op = Operation.get("ldh-AddFile")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                URIRef("https://example.org/"),
                Literal("/abs/path.png"),
                URIRef("not-a-literal"),
            )

    def test_wrong_description_type_raises(self, settings):
        op = Operation.get("ldh-AddFile")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                URIRef("https://example.org/"),
                Literal("/abs/path.png"),
                Literal("Title"),
                description=URIRef("not-a-literal"),
            )

    def test_wrong_content_type_type_raises(self, settings):
        op = Operation.get("ldh-AddFile")(settings=settings)
        with pytest.raises(TypeError):
            op.execute(
                URIRef("https://example.org/"),
                Literal("/abs/path.png"),
                Literal("Title"),
                content_type=URIRef("not-a-literal"),
            )


@pytest.mark.ldh
class TestLDHAddFileLive:
    @pytest.mark.skip(reason="UNCLEAR(spec): return type `Any`. Covered by integration LDH composition fixture instead.")
    def test_basic(self, settings_with_auth):
        pass
