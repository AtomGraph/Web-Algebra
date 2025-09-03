from typing import Any, Optional
import logging
import urllib.parse
import rdflib
from rdflib import URIRef, Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.operation import Operation
from web_algebra.operations.linked_data.put import PUT
from rdflib.query import Result


class CreateItem(PUT):
    @classmethod
    def name(cls):
        return "ldh-CreateItem"

    @classmethod
    def description(cls) -> str:
        return """Creates a LinkedDataHub Item document with proper structure.
        
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
                "container": {
                    "type": "string",
                    "description": "URI of the parent container",
                },
                "title": {"type": "string", "description": "The title of the item"},
                "slug": {
                    "type": "string",
                    "description": "URL path segment (optional)",
                },
            },
            "required": ["container", "title"],
        }

    def execute(
        self,
        container_uri: rdflib.URIRef,
        title: rdflib.Literal,
        slug: Optional[rdflib.Literal] = None,
    ) -> Result:
        """Pure function: create item with RDFLib terms"""
        if not isinstance(container_uri, URIRef):
            raise TypeError(
                f"CreateItem.execute expects container_uri to be URIRef, got {type(container_uri)}"
            )
        if not isinstance(title, Literal):
            raise TypeError(
                f"CreateItem.execute expects title to be Literal, got {type(title)}"
            )
        if slug is not None and not isinstance(slug, Literal):
            raise TypeError(
                f"CreateItem.execute expects slug to be Literal or None, got {type(slug)}"
            )

        # URL-encode slug or use title
        slug_str = urllib.parse.quote(str(slug) if slug else str(title), safe="")

        # Construct URL
        container_str = str(container_uri)
        if not container_str.endswith("/"):
            container_str += "/"
        url = container_str + slug_str + "/"

        logging.info("Creating LinkedDataHub Item at <%s> with title '%s'", url, title)

        # Create JSON-LD data
        data = {
            "@context": {
                "ldh": "https://w3id.org/atomgraph/linkeddatahub#",
                "dh": "https://www.w3.org/ns/ldt/document-hierarchy#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "dct": "http://purl.org/dc/terms/",
                "sioc": "http://rdfs.org/sioc/ns#",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
            },
            "@id": url,
            "@type": "dh:Item",
            "dct:title": str(title),
        }

        # Create graph and call parent PUT operation
        import json

        graph = rdflib.Graph()
        graph.parse(data=json.dumps(data), format="json-ld", publicID=url)

        # Call parent PUT execute method
        return super().execute(URIRef(url), graph)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Result:
        """JSON execution: process arguments with strict type checking"""
        # Process container URI
        container_data = Operation.process_json(
            self.settings, arguments["container"], self.context, variable_stack
        )
        container_uri = Operation.json_to_rdflib(container_data)
        if not isinstance(container_uri, URIRef):
            raise TypeError(
                f"ldh-CreateItem operation expects 'container' to be URIRef, got {type(container_uri)}"
            )

        # Process title
        title_data = Operation.process_json(
            self.settings, arguments["title"], self.context, variable_stack
        )
        title = Operation.json_to_rdflib(title_data)
        if not isinstance(title, Literal):
            raise TypeError(
                f"ldh-CreateItem operation expects 'title' to be Literal, got {type(title)}"
            )

        # Process optional slug
        slug = None
        if "slug" in arguments:
            slug_data = Operation.process_json(
                self.settings, arguments["slug"], self.context, variable_stack
            )
            slug = Operation.json_to_rdflib(slug_data)
            if not isinstance(slug, Literal):
                raise TypeError(
                    f"ldh-CreateItem operation expects 'slug' to be Literal, got {type(slug)}"
                )

        return self.execute(container_uri, title, slug)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        container_uri = URIRef(arguments["container"])
        title = Literal(arguments["title"], datatype=XSD.string)
        slug = (
            Literal(arguments.get("slug", ""), datatype=XSD.string)
            if "slug" in arguments
            else None
        )

        result = self.execute(container_uri, title, slug)

        # Extract URL from PUT result
        url_binding = result.bindings[0]["url"]
        return [
            types.TextContent(
                type="text", text=f"Item created successfully at: {url_binding}"
            )
        ]
