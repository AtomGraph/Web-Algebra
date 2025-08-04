from typing import Any
import logging
from datetime import datetime
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from web_algebra.operation import Operation
from web_algebra.operations.linked_data.put import PUT

class CreateContainer(PUT):
    
    @classmethod
    def name(cls):
        return "ldh-CreateContainer"
    
    @classmethod
    def description(cls) -> str:
        return """Creates a LinkedDataHub Container document with proper structure.
        
        IMPORTANT CONSTRAINTS:
        - The document URL needs to end with a trailing slash (/)
        - Documents can only be created at URLs relative to existing container's URL
        - Example: if https://localhost/blog/ exists, you cannot create https://localhost/blog/posts/something/
          before creating https://localhost/blog/posts/ 
        - LinkedDataHub automatically manages timestamps (dct:created, dct:modified)
        - LinkedDataHub automatically manages parent-child relationships (sioc:has_parent) based on URI hierarchy"""

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string", 
                    "description": "The URI for the container document."
                },
                "title": {
                    "type": "string", 
                    "description": "The title of the container (required)."
                },
                "description": {
                    "type": "string", 
                    "description": "Optional description of the container."
                }
            },
            "required": ["url", "title"]
        }
    
    def execute(self, arguments: dict[str, str]) -> Any:
        """
        Creates a LinkedDataHub v5 Container document
        
        :arguments: A dictionary containing:
            - `url`: The URL for the container document
            - `title`: The title of the container (required)
            - `description`: Optional description of the container
        :return: Result from PUT operation
        """
        url: str = Operation.execute_json(self.settings, arguments["url"], self.context)
        if not isinstance(url, str):
            raise ValueError("ldh-CreateContainer operation expects 'url' to be a string.")
        
        title: str = Operation.execute_json(self.settings, arguments["title"], self.context)
        if not isinstance(title, str):
            raise ValueError("ldh-CreateContainer operation expects 'title' to be a string.")
        
        description = arguments.get("description")
        if description:
            description = Operation.execute_json(self.settings, description, self.context)
            if not isinstance(description, str):
                raise ValueError("ldh-CreateContainer operation expects 'description' to be a string.")
        
        logging.info(f"Creating LinkedDataHub Container at <%s> with title '%s'", url, title)
        
        data = {
            "@context": {
                "ldh": "https://w3id.org/atomgraph/linkeddatahub#",
                "dh": "https://www.w3.org/ns/ldt/document-hierarchy#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "dct": "http://purl.org/dc/terms/",
                "sioc": "http://rdfs.org/sioc/ns#",
                "xsd": "http://www.w3.org/2001/XMLSchema#"
            },
            "@id": url,
            "@type": "dh:Container",
            "dct:title": title,
            # default content block
            "rdf:_1": {
                "@type": "ldh:Object",
                "rdf:value": {
                    "@id": "ldh:ChildrenView"
                }
            }
        }
        
        # Add optional description
        if description:
            data["dct:description"] = description
                
        # Call parent PUT execute with the constructed data
        return super().execute({
            "url": url,
            "data": data
        })

    def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        try:
            result = self.execute(arguments)
            url = Operation.execute_json(self.settings, arguments["url"], self.context)
            title = Operation.execute_json(self.settings, arguments["title"], self.context)
            return [types.TextContent(
                type="text", 
                text=f"Created LinkedDataHub Container: {url}\nTitle: {title}\nResult: {result}"
            )]
        except Exception as e:
            return [types.TextContent(
                type="text", 
                text=f"Error creating container: {str(e)}"
            )]
