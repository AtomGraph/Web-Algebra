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

from types import SimpleNamespace

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF

from web_algebra.operation import Operation

PROV_GENERATED_BY = URIRef("http://www.w3.org/ns/prov#wasGeneratedBy")
FOAF_PRIMARY_TOPIC = URIRef("http://xmlns.com/foaf/0.1/primaryTopic")
FOAF_NAME = URIRef("http://xmlns.com/foaf/0.1/name")
EX_AGE = URIRef("http://example.org/age")
DOC_TYPE = URIRef("http://example.org/Document")
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


class TestEmbeddedOpsAndVariables:
    """Ops/variables embedded in positions other than a subject @id."""

    def test_op_as_property_value_resolves_to_literal(self, settings):
        # An embedded op in object position (a property value), not an @id.
        json_data = {
            "@id": str(DOC_URI),
            str(FOAF_NAME): {"@op": "Value", "args": {"name": "$name"}},
        }
        stack = [{"name": Literal("Alice")}]

        result = Operation.process_json(settings, json_data, {}, stack)
        graph = Operation.to_graph(result)

        names = list(graph.objects(DOC_URI, FOAF_NAME))
        assert [str(n) for n in names] == ["Alice"]

    def test_op_in_type_resolves_to_iri(self, settings):
        # @type expects an IRI; an op-valued @type must resolve to a URIRef.
        json_data = {
            "@id": str(DOC_URI),
            "@type": {"@op": "Value", "args": {"name": "$cls"}},
        }
        stack = [{"cls": DOC_TYPE}]

        result = Operation.process_json(settings, json_data, {}, stack)
        graph = Operation.to_graph(result)

        assert (DOC_URI, RDF.type, DOC_TYPE) in graph

    def test_variable_from_context_binding(self, settings):
        # Bare name (no $) resolves from the context — the ForEach-row case from
        # the original bug report.
        json_data = {
            "@id": {"@op": "Value", "args": {"name": "doc"}},
            str(FOAF_PRIMARY_TOPIC): {
                "@id": {"@op": "Value", "args": {"name": "topic"}}
            },
        }
        context = SimpleNamespace(doc=DOC_URI, topic=MESSAGE_URI)

        result = Operation.process_json(settings, json_data, context, [])
        graph = Operation.to_graph(result)

        assert (DOC_URI, FOAF_PRIMARY_TOPIC, MESSAGE_URI) in graph
        assert not any(isinstance(s, BNode) for s, _, _ in graph)

    def test_embedded_ops_in_graph_array(self, settings):
        # @graph is a list of nodes; embedded ops in each must resolve, and the
        # @graph keyword must trigger JSON-LD handling (not generic recursion).
        a, b = URIRef("https://example.org/a"), URIRef("https://example.org/b")
        json_data = {
            "@graph": [
                {
                    "@id": {"@op": "Value", "args": {"name": "$a"}},
                    str(FOAF_NAME): "A",
                },
                {
                    "@id": {"@op": "Value", "args": {"name": "$b"}},
                    str(FOAF_NAME): "B",
                },
            ]
        }
        stack = [{"a": a, "b": b}]

        result = Operation.process_json(settings, json_data, {}, stack)
        graph = Operation.to_graph(result)

        assert [str(n) for n in graph.objects(a, FOAF_NAME)] == ["A"]
        assert [str(n) for n in graph.objects(b, FOAF_NAME)] == ["B"]
        assert not any(isinstance(s, BNode) for s, _, _ in graph)

    def test_context_keyword_preserved_with_embedded_op(self, settings):
        # A @context (which carries no @op) must survive intact so the parser
        # can use it, while a sibling embedded op still resolves.
        json_data = {
            "@context": {"name": str(FOAF_NAME)},
            "@id": str(DOC_URI),
            "name": {"@op": "Value", "args": {"name": "$name"}},
        }
        stack = [{"name": Literal("Alice")}]

        result = Operation.process_json(settings, json_data, {}, stack)

        assert result["@context"] == {"name": str(FOAF_NAME)}
        graph = Operation.to_graph(result)
        assert [str(n) for n in graph.objects(DOC_URI, FOAF_NAME)] == ["Alice"]

    def test_native_scalar_preserved_in_op_bearing_document(self, settings):
        # A plain JSON scalar inside an op-bearing document is left as native
        # JSON (not coerced to an rdflib term), so its JSON-LD datatype survives.
        json_data = {
            "@id": {"@op": "Value", "args": {"name": "$doc"}},
            str(EX_AGE): 30,
        }
        stack = [{"doc": DOC_URI}]

        result = Operation.process_json(settings, json_data, {}, stack)

        assert result[str(EX_AGE)] == 30  # still a Python int, not a Literal
        graph = Operation.to_graph(result)
        ages = list(graph.objects(DOC_URI, EX_AGE))
        assert len(ages) == 1 and ages[0].value == 30  # parsed as xsd:integer
