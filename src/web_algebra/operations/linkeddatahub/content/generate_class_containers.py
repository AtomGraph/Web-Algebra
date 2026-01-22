import logging
from rdflib import URIRef, Literal, Namespace, Graph
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS
from rdflib.query import Result
from web_algebra.operation import Operation
from web_algebra.operations.linkeddatahub.create_container import CreateContainer
from web_algebra.operations.linked_data.post import POST
from web_algebra.json_result import JSONResult


class GenerateClassContainers(Operation):
    """Creates LinkedDataHub containers for ontology classes with instance list views.

    For each class in the ontology:
    1. Creates a container using CreateContainer operation
    2. POSTs a SPIN sp:Select query that lists all instances
    3. POSTs an ldh:View that displays the instances

    This operation orchestrates actual HTTP operations to set up the portal structure.
    """

    @classmethod
    def description(cls) -> str:
        return "Creates LinkedDataHub containers with instance list views for ontology classes"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology": {
                    "type": "object",
                    "description": "RDF graph containing the extracted ontology"
                },
                "parent_container": {
                    "type": "string",
                    "description": "URI of the parent container where class containers will be created"
                },
                "endpoint": {
                    "type": "string",
                    "description": "SPARQL endpoint URI to be used by the queries"
                },
                "service_uri": {
                    "type": "string",
                    "description": "URI of the SPARQL service resource to reference in queries and views"
                }
            },
            "required": ["ontology", "parent_container", "endpoint", "service_uri"],
        }

    def execute(self, ontology: Graph, parent_container: URIRef, endpoint: URIRef, service_uri: URIRef) -> Result:
        """Create LDH containers for ontology classes

        Args:
            ontology: RDF graph containing classes
            parent_container: URI of parent container where class containers will be created
            endpoint: SPARQL endpoint URI to be used by the queries (for query text generation)
            service_uri: URI of the global SPARQL service resource to reference in queries and views

        Returns:
            Concatenated Result containing all operation results (CreateContainer + POST bindings)
        """
        # Define namespaces
        LDH = Namespace("https://w3id.org/atomgraph/linkeddatahub#")
        SP = Namespace("http://spinrdf.org/sp#")
        SPIN = Namespace("http://spinrdf.org/spin#")
        AC = Namespace("https://w3id.org/atomgraph/client#")

        # Query to find all classes in the ontology
        query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        SELECT DISTINCT ?class
        WHERE {
          ?class a owl:Class .
          FILTER (!isBlank(?class))
        }
        ORDER BY ?class
        """

        results = ontology.query(query)

        # Collect all operation results and track unique variables
        all_bindings = []
        all_vars = set()

        # Create container for each class
        for row in results:
            row_dict = row.asdict()
            class_uri = row_dict["class"]

            # Validate
            if not isinstance(class_uri, URIRef):
                raise TypeError(f"Expected class to be URIRef, got {type(class_uri)}")

            # Extract local name for URI
            class_local = self._get_local_name(class_uri)

            logging.info(f"Creating container for class {class_uri}")

            # Step 1: Create container
            title = Literal(f"{class_local} instances", datatype=XSD.string)
            slug = Literal(class_local, datatype=XSD.string)

            create_result = CreateContainer(settings=self.settings, context=self.context).execute(
                parent_container, title, slug
            )

            # Collect bindings from CreateContainer
            all_bindings.extend(create_result.bindings)
            all_vars.update(create_result.vars)

            # Extract created container URL from result
            container_uri = URIRef(create_result.bindings[0]["url"])
            logging.info(f"Created container at {container_uri}")

            # Step 2: Create and POST sp:Select query
            query_uri = URIRef(f"{container_uri}#Instances_Query")
            sparql_text = self._generate_instance_query(class_uri)

            query_graph = self._build_query_graph(query_uri, class_local, sparql_text, service_uri, LDH, SP)
            post_query_result = POST(settings=self.settings, context=self.context).execute(container_uri, query_graph)
            all_bindings.extend(post_query_result.bindings)
            all_vars.update(post_query_result.vars)
            logging.info(f"Posted query to {container_uri}")

            # Step 3: Create and POST ldh:View with service reference
            view_uri = URIRef(f"{container_uri}#Instances_View")
            view_graph = self._build_view_graph(view_uri, class_local, query_uri, service_uri, LDH, SP, AC, SPIN)
            post_view_result = POST(settings=self.settings, context=self.context).execute(container_uri, view_graph)
            all_bindings.extend(post_view_result.bindings)
            all_vars.update(post_view_result.vars)
            logging.info(f"Posted view to {container_uri}")

        # Create concatenated Result using JSONResult
        return JSONResult(list(all_vars), all_bindings)

    def _get_local_name(self, uri: URIRef) -> str:
        """Extract local name from URI (part after # or last /)"""
        uri_str = str(uri)
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        elif '/' in uri_str:
            return uri_str.split('/')[-1]
        return uri_str

    def _generate_instance_query(self, class_uri: URIRef) -> str:
        """Generate SPARQL SELECT query to list all instances of a class"""
        sparql = f"""SELECT DISTINCT ?instance
WHERE {{
  GRAPH ?instanceGraph {{
    ?instance a <{class_uri}> .
  }}
}}"""

        return sparql

    def _build_query_graph(self, query_uri: URIRef, class_local: str, sparql_text: str,
                          service_uri: URIRef, LDH, SP) -> Graph:
        """Build RDF graph for sp:Select query resource"""
        g = Graph()
        g.bind("sp", SP)
        g.bind("ldh", LDH)
        g.bind("rdfs", RDFS)
        g.bind("dct", DCTERMS)

        g.add((query_uri, RDF.type, SP.Select))
        g.add((query_uri, DCTERMS.title, Literal(f"Select {class_local} instances")))
        g.add((query_uri, RDFS.label, Literal(f"Select {class_local} instances")))
        g.add((query_uri, SP.text, Literal(sparql_text, datatype=XSD.string)))
        g.add((query_uri, LDH.service, service_uri))

        return g

    def _build_view_graph(self, view_uri: URIRef, class_local: str, query_uri: URIRef,
                         service_uri: URIRef, LDH, SP, AC, SPIN) -> Graph:
        """Build RDF graph for ldh:View resource"""
        g = Graph()
        g.bind("ldh", LDH)
        g.bind("spin", SPIN)
        g.bind("ac", AC)
        g.bind("dct", DCTERMS)

        g.add((view_uri, RDF.type, LDH.View))
        g.add((view_uri, DCTERMS.title, Literal(f"All {class_local}")))
        g.add((view_uri, SPIN.query, query_uri))
        g.add((view_uri, LDH.service, service_uri))
        g.add((view_uri, AC.mode, AC.ListMode))

        return g

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Result:
        """JSON execution: process arguments with type checking"""
        # Process ontology graph
        ontology_data = Operation.process_json(
            self.settings, arguments["ontology"], self.context, variable_stack
        )

        if not isinstance(ontology_data, Graph):
            raise TypeError(
                f"GenerateClassContainers operation expects 'ontology' to be Graph, got {type(ontology_data)}"
            )

        # Process parent_container
        parent_container_data = Operation.process_json(
            self.settings, arguments["parent_container"], self.context, variable_stack
        )

        if not isinstance(parent_container_data, URIRef):
            raise TypeError(
                f"GenerateClassContainers operation expects 'parent_container' to be URIRef, got {type(parent_container_data)}"
            )

        # Process endpoint
        endpoint_data = Operation.process_json(
            self.settings, arguments["endpoint"], self.context, variable_stack
        )

        if not isinstance(endpoint_data, URIRef):
            raise TypeError(
                f"GenerateClassContainers operation expects 'endpoint' to be URIRef, got {type(endpoint_data)}"
            )

        # Process service_uri
        service_uri_data = Operation.process_json(
            self.settings, arguments["service_uri"], self.context, variable_stack
        )

        if not isinstance(service_uri_data, URIRef):
            raise TypeError(
                f"GenerateClassContainers operation expects 'service_uri' to be URIRef, got {type(service_uri_data)}"
            )

        return self.execute(ontology_data, parent_container_data, endpoint_data, service_uri_data)
