from typing import ClassVar
from web_algebra.operation import Operation
from web_algebra.schema_extraction import SchemaExtraction


class ExtractObjectProperties(SchemaExtraction, Operation):
    """formal-semantics.md §4.6. The query is REST-VKG's, so the two
    serializations extract the same schema; `%SCOPE%` is where the
    `bindings` VALUES block goes."""

    QUERY: ClassVar[str] = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
CONSTRUCT {
  ?property a owl:ObjectProperty ; rdfs:domain ?domain ; rdfs:range ?range .
  ?functional a owl:FunctionalProperty .
}
WHERE {
  {
    SELECT ?property ?range (IF(?domains = 1, ?aDomain, ?UNDEF) AS ?domain) (IF(?maxC = 1, ?property, ?UNDEF) AS ?functional)
    WHERE {
      {
        SELECT ?property ?domains ?aDomain ?maxC (SAMPLE(?objectType) AS ?range)
        WHERE {
          {
            SELECT ?property (MAX(?c) AS ?maxC) (COUNT(DISTINCT ?type) AS ?domains) (SAMPLE(?type) AS ?aDomain) (SAMPLE(?anObject) AS ?sampleObject)
            WHERE {
              {
                SELECT ?subject ?property (COUNT(?object) AS ?c) (SAMPLE(?object) AS ?anObject)
                WHERE {
                  %SCOPE%
                  { ?subject ?property ?object . FILTER(?property != rdf:type) FILTER(!isLiteral(?object)) }
                  UNION
                  { GRAPH ?g { ?subject ?property ?object . FILTER(?property != rdf:type) FILTER(!isLiteral(?object)) } }
                }
                GROUP BY ?subject ?property
              }
              OPTIONAL {
                SELECT ?subject (SAMPLE(?d) AS ?type) WHERE {
                  %SCOPE%
                  { ?subject a ?d } UNION { GRAPH ?subjG { ?subject a ?d } }
                  FILTER(!isBlank(?d))
                } GROUP BY ?subject
              }
            }
            GROUP BY ?property
          }
          OPTIONAL {
            { ?sampleObject a ?objectType } UNION { GRAPH ?objG { ?sampleObject a ?objectType } }
            FILTER(!isBlank(?objectType))
          }
        }
        GROUP BY ?property ?domains ?aDomain ?maxC
      }
    }
  }
}
"""

    @classmethod
    def description(cls) -> str:
        return "Extracts OWL object properties (and functional properties, closed-world) from IRI-valued predicates in an RDF dataset, optionally scoped to the subjects in 'bindings'."
