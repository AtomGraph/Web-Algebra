from typing import Any
import logging
import urllib.parse
import rdflib
from rdflib import URIRef, Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation
from web_algebra.operations.linked_data.put import PUT
from rdflib.query import Result


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
                "parent": {
                    "type": "string",
                    "description": "URI of the parent container",
                },
                "title": {
                    "type": "string",
                    "description": "The title of the container",
                },
                "slug": {
                    "type": "string",
                    "description": "URL path segment (optional)",
                },
                "description": {
                    "type": "string",
                    "description": "Description (optional)",
                },
            },
            "required": ["parent", "title"],
        }

    def execute(
        self,
        parent_uri: rdflib.URIRef,
        title: rdflib.Literal,
        slug: rdflib.Literal = None,
        description: rdflib.Literal = None,
    ) -> Result:
        """Pure function: create container with RDFLib terms"""
        if not isinstance(parent_uri, URIRef):
            raise TypeError(
                f"CreateContainer.execute expects parent_uri to be URIRef, got {type(parent_uri)}"
            )
        if not isinstance(title, Literal):
            raise TypeError(
                f"CreateContainer.execute expects title to be Literal, got {type(title)}"
            )
        if slug is not None and not isinstance(slug, Literal):
            raise TypeError(
                f"CreateContainer.execute expects slug to be Literal or None, got {type(slug)}"
            )
        if description is not None and not isinstance(description, Literal):
            raise TypeError(
                f"CreateContainer.execute expects description to be Literal or None, got {type(description)}"
            )
        # URL-encode slug or use title
        slug_str = urllib.parse.quote(str(slug) if slug else str(title), safe="")

        # Construct URL
        parent_str = str(parent_uri)
        if not parent_str.endswith("/"):
            parent_str += "/"
        url = parent_str + slug_str + "/"

        logging.info(
            "Creating LinkedDataHub Container at <%s> with title '%s'", url, title
        )

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
            "@type": "dh:Container",
            "dct:title": str(title),
            "rdf:_1": {"@type": "ldh:Object", "rdf:value": {"@id": "ldh:ChildrenView"}},
        }

        if description:
            data["dct:description"] = str(description)

        # Create graph and call parent PUT operation
        import json

        graph = rdflib.Graph()
        graph.parse(data=json.dumps(data), format="json-ld", base=url)

        # Call parent PUT execute method
        return super().execute(URIRef(url), graph)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Result:
        """JSON execution: process arguments and call pure function"""
        # Process parent URI
        parent_data = Operation.process_json(
            self.settings, arguments["parent"], self.context, variable_stack
        )
        parent_uri = Operation.json_to_rdflib(parent_data)
        if not isinstance(parent_uri, URIRef):
            raise TypeError(
                f"ldh-CreateContainer operation expects 'parent' to be URIRef, got {type(parent_uri)}"
            )

        # Process title
        title_data = Operation.process_json(
            self.settings, arguments["title"], self.context, variable_stack
        )
        title = Operation.json_to_rdflib(title_data)
        if not isinstance(title, Literal):
            raise TypeError(
                f"ldh-CreateContainer operation expects 'title' to be Literal, got {type(title)}"
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
                    f"ldh-CreateContainer operation expects 'slug' to be Literal, got {type(slug)}"
                )

        # Process optional description
        description = None
        if "description" in arguments:
            desc_data = Operation.process_json(
                self.settings, arguments["description"], self.context, variable_stack
            )
            description = Operation.json_to_rdflib(desc_data)
            if not isinstance(description, Literal):
                raise TypeError(
                    f"ldh-CreateContainer operation expects 'description' to be Literal, got {type(description)}"
                )

        return self.execute(parent_uri, title, slug, description)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        parent_uri = URIRef(arguments["parent"])
        title = Literal(arguments["title"], datatype=XSD.string)
        slug = (
            Literal(arguments.get("slug", ""), datatype=XSD.string)
            if "slug" in arguments
            else None
        )
        description = (
            Literal(arguments.get("description", ""), datatype=XSD.string)
            if "description" in arguments
            else None
        )

        result = self.execute(parent_uri, title, slug, description)

        # Extract URL from PUT result
        url_binding = result.bindings[0]["url"]
        return [
            types.TextContent(
                type="text", text=f"Container created successfully at: {url_binding}"
            )
        ]
