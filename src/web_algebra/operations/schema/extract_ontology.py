from typing import Optional
from rdflib import Graph, URIRef
from rdflib.query import Result
from web_algebra.operation import Operation
from web_algebra.schema_extraction import SchemaExtraction
from web_algebra.operations.schema.extract_classes import ExtractClasses
from web_algebra.operations.schema.extract_datatype_properties import ExtractDatatypeProperties
from web_algebra.operations.schema.extract_object_properties import ExtractObjectProperties


class ExtractOntology(SchemaExtraction, Operation):
    """The union of the three schema extractions — classes plus datatype and
    object properties — as one graph, each scoped by the same `bindings`
    (formal-semantics.md §4.6).
    """

    @classmethod
    def description(cls) -> str:
        return "Extracts a complete OWL ontology (classes, datatype properties, and object properties with functional property restrictions) from an RDF dataset, optionally scoped to the subjects in 'bindings'."

    def execute(self, endpoint: URIRef, bindings: Optional[Result] = None) -> Graph:
        """Extract the ontology by running every extraction with one scope"""
        scope = self.scope(endpoint, bindings)
        ontology = Graph()
        for extraction in (ExtractClasses, ExtractDatatypeProperties, ExtractObjectProperties):
            ontology += extraction(settings=self.settings, context=self.context).extract(endpoint, scope)
        return ontology
