from typing import Any
import logging
from web_algebra.operation import Operation
from web_algebra.operations.linked_data.post import POST

class AddSelect(POST):
    
    @classmethod
    def name(cls):
        return "ldh-AddSelect"
    
    @classmethod
    def description(cls) -> str:
        return """Creates a SPARQL SELECT query resource in a document.
        
        This tool creates a SPARQL SELECT query that can be executed and referenced within LinkedDataHub.
        The query can be used for charts, views, or other data processing operations.
        
        This tool:
        - Creates a sp:Select resource with the SPARQL query text
        - Posts the new SELECT query resource to the target document
        - Supports optional title, description, fragment identifier, and service URI
        Note: the service URI is _not_ the SPARQL endpoint URL but an instance of `sd:Service` that describes the SPARQL service capabilities (and contains the endpoint URL).
        The service URI can be used to reference the SPARQL service in other operations.
        """

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string", 
                    "description": "The URI of the document to append the SELECT query to."
                },
                "query": {
                    "type": "string", 
                    "description": "The SPARQL SELECT query string."
                },
                "title": {
                    "type": "string", 
                    "description": "Title of the SELECT query."
                },
                "description": {
                    "type": "string", 
                    "description": "Optional description of the SELECT query."
                },
                "fragment": {
                    "type": "string", 
                    "description": "Optional fragment identifier for the query URI (e.g., 'my-query' creates #my-query)."
                },
                "service": {
                    "type": "string", 
                    "description": "Optional URI of the SPARQL service/endpoint specific to this query. Note: the service URI is _not_ the SPARQL endpoint URL but an instance of `sd:Service` that describes the SPARQL service capabilities (and contains the endpoint URL)."
                }
            },
            "required": ["url", "query", "title"]
        }
    
    def execute(self, arguments: dict[str, str]) -> Any:
        """
        Creates a SPARQL SELECT query resource, matching the reference shell script
        
        :arguments: A dictionary containing:
            - `url`: URI of the document to post to
            - `query`: SPARQL SELECT query string
            - `title`: Title of the query
            - `description`: Optional description
            - `fragment`: Optional fragment identifier
            - `service`: Optional SPARQL service URI (instance of `sd:Service`, not the endpoint URL)
        :return: Result from POST operation
        """
        url: str = Operation.execute_json(self.settings, arguments["url"], self.context)
        if not isinstance(url, str):
            raise ValueError("AddSelect operation expects 'url' to be a string.")
        
        query: str = Operation.execute_json(self.settings, arguments["query"], self.context)
        if not isinstance(query, str):
            raise ValueError("AddSelect operation expects 'query' to be a string.")
        
        title: str = Operation.execute_json(self.settings, arguments["title"], self.context)
        if not isinstance(title, str):
            raise ValueError("AddSelect operation expects 'title' to be a string.")
        
        description = arguments.get("description")
        if description:
            description = Operation.execute_json(self.settings, description, self.context)
            if not isinstance(description, str):
                raise ValueError("AddSelect operation expects 'description' to be a string.")
        
        fragment = arguments.get("fragment")
        if fragment:
            fragment = Operation.execute_json(self.settings, fragment, self.context)
            if not isinstance(fragment, str):
                raise ValueError("AddSelect operation expects 'fragment' to be a string.")
        
        service = arguments.get("service")
        if service:
            service = Operation.execute_json(self.settings, service, self.context)
            if not isinstance(service, str):
                raise ValueError("AddSelect operation expects 'service' to be a string.")
        
        logging.info(f"Creating SELECT query for document <%s> with title '%s'", url, title)
        
        # Create subject URI (fragment or blank node) - matching shell script logic
        if fragment:
            subject_id = f"#{fragment}"  # relative URI that will be resolved against the request URI
        else:
            subject_id = "_:subject"
        
        # Build JSON-LD structure for the SELECT query - matching shell script output
        data = {
            "@context": {
                "ldh": "https://w3id.org/atomgraph/linkeddatahub#",
                "dct": "http://purl.org/dc/terms/",
                "sp": "http://spinrdf.org/sp#"
            },
            "@id": subject_id,
            "@type": "sp:Select",
            "dct:title": title,
            "sp:text": query
        }
        
        # Add optional properties - matching shell script conditional logic
        if service:
            data["ldh:service"] = {
                "@id": service
            }
            
        if description:
            data["dct:description"] = description
        
        logging.info(f"Posting SELECT query with JSON-LD data: {data}")
        
        # POST the JSON-LD content to the target URI
        return super().execute({
            "url": url,
            "data": data
        })
