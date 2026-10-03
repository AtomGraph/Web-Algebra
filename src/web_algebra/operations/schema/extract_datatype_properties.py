from typing import ClassVar
from web_algebra.operation import Operation
from web_algebra.schema_extraction import SchemaExtraction


class ExtractDatatypeProperties(SchemaExtraction, Operation):
    """formal-semantics.md §4.6. The query is REST-VKG's, so the two
    serializations extract the same schema; `%SCOPE%` is where the
    `bindings` VALUES block goes."""

    QUERY: ClassVar[str] = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
CONSTRUCT {
  ?property a owl:DatatypeProperty ; rdfs:domain ?domain ; rdfs:range ?datatype .
  ?domain rdfs:subClassOf ?restriction .
  ?restriction a owl:Restriction ; owl:onProperty ?property ; owl:maxQualifiedCardinality ?maxCardinality ; owl:onDataRange ?datatype .
}
WHERE {
  {
    SELECT ?property ?datatype (IF(?domains = 1, ?aDomain, ?UNDEF) AS ?domain) (IF(?maxC = 1 && ?domains = 1, 1, ?UNDEF) AS ?maxCardinality)
    WHERE {
      {
        SELECT ?property ?datatype (MAX(?c) AS ?maxC) (COUNT(DISTINCT ?type) AS ?domains) (SAMPLE(?type) AS ?aDomain)
        WHERE {
          {
            SELECT ?subject ?property ?datatype (COUNT(?literal) AS ?c)
            WHERE {
              %SCOPE%
              { ?subject ?property ?literal . FILTER(?property != rdf:type) FILTER(isLiteral(?literal)) BIND(datatype(?literal) AS ?datatype) }
              UNION
              { GRAPH ?g { ?subject ?property ?literal . FILTER(?property != rdf:type) FILTER(isLiteral(?literal)) BIND(datatype(?literal) AS ?datatype) } }
            }
            GROUP BY ?subject ?property ?datatype
          }
          OPTIONAL {
            SELECT ?subject (SAMPLE(?d) AS ?type) WHERE {
              %SCOPE%
              { ?subject a ?d } UNION { GRAPH ?subjG { ?subject a ?d } }
              FILTER(!isBlank(?d))
            } GROUP BY ?subject
          }
        }
        GROUP BY ?property ?datatype
      }
    }
  }
  OPTIONAL { FILTER(BOUND(?maxCardinality)) BIND(BNODE() AS ?restriction) }
}
"""

    @classmethod
    def description(cls) -> str:
        return "Extracts OWL datatype properties from literal-valued predicates in an RDF dataset, optionally scoped to the subjects in 'bindings'."
