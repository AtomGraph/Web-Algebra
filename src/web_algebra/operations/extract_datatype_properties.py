from typing import Any
from web_algebra.operations.construct import CONSTRUCT

class ExtractDatatypeProperties(CONSTRUCT):

    @classmethod
    def description(cls) -> str:
        return "Extracts OWL datatypes properties from an RDF dataset."

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
  ?property a owl:DatatypeProperty ;
           rdfs:domain ?domain ;
           rdfs:range ?datatype .
}
WHERE {
  {
    ?subject ?property ?literal .
    FILTER(?property != rdf:type)
    FILTER(isLiteral(?literal))
    
    OPTIONAL { 
      { ?subject a ?domain }
      UNION 
      { GRAPH ?subjG { ?subject a ?domain } }
    }
    BIND(datatype(?literal) as ?datatype)
  } UNION {
    GRAPH ?g {
      ?subject ?property ?literal .
      FILTER(?property != rdf:type)
      FILTER(isLiteral(?literal))
      
      OPTIONAL { 
        { ?subject a ?domain }
        UNION 
        { GRAPH ?subjG { ?subject a ?domain } }
      }
      BIND(datatype(?literal) as ?datatype)
    }
  }
}
"""
        return super().execute(arguments)
