"""Tests for Operation.to_graph — the single JSON-LD -> rdflib.Graph boundary.

Convention (implementation-level): operations resolve their arguments to plain
data via process_json, then call to_graph to hand execute() an rdflib.Graph.
execute() always works in rdflib terms; to_graph is the only place JSON-LD is
parsed, and the only place an op-specific base IRI is applied.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from web_algebra.operation import Operation

DOC_URI = URIRef("https://example.org/doc/")
PROV_GENERATED_BY = URIRef("http://www.w3.org/ns/prov#wasGeneratedBy")
ACTIVITY_URI = URIRef("https://example.org/activity/#this")
DOC_TYPE = URIRef("https://example.org/T")


class TestToGraph:
    def test_dict_is_parsed_as_jsonld(self):
        data = {
            "@id": str(DOC_URI),
            str(PROV_GENERATED_BY): {"@id": str(ACTIVITY_URI)},
        }

        graph = Operation.to_graph(data)

        assert isinstance(graph, Graph)
        assert (DOC_URI, PROV_GENERATED_BY, ACTIVITY_URI) in graph

    def test_top_level_array_is_parsed_as_jsonld(self):
        # SPARQL DESCRIBE/CONSTRUCT over multiple subjects returns a top-level
        # JSON-LD array of nodes; to_graph must accept it, not raise.
        data = [
            {"@id": str(DOC_URI), "@type": [str(DOC_TYPE)]},
            {"@id": str(ACTIVITY_URI), str(PROV_GENERATED_BY): {"@id": str(DOC_URI)}},
        ]

        graph = Operation.to_graph(data)

        assert isinstance(graph, Graph)
        assert (DOC_URI, RDF.type, DOC_TYPE) in graph
        assert (ACTIVITY_URI, PROV_GENERATED_BY, DOC_URI) in graph

    def test_graph_passes_through_unchanged(self):
        # An upstream op (e.g. CONSTRUCT) already produced a Graph — identity.
        g = Graph()
        g.add((DOC_URI, PROV_GENERATED_BY, ACTIVITY_URI))

        assert Operation.to_graph(g) is g

    def test_base_resolves_relative_iris(self):
        # A relative @id must resolve against the supplied base IRI.
        data = {"@id": "", str(PROV_GENERATED_BY): {"@id": "#this"}}

        graph = Operation.to_graph(data, base="https://example.org/doc/")

        assert (
            URIRef("https://example.org/doc/"),
            PROV_GENERATED_BY,
            URIRef("https://example.org/doc/#this"),
        ) in graph

    def test_non_jsonld_input_raises_typeerror(self):
        with pytest.raises(TypeError):
            Operation.to_graph("not a graph or dict")
