from rdflib import URIRef, Literal, Namespace, Graph
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS
from web_algebra.operation import Operation


class GenerateOntologyViews(Operation):
    """Generates LinkedDataHub view templates for non-functional properties.

    Takes an extracted ontology graph and generates an RDF graph containing:
    - ldh:View resources for each non-functional property
    - SPIN sp:Select queries for retrieving related resources
    - ldh:template links from classes to views

    A property is considered non-functional if it does not have a
    owl:maxQualifiedCardinality restriction of 1.
    """

    @classmethod
    def description(cls) -> str:
        return "Generates LinkedDataHub view templates and SPIN queries for non-functional properties"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology": {
                    "type": "object",
                    "description": "RDF graph containing the extracted ontology"
                },
                "base_uri": {
                    "type": "string",
                    "description": "Base URI for generated view and query resources"
                },
                "service_uri": {
                    "type": "string",
                    "description": "URI of the sd:Service resource to be referenced by queries"
                },
                "package_path": {
                    "type": "string",
                    "description": "Optional path to write the ontology as ns.ttl file"
                }
            },
            "required": ["ontology", "base_uri", "service_uri"],
        }

    def execute(self, ontology: Graph, base_uri: URIRef, service_uri: URIRef, package_path: str = None) -> Graph:
        """Generate LDH view templates for non-functional properties

        Args:
            ontology: RDF graph containing classes and properties with optional restrictions
            base_uri: Base URI for generating view and query resource URIs
            service_uri: URI of the sd:Service resource to be referenced by queries
            package_path: Optional path to write the ontology as ns.ttl file

        Returns:
            RDF graph containing ldh:View, sp:Select, and ldh:view triples
        """
        # Define namespaces
        LDH = Namespace("https://w3id.org/atomgraph/linkeddatahub#")
        SP = Namespace("http://spinrdf.org/sp#")
        SPIN = Namespace("http://spinrdf.org/spin#")
        AC = Namespace("https://w3id.org/atomgraph/client#")

        # Query to find all non-functional properties with their classes
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        SELECT DISTINCT ?class ?property ?propertyType ?range
        WHERE {
          # Get all properties with their domain
          ?property a ?propertyType ;
                    rdfs:domain ?class ;
                    rdfs:range ?range .
          FILTER(?propertyType IN (owl:DatatypeProperty, owl:ObjectProperty))

          # Exclude functional properties (those with maxQualifiedCardinality = 1)
          FILTER NOT EXISTS {
            ?class rdfs:subClassOf ?restriction .
            ?restriction a owl:Restriction ;
                         owl:onProperty ?property ;
                         owl:maxQualifiedCardinality 1 .
          }
        }
        ORDER BY ?class ?property
        """

        results = ontology.query(query)

        # Create output graph
        g = Graph()
        g.bind("ldh", LDH)
        g.bind("sp", SP)
        g.bind("spin", SPIN)
        g.bind("ac", AC)
        g.bind("dct", DCTERMS)
        g.bind("rdfs", RDFS)
        g.bind("rdf", RDF)

        # Generate views and queries for each non-functional property
        for row in results:
            row_dict = row.asdict()
            class_uri = row_dict["class"]
            property_uri = row_dict["property"]
            property_type = row_dict["propertyType"]
            range_uri = row_dict["range"]

            # Validate that all values are URIRefs
            if not isinstance(class_uri, URIRef):
                raise TypeError(f"Expected class to be URIRef, got {type(class_uri)}")
            if not isinstance(property_uri, URIRef):
                raise TypeError(f"Expected property to be URIRef, got {type(property_uri)}")
            if not isinstance(property_type, URIRef):
                raise TypeError(f"Expected propertyType to be URIRef, got {type(property_type)}")
            if not isinstance(range_uri, URIRef):
                raise TypeError(f"Expected range to be URIRef, got {type(range_uri)}")

            # Extract local names for URIs
            class_local = self._get_local_name(class_uri)
            property_local = self._get_local_name(property_uri)

            # Generate URIs for view and query using Namespace for proper URI resolution
            ns = Namespace(base_uri)
            view_uri = ns[f"{class_local}_{property_local}_View"]
            query_uri = ns[f"{class_local}_{property_local}_Query"]

            # Generate human-readable title
            title = f"{property_local}"

            # Generate SPARQL query text
            sparql_text = self._generate_sparql_query(property_uri, property_type, range_uri)

            # Create ldh:view link from property to view
            g.add((property_uri, LDH.view, view_uri))

            # Create ldh:View resource
            g.add((view_uri, RDF.type, LDH.View))
            g.add((view_uri, DCTERMS.title, Literal(title)))
            g.add((view_uri, SPIN.query, query_uri))
            g.add((view_uri, AC.mode, AC.TableMode))

            # Create sp:Select query resource
            g.add((query_uri, RDF.type, SP.Select))
            g.add((query_uri, DCTERMS.title, Literal(f"Select {property_local}")))
            g.add((query_uri, RDFS.label, Literal(f"Select {property_local}")))
            g.add((query_uri, SP.text, Literal(sparql_text, datatype=XSD.string)))
            g.add((query_uri, LDH.service, service_uri))

        # Write to file if package_path is provided
        if package_path:
            from pathlib import Path

            # Create package directory if it doesn't exist
            package_dir = Path(package_path)
            package_dir.mkdir(parents=True, exist_ok=True)

            # Write ontology as Turtle file
            ontology_file = package_dir / "ns.ttl"
            ontology_file.write_text(g.serialize(format="turtle"))

        return g

    def _get_local_name(self, uri: URIRef) -> str:
        """Extract local name from URI (part after # or last /)"""
        uri_str = str(uri)
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        elif '/' in uri_str:
            return uri_str.split('/')[-1]
        return uri_str

    def _generate_sparql_query(self, property_uri: URIRef, property_type: URIRef, range_uri: URIRef) -> str:
        """Generate SPARQL SELECT query for a property"""
        sparql = f"""SELECT DISTINCT ?related ?label
WHERE {{
  GRAPH ?relatedGraph {{
    $about <{property_uri}> ?related .
  }}
}}
ORDER BY ?label"""

        return sparql

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Graph:
        """JSON execution: process arguments with type checking"""
        # Process ontology graph
        ontology_data = Operation.process_json(
            self.settings, arguments["ontology"], self.context, variable_stack
        )

        if not isinstance(ontology_data, Graph):
            raise TypeError(
                f"GenerateOntologyViews operation expects 'ontology' to be Graph, got {type(ontology_data)}"
            )

        # Process base_uri
        base_uri_data = Operation.process_json(
            self.settings, arguments["base_uri"], self.context, variable_stack
        )

        if not isinstance(base_uri_data, URIRef):
            raise TypeError(
                f"GenerateOntologyViews operation expects 'base_uri' to be URIRef, got {type(base_uri_data)}"
            )

        # Process service_uri
        service_uri_data = Operation.process_json(
            self.settings, arguments["service_uri"], self.context, variable_stack
        )

        if not isinstance(service_uri_data, URIRef):
            raise TypeError(
                f"GenerateOntologyViews operation expects 'service_uri' to be URIRef, got {type(service_uri_data)}"
            )

        # Process optional package_path
        package_path_data = None
        if "package_path" in arguments:
            package_path_data = Operation.process_json(
                self.settings, arguments["package_path"], self.context, variable_stack
            )
            if not isinstance(package_path_data, (str, Literal)):
                raise TypeError(
                    f"GenerateOntologyViews operation expects 'package_path' to be string, got {type(package_path_data)}"
                )
            # Convert Literal to string if needed
            if isinstance(package_path_data, Literal):
                package_path_data = str(package_path_data)

        return self.execute(ontology_data, base_uri_data, service_uri_data, package_path_data)
