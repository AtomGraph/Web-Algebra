from rdflib import URIRef, Graph
from web_algebra.operation import Operation
from web_algebra.operations.schema.extract_classes import ExtractClasses
from web_algebra.operations.schema.extract_datatype_properties import ExtractDatatypeProperties
from web_algebra.operations.schema.extract_object_properties import ExtractObjectProperties
from web_algebra.operations.merge import Merge


class ExtractOntology(Operation):
    """Extracts complete OWL ontology (classes + properties) from an RDF dataset.

    Composes ExtractClasses, ExtractDatatypeProperties, and ExtractObjectProperties,
    then merges their results using the Merge operation.
    """

    @classmethod
    def description(cls) -> str:
        return "Extracts complete OWL ontology (classes, datatype properties, and object properties with functional property restrictions) from an RDF dataset."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {"endpoint": {"type": "string"}},
            "required": ["endpoint"],
        }

    def execute(self, endpoint: URIRef) -> Graph:
        """Extract complete ontology by composing individual extraction operations"""

        # Extract classes
        classes_graph = ExtractClasses(settings=self.settings, context=self.context).execute(endpoint)

        # Extract datatype properties (with functional property restrictions)
        datatype_props_graph = ExtractDatatypeProperties(settings=self.settings, context=self.context).execute(endpoint)

        # Extract object properties (with functional property restrictions)
        object_props_graph = ExtractObjectProperties(settings=self.settings, context=self.context).execute(endpoint)

        # Merge all graphs using the Merge operation
        graphs = [classes_graph, datatype_props_graph, object_props_graph]
        ontology_graph = Merge(settings=self.settings, context=self.context).execute(graphs)

        return ontology_graph

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Graph:
        """JSON execution: process arguments with strict type checking"""
        # Process endpoint
        endpoint_data = Operation.process_json(
            self.settings, arguments["endpoint"], self.context, variable_stack
        )
        if not isinstance(endpoint_data, URIRef):
            raise TypeError(
                f"ExtractOntology operation expects 'endpoint' to be URIRef, got {type(endpoint_data)}"
            )

        return self.execute(endpoint_data)
