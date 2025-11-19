import rdflib
from rdflib import URIRef, Literal
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

    def execute(self, endpoint: URIRef) -> rdflib.Graph:
        """Pure function: extract OWL object properties with RDFLib terms

        Infers functional properties using closed world assumption:
        - Counts max cardinality by examining all subjects in the dataset
        - Creates OWL restriction with maxQualifiedCardinality
        - When maxC = 1, property is inferred to be functional in this dataset
        - Note: Inference based solely on present data, not formal ontology definitions
        """
        query = Literal("""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

CONSTRUCT {
  # Basic property metadata - constructed for ALL properties
  ?property a owl:ObjectProperty ;
           rdfs:domain ?domain ;
           rdfs:range ?range .

  # Restriction triples - only constructed when ?restriction and ?maxCardinality are bound
  # This happens only for functional properties (maxC = 1)
  ?domain rdfs:subClassOf ?restriction .

  ?restriction a owl:Restriction ;
               owl:onProperty ?property ;
               owl:maxQualifiedCardinality ?maxCardinality ;
               owl:onClass ?range .
}
WHERE {
  {
    # Outermost SELECT: Conditionally bind maxCardinality only when maxC = 1
    # The IF expression makes ?maxCardinality unbound for non-functional properties
    SELECT ?domain ?property ?range (IF(?maxC = 1, ?maxC, ?UNDEF) AS ?maxCardinality)
    WHERE {
      {
        # Outer SELECT: Aggregate to single domain/range per property
        # Filter to properties with unambiguous range (COUNT DISTINCT <= 1)
        # Get final max cardinality value
        SELECT ?property (SAMPLE(?d) AS ?domain) (SAMPLE(?r) AS ?range) (MAX(?maxC2) AS ?maxC)
        WHERE {
          {
            # Middle SELECT: Get max cardinality per property-range pair
            # Filter to properties with unambiguous domain (COUNT DISTINCT <= 1)
            SELECT ?property ?r (SAMPLE(?d2) AS ?d) (MAX(?c) AS ?maxC2)
            WHERE {
              {
                # Innermost SELECT: Count objects per subject-property-range triple
                # This gives us cardinality for each individual subject
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
                      FILTER (!isBlank(?r))
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
                        FILTER (!isBlank(?r))
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

  # Create blank node for restriction ONLY when ?maxCardinality is bound (functional properties)
  # This OPTIONAL block does NOT filter out rows - all properties are still returned
  # For functional properties: ?restriction is bound, and restriction triples are constructed
  # For non-functional properties: ?restriction is unbound, no restriction triples created
  OPTIONAL {
    FILTER(BOUND(?maxCardinality))
    BIND(BNODE() AS ?restriction)
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
                f"ExtractObjectProperties operation expects 'endpoint' to be URIRef, got {type(endpoint_data)}"
            )

        return self.execute(endpoint_data)
