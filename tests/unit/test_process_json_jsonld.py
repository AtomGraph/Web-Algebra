"""Regression tests for Operation.process_json JSON-LD handling.

These are implementation-level regression tests (not spec derivations): they
pin how process_json treats JSON-LD-shaped dicts.

Bug (regressed in 1.3.0): a JSON-LD-shaped dict carrying a reserved key
(@id/@type/@graph/@context) was eagerly parsed to an rdflib.Graph at the
process_json layer. When such a dict embedded {"@op": ...} operations, the
parse happened *before* those ops resolved. Unresolved @op objects are illegal
JSON-LD (an @id must be a string IRI, not an object), so the parser silently
minted blank nodes and the intended IRIs were lost.

Fix: process_json no longer parses JSON-LD to a Graph at all. It resolves any
embedded @op/variable references in place (leaving the rest as plain JSON) and
returns a dict; the consuming op (POST/PUT/Merge/ldh Create*/Add*) parses it,
which they all already do — and with the correct base IRI.
"""

from __future__ import annotations

from rdflib import BNode, Graph, URIRef

from web_algebra.operation import Operation

PROV_GENERATED_BY = URIRef("http://www.w3.org/ns/prov#wasGeneratedBy")
FOAF_PRIMARY_TOPIC = URIRef("http://xmlns.com/foaf/0.1/primaryTopic")
DOC_URI = URIRef("https://example.org/doc/")
ACTIVITY_URI = URIRef("https://example.org/activity/#this")
MESSAGE_URI = URIRef("https://example.org/message/#this")


class TestOpBearingJsonLd:
    """JSON-LD documents with embedded @op must resolve before being parsed."""

    def test_op_valued_ids_resolve_to_iris_not_bnodes(self, settings):
        # An @id and a nested object @id both come from runtime bindings.
        # End-to-end through a consuming op (Merge) that parses the document.
        json_data = {
            "@op": "Merge",
            "args": {
                "graphs": [
                    {
                        "@id": {"@op": "Value", "args": {"name": "$docUrl"}},
                        str(PROV_GENERATED_BY): {"@id": str(ACTIVITY_URI)},
                        str(FOAF_PRIMARY_TOPIC): {
                            "@id": {"@op": "Value", "args": {"name": "$message"}}
                        },
                    }
                ]
            },
        }
        stack = [{"docUrl": DOC_URI, "message": MESSAGE_URI}]

        result = Operation.process_json(settings, json_data, {}, stack)

        assert isinstance(result, Graph)
        # The document URI must survive as a concrete subject, not a blank node.
        assert (DOC_URI, PROV_GENERATED_BY, ACTIVITY_URI) in result
        assert (DOC_URI, FOAF_PRIMARY_TOPIC, MESSAGE_URI) in result
        # No triple should have a blank-node subject — that was the bug.
        assert not any(isinstance(s, BNode) for s, _, _ in result)

    def test_op_valued_id_resolves_in_place(self, settings):
        # process_json resolves the embedded op to its RDFLib term and returns
        # a dict — it does not parse to a Graph.
        json_data = {
            "@id": {"@op": "Value", "args": {"name": "$docUrl"}},
            str(PROV_GENERATED_BY): {"@id": str(ACTIVITY_URI)},
        }
        stack = [{"docUrl": DOC_URI}]

        result = Operation.process_json(settings, json_data, {}, stack)

        assert isinstance(result, dict)
        assert result["@id"] == DOC_URI

    def test_pure_data_fragment_inside_document_stays_a_dict(self, settings):
        # A nested {"@id": "..."} object reference must NOT be parsed into a
        # standalone Graph — it is part of the one enclosing JSON-LD document
        # that the consuming op serialises and parses as a whole.
        json_data = {
            "@id": {"@op": "Value", "args": {"name": "$docUrl"}},
            str(PROV_GENERATED_BY): {"@id": str(ACTIVITY_URI)},
        }
        stack = [{"docUrl": DOC_URI}]

        result = Operation.process_json(settings, json_data, {}, stack)

        assert not isinstance(result[str(PROV_GENERATED_BY)], Graph)
        assert result[str(PROV_GENERATED_BY)] == {"@id": str(ACTIVITY_URI)}


class TestPureDataJsonLd:
    """Static JSON-LD (no @op) is returned as a dict for the consumer to parse."""

    def test_pure_data_jsonld_returns_dict(self, settings):
        json_data = {
            "@id": str(DOC_URI),
            str(PROV_GENERATED_BY): {"@id": str(ACTIVITY_URI)},
        }

        result = Operation.process_json(settings, json_data)

        # No eager Graph parse: the dict is preserved verbatim for the consumer.
        assert isinstance(result, dict)
        assert result == json_data

    def test_pure_data_jsonld_parses_to_expected_graph(self, settings):
        # Sanity: the preserved dict still yields the intended triples when a
        # consuming op parses it (the standard json.dumps -> json-ld parse).
        import json

        json_data = {
            "@id": str(DOC_URI),
            str(PROV_GENERATED_BY): {"@id": str(ACTIVITY_URI)},
        }

        result = Operation.process_json(settings, json_data)
        graph = Graph()
        graph.parse(data=json.dumps(result), format="json-ld")

        assert (DOC_URI, PROV_GENERATED_BY, ACTIVITY_URI) in graph
