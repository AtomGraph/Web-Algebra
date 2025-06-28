from typing import Any
from web_algebra.operations.sparql.construct import CONSTRUCT

class ExtractClasses(CONSTRUCT):

    @classmethod
    def description(cls) -> str:
        return "Extracts OWL classes from an RDF dataset."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string"}
            },
            "required": ["endpoint"]
        }

    def execute(self, arguments: dict[str, Any]) -> dict:
        arguments["query"] = """
PREFIX  owl:  <http://www.w3.org/2002/07/owl#>
PREFIX  rdfs: <http://www.w3.org/2000/01/rdf-schema#>

CONSTRUCT 
  { 
    ?class a owl:Class .
  }
WHERE
  {   { ?instance  a  ?class
        FILTER ( ! isBlank(?class) )
      }
    UNION
      { GRAPH ?g
          { ?instance  a  ?class
            FILTER ( ! isBlank(?class) )
          }
      }
  }
"""
        return super().execute(arguments)
