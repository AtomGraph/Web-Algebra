from typing import Any
import logging
from web_algebra.operation import Operation
from web_algebra.operations.linked_data.post import POST

class AddGenericService(POST):
    
    @classmethod
    def name(cls):
        return "ldh-AddGenericService"
    
    @classmethod
    def description(cls) -> str:
        return """Appends a generic SPARQL service to a LinkedDataHub document using service description.
        
        This tool creates a SPARQL service description that can be referenced and used within LinkedDataHub.
        The service description includes endpoint information and supported capabilities.
        
        This tool:
        - Creates an sd:Service resource with endpoint URI and supported languages
        - Posts the new service description to the target document
        - Supports optional title, description, fragment identifier, graph store, and authentication
        - Automatically sets SPARQL 1.1 Query and Update support"""

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string", 
                    "description": "The URI of the document to append the service to."
                },
                "endpoint": {
                    "type": "string", 
                    "description": "Endpoint URI of the SPARQL service."
                },
                "title": {
                    "type": "string", 
                    "description": "Title of the service."
                },
                "description": {
                    "type": "string", 
                    "description": "Optional description of the service."
                },
                "fragment": {
                    "type": "string", 
                    "description": "Optional fragment identifier for the service URI (e.g., 'my-service' creates #my-service)."
                },
                "graph_store": {
                    "type": "string", 
                    "description": "Optional Graph Store URI for the service."
                },
                "auth_user": {
                    "type": "string", 
                    "description": "Optional authorization username for the service."
                },
                "auth_pwd": {
                    "type": "string", 
                    "description": "Optional authorization password for the service."
                }
            },
            "required": ["url", "endpoint", "title"]
        }
    
    def execute(self, arguments: dict[str, str]) -> Any:
        """
        Creates a SPARQL service description resource, matching the reference shell script
        
        :arguments: A dictionary containing:
            - `url`: URI of the document to post to
            - `endpoint`: SPARQL endpoint URI
            - `title`: Title of the service
            - `description`: Optional description
            - `fragment`: Optional fragment identifier
            - `graph_store`: Optional graph store URI
            - `auth_user`: Optional auth username
            - `auth_pwd`: Optional auth password
        :return: Result from POST operation
        """
        url: str = Operation.execute_json(self.settings, arguments["url"], self.context)
        if not isinstance(url, str):
            raise ValueError("AddGenericService operation expects 'url' to be a string.")
        
        endpoint: str = Operation.execute_json(self.settings, arguments["endpoint"], self.context)
        if not isinstance(endpoint, str):
            raise ValueError("AddGenericService operation expects 'endpoint' to be a string.")
        
        title: str = Operation.execute_json(self.settings, arguments["title"], self.context)
        if not isinstance(title, str):
            raise ValueError("AddGenericService operation expects 'title' to be a string.")
        
        description = arguments.get("description")
        if description:
            description = Operation.execute_json(self.settings, description, self.context)
            if not isinstance(description, str):
                raise ValueError("AddGenericService operation expects 'description' to be a string.")
        
        fragment = arguments.get("fragment")
        if fragment:
            fragment = Operation.execute_json(self.settings, fragment, self.context)
            if not isinstance(fragment, str):
                raise ValueError("AddGenericService operation expects 'fragment' to be a string.")
        
        graph_store = arguments.get("graph_store")
        if graph_store:
            graph_store = Operation.execute_json(self.settings, graph_store, self.context)
            if not isinstance(graph_store, str):
                raise ValueError("AddGenericService operation expects 'graph_store' to be a string.")
                
        auth_user = arguments.get("auth_user")
        if auth_user:
            auth_user = Operation.execute_json(self.settings, auth_user, self.context)
            if not isinstance(auth_user, str):
                raise ValueError("AddGenericService operation expects 'auth_user' to be a string.")
                
        auth_pwd = arguments.get("auth_pwd")
        if auth_pwd:
            auth_pwd = Operation.execute_json(self.settings, auth_pwd, self.context)
            if not isinstance(auth_pwd, str):
                raise ValueError("AddGenericService operation expects 'auth_pwd' to be a string.")
        
        logging.info(f"Creating service description for document <%s> with endpoint <%s>", url, endpoint)
        
        # Create subject URI (fragment or blank node) - matching shell script logic
        if fragment:
            subject_id = f"#{fragment}"  # relative URI that will be resolved against the request URI
        else:
            subject_id = "_:subject"
        
        # Build JSON-LD structure for the service description - matching shell script output
        data = {
            "@context": {
                "ldh": "https://w3id.org/atomgraph/linkeddatahub#",
                "dh": "https://www.w3.org/ns/ldt/document-hierarchy#",
                "a": "https://w3id.org/atomgraph/core#",
                "dct": "http://purl.org/dc/terms/",
                "foaf": "http://xmlns.com/foaf/0.1/",
                "sd": "http://www.w3.org/ns/sparql-service-description#"
            },
            "@id": subject_id,
            "@type": "sd:Service",
            "dct:title": title,
            "sd:endpoint": {
                "@id": endpoint
            },
            "sd:supportedLanguage": [
                {
                    "@id": "sd:SPARQL11Query"
                },
                {
                    "@id": "sd:SPARQL11Update"
                }
            ]
        }
        
        # Add optional properties - matching shell script conditional logic
        if graph_store:
            data["a:graphStore"] = {
                "@id": graph_store
            }
            
        if auth_user:
            data["a:authUser"] = auth_user
            
        if auth_pwd:
            data["a:authPwd"] = auth_pwd
            
        if description:
            data["dct:description"] = description
        
        logging.info(f"Posting service description with JSON-LD data: {data}")
        
        # POST the JSON-LD content to the target URI
        return super().execute({
            "url": url,
            "data": data
        })
