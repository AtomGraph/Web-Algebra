from typing import Any
import rdflib
from rdflib import URIRef, Literal
from web_algebra.operations.sparql.construct import CONSTRUCT
from web_algebra.operation import Operation


class ExtractClasses(CONSTRUCT):
    @classmethod
    def description(cls) -> str:
        return "Extracts OWL classes from an RDF dataset."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {"endpoint": {"type": "string"}},
            "required": ["endpoint"],
        }

    def execute(self, endpoint: URIRef) -> rdflib.Graph:
        """Pure function: extract OWL classes with RDFLib terms"""
        query = Literal("""
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
""")
        return super().execute(endpoint, query)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> rdflib.Graph:
        """JSON execution: process arguments with strict type checking"""
        # Process endpoint
        endpoint_data = Operation.process_json(
            self.settings, arguments["endpoint"], self.context, variable_stack
        )
        if not isinstance(endpoint_data, URIRef):
            raise TypeError(
                f"ExtractClasses operation expects 'endpoint' to be URIRef, got {type(endpoint_data)}"
            )

        return self.execute(endpoint_data)
