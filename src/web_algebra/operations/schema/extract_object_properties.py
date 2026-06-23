from rdflib import URIRef, Literal, Graph
from rdflib.namespace import XSD
from web_algebra.operations.sparql.construct import CONSTRUCT
from web_algebra.operation import Operation


class ExtractObjectProperties(CONSTRUCT):
    @classmethod
    def description(cls) -> str:
        return "Extracts OWL object properties from an RDF dataset."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {"endpoint": {"type": "string"}},
            "required": ["endpoint"],
        }

    def execute(self, endpoint: URIRef) -> Graph:
        """Pure function: extract OWL object properties with RDFLib terms

        Infers functional properties using closed world assumption:
        - Counts max cardinality per property across all subjects in the dataset
        - When global max = 1, emits ?property a owl:FunctionalProperty
        - Note: Inference based solely on present data, not formal ontology definitions
        """
        query = Literal("""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

CONSTRUCT {
  ?property a owl:ObjectProperty ;
            rdfs:domain ?domain ;
            rdfs:range ?range .
  ?functional a owl:FunctionalProperty .
}
WHERE {
  {
    SELECT ?property ?domain ?range (IF(?maxC = 1, ?property, ?UNDEF) AS ?functional)
    WHERE {
      {
        SELECT ?property (SAMPLE(?d) AS ?domain) (SAMPLE(?r) AS ?range) (MAX(?maxC2) AS ?maxC)
        WHERE {
          {
            SELECT ?property ?r (SAMPLE(?d2) AS ?d) (MAX(?c) AS ?maxC2)
            WHERE {
              {
                SELECT ?subject ?property ?r (COUNT(?object) AS ?c)
                WHERE {
                  {
                    ?subject ?property ?object .
                    FILTER(?property != rdf:type)
                    FILTER(!isLiteral(?object))
                    OPTIONAL {
                      { ?object a ?r }
                      UNION
                      { GRAPH ?objG { ?object a ?r } }
                      FILTER(!isBlank(?r))
                    }
                  } UNION {
                    GRAPH ?g {
                      ?subject ?property ?object .
                      FILTER(?property != rdf:type)
                      FILTER(!isLiteral(?object))
                      OPTIONAL {
                        { ?object a ?r }
                        UNION
                        { GRAPH ?objG { ?object a ?r } }
                        FILTER(!isBlank(?r))
                      }
                    }
                  }
                }
                GROUP BY ?subject ?property ?r
              }
              OPTIONAL {
                { ?subject a ?d2 }
                UNION
                { GRAPH ?subjG { ?subject a ?d2 } }
                FILTER(!isBlank(?d2))
              }
            }
            GROUP BY ?property ?r
            HAVING(COUNT(DISTINCT ?d2) <= 1)
          }
        }
        GROUP BY ?property
        HAVING(COUNT(DISTINCT ?r) <= 1)
      }
    }
  }
}
""", datatype=XSD.string)
        return super().execute(endpoint, query)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Graph:
        """JSON execution: process arguments with strict type checking"""
        # Process endpoint
        endpoint_data = Operation.process_json(
            self.settings, arguments["endpoint"], self.context, variable_stack
        )
        if not isinstance(endpoint_data, URIRef):
            raise TypeError(
                f"ExtractObjectProperties operation expects 'endpoint' to be URIRef, got {type(endpoint_data)}"
            )

        return self.execute(endpoint_data)
