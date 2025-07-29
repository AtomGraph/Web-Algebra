from typing import Any
import logging
from web_algebra.operation import Operation
from web_algebra.operations.linked_data.post import POST

class AddView(POST):
    
    @classmethod
    def name(cls):
        return "ldh-AddView"
    
    @classmethod
    def description(cls) -> str:
        return """Appends a view for SPARQL SELECT query results to a LinkedDataHub document.
        
        This tool creates a View that displays data from SPARQL SELECT query resources.
        The view references an existing sp:Select resource (not a query string) and can display 
        results using different display modes (list, grid, etc.).
        
        This tool:
        - Creates an ldh:View resource linked to an existing sp:Select query resource
        - Configures optional display mode for the view
        - Posts the new view resource to the target document
        - Supports optional title, description, fragment identifier, and display mode
        
        Possible display modes include:
        - https://w3id.org/atomgraph/client#ReadMode: Default read mode for displaying resources
        - https://w3id.org/atomgraph/client#ListMode: List display of results
        - https://w3id.org/atomgraph/client#GridMode: Grid display of results
        - https://w3id.org/atomgraph/client#GraphMode: Graph visualization of resources
        - https://w3id.org/atomgraph/client#MapMode: Map display for geographic data

        IMPORTANT: All variables projected by the SELECT query will be DESCRIBE'd by LinkedDataHub,
        meaning that the view will fetch complete RDF descriptions for each result resource. This can
        result in very large graph results and may not be suitable for all SELECT queries, especially
        those returning many resources or aggregate/computed values.

        Note: The query parameter must be a URI of an existing sp:Select resource, not a SPARQL query string."""

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string", 
                    "description": "The URI of the document to append the view to."
                },
                "query": {
                    "type": "string", 
                    "description": "URI of an existing sp:Select query resource to visualize (not a SPARQL query string)."
                },
                "title": {
                    "type": "string", 
                    "description": "Title of the view."
                },
                "description": {
                    "type": "string", 
                    "description": "Optional description of the view."
                },
                "fragment": {
                    "type": "string", 
                    "description": "Optional fragment identifier for the view URI (e.g., 'my-view' creates #my-view)."
                },
                "mode": {
                    "type": "string", 
                    "description": "Optional URI of the display mode for the view.",
                    "enum": [
                        "https://w3id.org/atomgraph/client#ReadMode",
                        "https://w3id.org/atomgraph/client#ListMode",
                        "https://w3id.org/atomgraph/client#GridMode",
                        "https://w3id.org/atomgraph/client#GraphMode",
                        "https://w3id.org/atomgraph/client#MapMode"
                    ]
                }
            },
            "required": ["url", "query", "title"]
        }
    
    def execute(self, arguments: dict[str, str]) -> Any:
        """
        Creates a SPARQL result set view resource, matching the reference shell script
        
        :arguments: A dictionary containing:
            - `url`: URI of the document to post to
            - `query`: URI of an existing sp:Select query resource (not a query string)
            - `title`: Title of the view
            - `description`: Optional description
            - `fragment`: Optional fragment identifier
            - `mode`: Optional URI of the display mode
        :return: Result from POST operation
        """
        url: str = Operation.execute_json(self.settings, arguments["url"], self.context)
        if not isinstance(url, str):
            raise ValueError("AddView operation expects 'url' to be a string.")
        
        query: str = Operation.execute_json(self.settings, arguments["query"], self.context)
        if not isinstance(query, str):
            raise ValueError("AddView operation expects 'query' to be a URI string referencing an sp:Select resource.")
        
        title: str = Operation.execute_json(self.settings, arguments["title"], self.context)
        if not isinstance(title, str):
            raise ValueError("AddView operation expects 'title' to be a string.")
        
        description = arguments.get("description")
        if description:
            description = Operation.execute_json(self.settings, description, self.context)
            if not isinstance(description, str):
                raise ValueError("AddView operation expects 'description' to be a string.")
        
        fragment = arguments.get("fragment")
        if fragment:
            fragment = Operation.execute_json(self.settings, fragment, self.context)
            if not isinstance(fragment, str):
                raise ValueError("AddView operation expects 'fragment' to be a string.")
        
        mode = arguments.get("mode")
        if mode:
            mode = Operation.execute_json(self.settings, mode, self.context)
            if not isinstance(mode, str):
                raise ValueError("AddView operation expects 'mode' to be a string.")
        
        logging.info(f"Creating View for document <%s> with sp:Select resource <%s>", url, query)
        
        # Create subject URI (fragment or blank node) - matching shell script logic
        if fragment:
            subject_id = f"#{fragment}"  # relative URI that will be resolved against the request URI
        else:
            subject_id = "_:subject"
        
        # Build JSON-LD structure for the view - matching shell script output
        data = {
            "@context": {
                "ldh": "https://w3id.org/atomgraph/linkeddatahub#",
                "dct": "http://purl.org/dc/terms/",
                "spin": "http://spinrdf.org/spin#"
            },
            "@id": subject_id,
            "@type": "ldh:View",
            "dct:title": title,
            "spin:query": {
                "@id": query
            }
        }
        
        # Add optional properties - matching shell script conditional logic
        if description:
            data["dct:description"] = description
        
        if mode:
            # Add the ac: namespace to context when mode is used
            data["@context"]["ac"] = "https://w3id.org/atomgraph/client#"
            data["ac:mode"] = {
                "@id": mode
            }
        
        logging.info(f"Posting View with JSON-LD data: {data}")
        
        # POST the JSON-LD content to the target URI
        return super().execute({
            "url": url,
            "data": data
        })
