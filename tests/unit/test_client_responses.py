"""Implementation-level tests for the Linked Data response contract
(formal-semantics.md §4.3–4.4): the operations read and write RDF graphs;
content negotiation is transparent; a non-RDF response — unsupported media
type, missing Content-Type, or a body that does not parse as the negotiated
format — raises ValueError.

These pin the contract at the client seam with a stubbed opener (no network).
"""

from __future__ import annotations

import pytest
from rdflib import URIRef

from web_algebra.client import LinkedDataClient, SPARQLClient


class _FakeResponse:
    def __init__(self, body: bytes, content_type: str | None):
        self._body = body
        self.headers = {} if content_type is None else {"Content-Type": content_type}

    def read(self) -> bytes:
        return self._body


class _FakeOpener:
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.last_request = None

    def open(self, request):
        self.last_request = request
        return self._response


def _get_client(body: bytes, content_type: str | None) -> LinkedDataClient:
    client = LinkedDataClient(verify_ssl=False)
    client.opener = _FakeOpener(_FakeResponse(body, content_type))
    return client


class TestLinkedDataResponses:
    def test_rdf_response_parses_to_graph(self):
        client = _get_client(
            b"<http://ex/s> <http://ex/p> <http://ex/o> .", "text/turtle"
        )
        graph = client.get("http://ex/doc")
        assert (URIRef("http://ex/s"), URIRef("http://ex/p"), URIRef("http://ex/o")) in graph

    def test_accept_header_offers_rdf_media_types_only(self):
        # §4.4: content negotiation is transparent — RDF media types are
        # requested
        client = _get_client(b"", "text/turtle")
        client.get("http://ex/doc")
        accept = client.opener.last_request.get_header("Accept")
        assert "text/turtle" in accept
        assert "application/rdf+xml" in accept

    def test_non_rdf_media_type_raises_value_error(self):
        # §4.4: unsupported media type → ValueError
        client = _get_client(b"<html></html>", "text/html")
        with pytest.raises(ValueError):
            client.get("http://ex/doc")

    def test_missing_content_type_raises_value_error(self):
        # §4.4: missing Content-Type → ValueError
        client = _get_client(b"anything", None)
        with pytest.raises(ValueError):
            client.get("http://ex/doc")

    def test_rdf_labelled_garbage_raises_value_error(self):
        # §4.4: a body that does not parse as its declared RDF type →
        # ValueError
        client = _get_client(b"this is not turtle @@@", "text/turtle")
        with pytest.raises(ValueError):
            client.get("http://ex/doc")


class TestSPARQLResponses:
    def test_construct_response_not_parsing_as_ntriples_raises(self):
        # §4.3: a response that does not parse as the negotiated format →
        # ValueError
        client = SPARQLClient(verify_ssl=False)
        client.opener = _FakeOpener(_FakeResponse(b"not n-triples @@@", None))
        with pytest.raises(ValueError):
            client.query(
                "http://ex/sparql",
                "CONSTRUCT { <http://ex/s> <http://ex/p> <http://ex/o> } WHERE {}",
            )

    def test_select_response_not_parsing_as_json_raises(self):
        # §4.3: json.JSONDecodeError is a ValueError subclass
        client = SPARQLClient(verify_ssl=False)
        client.opener = _FakeOpener(_FakeResponse(b"not json", None))
        with pytest.raises(ValueError):
            client.query("http://ex/sparql", "SELECT * WHERE { ?s ?p ?o }")
