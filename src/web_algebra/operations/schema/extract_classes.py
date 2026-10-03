from typing import ClassVar
from web_algebra.operation import Operation
from web_algebra.schema_extraction import SchemaExtraction


class ExtractClasses(SchemaExtraction, Operation):
    """formal-semantics.md §4.6. The query is REST-VKG's, so the two
    serializations extract the same schema; `%SCOPE%` is where the
    `bindings` VALUES block goes."""

    QUERY: ClassVar[str] = """
PREFIX  owl:  <http://www.w3.org/2002/07/owl#>
PREFIX  rdfs: <http://www.w3.org/2000/01/rdf-schema#>

CONSTRUCT
  {
    ?class a owl:Class .
  }
WHERE
  {   %SCOPE%
      { ?subject  a  ?class
        FILTER ( ! isBlank(?class) )
      }
    UNION
      { GRAPH ?g
          { ?subject  a  ?class
            FILTER ( ! isBlank(?class) )
          }
      }
  }
"""

    @classmethod
    def description(cls) -> str:
        return "Extracts OWL classes (owl:Class candidates) from rdf:type usage in an RDF dataset, optionally scoped to the subjects in 'bindings'."
