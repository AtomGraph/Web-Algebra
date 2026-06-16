import hashlib
from rdflib import URIRef, Literal, Namespace, Graph
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS
from web_algebra.operation import Operation


class GenerateOntologyViews(Operation):
    """Generates LinkedDataHub views for ontology properties.

    Takes an extracted ontology graph and generates an RDF graph containing:
    - ldh:View resources for each non-functional property
    - SPIN sp:Select queries for retrieving related resources
    - ldh:view links from properties to views

    Functional properties (declared `owl:FunctionalProperty`) are skipped:
    they yield at most one value, so a table view would be redundant.
    """

    @classmethod
    def description(cls) -> str:
        return "Generates LinkedDataHub views and SPIN queries for ontology properties (excluding owl:FunctionalProperty)"

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
                }
            },
            "required": ["ontology", "base_uri", "service_uri"],
        }

    def execute(self, ontology: Graph, base_uri: URIRef, service_uri: URIRef) -> Graph:
        """Generate LDH views for ontology properties

        Args:
            ontology: RDF graph containing property declarations
            base_uri: Base URI for generating view and query resource URIs
            service_uri: URI of the sd:Service resource to be referenced by queries

        Returns:
            RDF graph containing ldh:View, sp:Select, and ldh:view triples
        """
        # Define namespaces
        LDH = Namespace("https://w3id.org/atomgraph/linkeddatahub#")
        SP = Namespace("http://spinrdf.org/sp#")
        SPIN = Namespace("http://spinrdf.org/spin#")
        AC = Namespace("https://w3id.org/atomgraph/client#")

        # Find all distinct datatype/object properties that are not owl:FunctionalProperty.
        # Views attach to properties (LDH `ldh:view` has rdfs:domain rdf:Property), so we
        # iterate by property rather than by (class, property) pair.
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        SELECT DISTINCT ?property ?propertyType
        WHERE {
          ?property a ?propertyType .
          FILTER(?propertyType IN (owl:DatatypeProperty, owl:ObjectProperty))
          FILTER NOT EXISTS { ?property a owl:FunctionalProperty }
        }
        ORDER BY ?property
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

        seen_locals: set[str] = set()

        for row in results:
            row_dict = row.asdict()
            property_uri = row_dict["property"]
            property_type = row_dict["propertyType"]

            if not isinstance(property_uri, URIRef):
                raise TypeError(f"Expected property to be URIRef, got {type(property_uri)}")
            if not isinstance(property_type, URIRef):
                raise TypeError(f"Expected propertyType to be URIRef, got {type(property_type)}")

            # Disambiguate when two properties share a local name (different namespaces).
            property_local = self._get_local_name(property_uri)
            if property_local in seen_locals:
                suffix = hashlib.sha1(str(property_uri).encode()).hexdigest()[:6]
                property_local = f"{property_local}_{suffix}"
            seen_locals.add(property_local)

            view_uri = URIRef(f"{base_uri}#{property_local}_View")
            query_uri = URIRef(f"{base_uri}#{property_local}_Query")

            title = f"{property_local}"
            sparql_text = self._generate_sparql_query(property_uri)

            # Attach view to property via ldh:view (forward direction).
            # TODO: emit ldh:inverseView for selected object properties in a follow-up.
            g.add((property_uri, LDH.view, view_uri))

            # ldh:View resource
            g.add((view_uri, RDF.type, LDH.View))
            g.add((view_uri, DCTERMS.title, Literal(title)))
            g.add((view_uri, SPIN.query, query_uri))
            g.add((view_uri, AC.mode, AC.TableMode))

            # sp:Select query resource
            g.add((query_uri, RDF.type, SP.Select))
            g.add((query_uri, DCTERMS.title, Literal(f"Select {property_local}")))
            g.add((query_uri, RDFS.label, Literal(f"Select {property_local}")))
            g.add((query_uri, SP.text, Literal(sparql_text, datatype=XSD.string)))
            g.add((query_uri, LDH.service, service_uri))

        return g

    def _get_local_name(self, uri: URIRef) -> str:
        """Extract local name from URI (part after # or last /)"""
        uri_str = str(uri)
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        elif '/' in uri_str:
            return uri_str.split('/')[-1]
        return uri_str

    def _generate_sparql_query(self, property_uri: URIRef) -> str:
        """Generate SPARQL SELECT query for a property (forward direction)"""
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

        return self.execute(ontology_data, base_uri_data, service_uri_data)
