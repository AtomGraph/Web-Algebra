from typing import Any
from web_algebra.operations.sparql.construct import CONSTRUCT

class ExtractObjectProperties(CONSTRUCT):

    @classmethod
    def description(cls) -> str:
        return "Extracts OWL object properties from an RDF dataset."

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
"""
        return super().execute(arguments)
