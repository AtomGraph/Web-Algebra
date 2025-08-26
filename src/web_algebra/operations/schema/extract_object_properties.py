from typing import Any
import rdflib
from rdflib import URIRef, Literal
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
        """Pure function: extract OWL object properties with RDFLib terms"""
        query = Literal("""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

CONSTRUCT {
  ?property a owl:ObjectProperty ;
           rdfs:domain ?domain ;
           rdfs:range ?range .
}
WHERE {
  {
    ?subject ?property ?object .
    FILTER(?property != rdf:type)
    FILTER(!isLiteral(?object))
    
    OPTIONAL { 
      { ?subject a ?domain }
      UNION 
      { GRAPH ?subjG { ?subject a ?domain } }
    }
    OPTIONAL { 
      { ?object a ?range }
      UNION 
      { GRAPH ?objG { ?object a ?range } }
    }
  } UNION {
    GRAPH ?g {
      ?subject ?property ?object .
      FILTER(?property != rdf:type)
      FILTER(!isLiteral(?object))
      
      OPTIONAL { 
        { ?subject a ?domain }
        UNION 
        { GRAPH ?subjG { ?subject a ?domain } }
      }
      OPTIONAL { 
        { ?object a ?range }
        UNION 
        { GRAPH ?objG { ?object a ?range } }
      }
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
                f"ExtractObjectProperties operation expects 'endpoint' to be URIRef, got {type(endpoint_data)}"
            )

        return self.execute(endpoint_data)
