from typing import Any
import logging
from datetime import datetime
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from web_algebra.operation import Operation
from web_algebra.operations.linked_data.put import PUT

class CreateItem(PUT):
    
    @classmethod
    def name(cls):
        return "ldh-CreateItem"
    
    @classmethod
    def description(cls) -> str:
        return """Creates a LinkedDataHub Item document with proper structure.
        
        IMPORTANT CONSTRAINTS:
        - Documents can only be created at URLs relative to existing container's URL
        - Example: if https://localhost/blog/ exists, you cannot create https://localhost/blog/posts/something/
          before creating https://localhost/blog/posts/
        - LinkedDataHub automatically manages timestamps (dct:created, dct:modified)
        - LinkedDataHub automatically manages parent-child relationships (sioc:has_parent) based on URI hierarchy
        
        Use this tool to create the item hierarchy from root down to your target location."""

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string", 
                    "description": "The URI for the item document."
                },
                "title": {
                    "type": "string", 
                    "description": "The title of the item (required)."
                },
                "description": {
                    "type": "string", 
                    "description": "Optional description of the item."
                }
            },
            "required": ["url", "title"]
        }
    
    def execute(self, arguments: dict[str, str]) -> Any:
        """
        Creates a LinkedDataHub Item document
        
        :arguments: A dictionary containing:
            - `url`: The URL for the item document
            - `title`: The title of the item (required)
            - `description`: Optional description of the item
        :return: Result from PUT operation
        """
        url: str = Operation.execute_json(self.settings, arguments["url"], self.context)
        if not isinstance(url, str):
            raise ValueError("ldh-CreateItem operation expects 'url' to be a string.")
        
        title: str = Operation.execute_json(self.settings, arguments["title"], self.context)
        if not isinstance(title, str):
            raise ValueError("ldh-CreateItem operation expects 'title' to be a string.")
        
        description = arguments.get("description")
        if description:
            description = Operation.execute_json(self.settings, description, self.context)
            if not isinstance(description, str):
                raise ValueError("ldh-CreateItem operation expects 'description' to be a string.")
        
        logging.info(f"Creating LinkedDataHub Item at <%s> with title '%s'", url, title)
                
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
            "@type": "dh:Item",
            "dct:title": title
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
                text=f"Created LinkedDataHub Item: {url}\nTitle: {title}\nResult: {result}"
            )]
        except Exception as e:
            return [types.TextContent(
                type="text", 
                text=f"Error creating item: {str(e)}"
            )]
