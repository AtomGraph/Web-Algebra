from rdflib import URIRef, Literal
from rdflib.namespace import XSD
from rdflib.query import Result
from web_algebra.operation import Operation
from web_algebra.operations.schema.extract_ontology import ExtractOntology
from web_algebra.operations.linkeddatahub.content.generate_ontology_views import GenerateOntologyViews
from web_algebra.operations.linkeddatahub.content.generate_class_containers import GenerateClassContainers
from web_algebra.operations.linked_data.post import POST
from web_algebra.operations.linkeddatahub.add_generic_service import AddGenericService
from web_algebra.json_result import JSONResult


class GeneratePortal(Operation):
    """Generates a complete LinkedDataHub portal from a SPARQL endpoint.

    Composes:
    1. ExtractOntology - extracts classes and properties
    2. GenerateOntologyViews - generates property views as a single RDF graph
    3. POST - posts the views to the ontology namespace
    4. GenerateClassContainers - creates containers for each class with instance views
    """

    @classmethod
    def description(cls) -> str:
        return "Generates a complete LinkedDataHub portal with class containers and property views from a SPARQL endpoint"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string", "description": "SPARQL endpoint to extract ontology from"},
                "ontology_namespace": {"type": "string", "description": "URI where ontology views will be posted"},
                "parent_container": {"type": "string", "description": "URI of parent container for class containers"},
            },
            "required": ["endpoint", "ontology_namespace", "parent_container"],
        }

    def execute(self, endpoint: URIRef, ontology_namespace: URIRef, parent_container: URIRef) -> Result:
        """Generate complete portal by composing extraction and generation operations

        Args:
            endpoint: SPARQL endpoint URI
            ontology_namespace: URI where ontology views will be posted
            parent_container: URI of parent container for class containers

        Returns:
            Concatenated Result containing all operation results
        """
        import logging

        # Step 0: Create service resource for the SPARQL endpoint
        logging.info(f"Creating service resource for endpoint {endpoint}")
        fragment = "Service"
        service_result = AddGenericService(settings=self.settings, context=self.context).execute(
            url=ontology_namespace,
            endpoint=endpoint,
            title=Literal("SPARQL Service", datatype=XSD.string),
            fragment=Literal(fragment, datatype=XSD.string)
        )
        # Extract service URI from result - POST to URL with fragment creates resource at URL#fragment
        service_uri = URIRef(f"{ontology_namespace}#{fragment}")
        logging.info(f"Created service resource at {service_uri}")

        # Step 1: Extract ontology
        ontology_graph = ExtractOntology(settings=self.settings, context=self.context).execute(endpoint)

        # Step 2: Generate property views (single RDF graph)
        views_graph = GenerateOntologyViews(settings=self.settings, context=self.context).execute(
            ontology_graph, ontology_namespace, service_uri
        )

        # Debug: print the views graph before POSTing
        logging.info("=== Generated views graph (Turtle format) ===")
        logging.info(views_graph.serialize(format="turtle"))
        logging.info("=== End of views graph ===")

        # Step 3: POST views to ontology namespace
        post_views_result = POST(settings=self.settings, context=self.context).execute(ontology_namespace, views_graph)

        # Step 4: Generate class containers (performs multiple operations internally)
        # Each container creates its own service resource
        class_containers_result = GenerateClassContainers(settings=self.settings, context=self.context).execute(
            ontology_graph, parent_container, endpoint
        )

        # Concatenate all results
        all_bindings = []
        all_vars = set()

        all_bindings.extend(service_result.bindings)
        all_vars.update(service_result.vars)

        all_bindings.extend(post_views_result.bindings)
        all_vars.update(post_views_result.vars)

        all_bindings.extend(class_containers_result.bindings)
        all_vars.update(class_containers_result.vars)

        return JSONResult(list(all_vars), all_bindings)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Result:
        """JSON execution: process arguments with strict type checking"""
        # Process endpoint
        endpoint_data = Operation.process_json(
            self.settings, arguments["endpoint"], self.context, variable_stack
        )
        if not isinstance(endpoint_data, URIRef):
            raise TypeError(
                f"GeneratePortal operation expects 'endpoint' to be URIRef, got {type(endpoint_data)}"
            )

        # Process ontology_namespace
        ontology_namespace_data = Operation.process_json(
            self.settings, arguments["ontology_namespace"], self.context, variable_stack
        )
        if not isinstance(ontology_namespace_data, URIRef):
            raise TypeError(
                f"GeneratePortal operation expects 'ontology_namespace' to be URIRef, got {type(ontology_namespace_data)}"
            )

        # Process parent_container
        parent_container_data = Operation.process_json(
            self.settings, arguments["parent_container"], self.context, variable_stack
        )
        if not isinstance(parent_container_data, URIRef):
            raise TypeError(
                f"GeneratePortal operation expects 'parent_container' to be URIRef, got {type(parent_container_data)}"
            )

        return self.execute(endpoint_data, ontology_namespace_data, parent_container_data)
