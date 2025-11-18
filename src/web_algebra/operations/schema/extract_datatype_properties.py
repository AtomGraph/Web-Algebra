import rdflib
from rdflib import URIRef, Literal
from rdflib.namespace import XSD
from web_algebra.operations.sparql.construct import CONSTRUCT
from web_algebra.operation import Operation


class ExtractDatatypeProperties(CONSTRUCT):
    @classmethod
    def description(cls) -> str:
        return "Extracts OWL datatype properties from an RDF dataset."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {"endpoint": {"type": "string"}},
            "required": ["endpoint"],
        }

    def execute(self, endpoint: URIRef) -> rdflib.Graph:
        """Pure function: extract OWL datatype properties with RDFLib terms"""
        query = Literal("""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

CONSTRUCT {
  ?property a owl:DatatypeProperty ;
           rdfs:domain ?domain ;
           rdfs:range ?datatype .
}
WHERE {
  {
    SELECT ?property ?datatype (SAMPLE(?d) AS ?domain)
    WHERE {
      {
        ?subject ?property ?literal .
        FILTER(?property != rdf:type)
        FILTER(isLiteral(?literal))
        BIND(datatype(?literal) as ?datatype)
      } UNION {
        GRAPH ?g {
          ?subject ?property ?literal .
          FILTER(?property != rdf:type)
          FILTER(isLiteral(?literal))
          BIND(datatype(?literal) as ?datatype)
        }
      }

      OPTIONAL {
        { ?subject a ?d }
        UNION
        { GRAPH ?subjG { ?subject a ?d } }
        FILTER(!isBlank(?d))
      }
    }
    GROUP BY ?property ?datatype
    HAVING(COUNT(DISTINCT ?d) <= 1)
  }
}
""", datatype=XSD.string)
        return super().execute(endpoint, query)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> rdflib.Graph:
        """JSON execution: process arguments with strict type checking"""
        # Process endpoint
        endpoint_data = Operation.process_json(
            self.settings, arguments["endpoint"], self.context, variable_stack
        )
        if not isinstance(endpoint_data, URIRef):
            raise TypeError(
                f"ExtractDatatypeProperties operation expects 'endpoint' to be URIRef, got {type(endpoint_data)}"
            )

        return self.execute(endpoint_data)
