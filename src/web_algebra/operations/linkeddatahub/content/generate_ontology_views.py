import hashlib
from rdflib import URIRef, Literal, Namespace, Graph
from rdflib.namespace import RDF, RDFS, OWL, XSD, DCTERMS
from web_algebra.operation import Operation

LDH = Namespace("https://w3id.org/atomgraph/linkeddatahub#")
SP = Namespace("http://spinrdf.org/sp#")
SPIN = Namespace("http://spinrdf.org/spin#")
AC = Namespace("https://w3id.org/atomgraph/client#")


class GenerateOntologyViews(Operation):
    """The LinkedDataHub views of an ontology's object properties
    (formal-semantics.md Appendix A), as a graph for the application's namespace
    ontology: an ldh:view per property with an rdfs:domain that is not
    functional, an ldh:inverseView per property with an rdfs:range that is not
    inverse-functional, and the domains and ranges, without which LinkedDataHub's
    client cannot find the views. Pure: it builds the graph and writes nothing.
    """

    @classmethod
    def name(cls):
        return "ldh-GenerateOntologyViews"

    @classmethod
    def description(cls) -> str:
        return "Generates the LinkedDataHub views of an ontology's object properties, to be written into the application's namespace ontology: an ldh:view (shown on resources of the property's rdfs:domain) for each non-functional property with a domain, an ldh:inverseView (shown on resources of its rdfs:range) for each non-inverse-functional property with a range, and the domain and range triples the client needs to find them."

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
        if not isinstance(ontology, Graph):
            raise TypeError(
                f"GenerateOntologyViews operation expects 'ontology' to be Graph, got {type(ontology)}"
            )
        if not isinstance(base_uri, URIRef):
            raise TypeError(
                f"GenerateOntologyViews operation expects 'base_uri' to be URIRef, got {type(base_uri)}"
            )
        if not isinstance(service_uri, URIRef):
            raise TypeError(
                f"GenerateOntologyViews operation expects 'service_uri' to be URIRef, got {type(service_uri)}"
            )


        # The client shows a property's ldh:view on a resource whose type is the
        # property's rdfs:domain, and its ldh:inverseView on one whose type is its
        # rdfs:range (LinkedDataHub's ldh:ontology-view-query), so a view is only
        # made where the client can find it, and the domain and range go with it.
        properties = sorted(set(ontology.subjects(RDF.type, OWL.ObjectProperty)), key=str)

        g = Graph()
        g.bind("ldh", LDH)
        g.bind("sp", SP)
        g.bind("spin", SPIN)
        g.bind("ac", AC)
        g.bind("dct", DCTERMS)
        g.bind("rdfs", RDFS)
        g.bind("rdf", RDF)

        seen_locals: set[str] = set()
        for property_uri in properties:
            if not isinstance(property_uri, URIRef):
                continue
            domains = set(ontology.objects(property_uri, RDFS.domain))
            ranges = set(ontology.objects(property_uri, RDFS.range))
            forward = bool(domains) and (property_uri, RDF.type, OWL.FunctionalProperty) not in ontology
            inverse = bool(ranges) and (property_uri, RDF.type, OWL.InverseFunctionalProperty) not in ontology
            if not (forward or inverse):
                continue

            # Disambiguate when two properties share a local name (different namespaces).
            property_local = self._get_local_name(property_uri)
            if property_local in seen_locals:
                suffix = hashlib.sha1(str(property_uri).encode()).hexdigest()[:6]
                property_local = f"{property_local}_{suffix}"
            seen_locals.add(property_local)

            if forward:
                self._add_view(g, base_uri, service_uri, property_uri, LDH.view,
                               f"{property_local}_View", f"{property_local}_Query", property_local,
                               f"$about <{property_uri}> ?related")
            if inverse:
                self._add_view(g, base_uri, service_uri, property_uri, LDH.inverseView,
                               f"{property_local}_InverseView", f"{property_local}_InverseQuery",
                               f"{property_local} (inverse)", f"?related <{property_uri}> $about")
            for domain in domains:
                g.add((property_uri, RDFS.domain, domain))
            for range_ in ranges:
                g.add((property_uri, RDFS.range, range_))

        return g

    @staticmethod
    def _add_view(g: Graph, base_uri: URIRef, service_uri: URIRef, property_uri: URIRef, attachment: URIRef,
                  view_name: str, query_name: str, title: str, pattern: str) -> None:
        """A view on `property_uri` by `attachment` (ldh:view or ldh:inverseView),
        whose query selects ?related by `pattern`, which reads the resource shown
        as $about, the variable LinkedDataHub's client binds."""
        view_uri = URIRef(f"{base_uri}#{view_name}")
        query_uri = URIRef(f"{base_uri}#{query_name}")
        g.add((property_uri, attachment, view_uri))
        g.add((view_uri, RDF.type, LDH.View))
        g.add((view_uri, DCTERMS.title, Literal(title)))
        g.add((view_uri, SPIN.query, query_uri))
        g.add((view_uri, AC.mode, AC.TableMode))
        g.add((query_uri, RDF.type, SP.Select))
        g.add((query_uri, DCTERMS.title, Literal(f"Select {title}")))
        g.add((query_uri, SP.text, Literal(f"SELECT DISTINCT ?related WHERE {{ GRAPH ?g {{ {pattern} }} }}", datatype=XSD.string)))
        g.add((query_uri, LDH.service, service_uri))

    def _get_local_name(self, uri: URIRef) -> str:
        """Extract local name from URI (part after # or last /)"""
        uri_str = str(uri)
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        elif '/' in uri_str:
            return uri_str.split('/')[-1]
        return uri_str

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Graph:
        """JSON execution: process arguments with type checking"""
        # Process ontology graph — accept a Graph (e.g. from CONSTRUCT) or a
        # JSON-LD document, converting the latter to a Graph
        ontology_data = self.to_graph(
            Operation.process_json(
                self.settings, arguments["ontology"], self.context, variable_stack
            )
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
