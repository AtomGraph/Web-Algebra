from typing import Any, Optional
import logging
import urllib.parse
import uuid
from rdflib import URIRef, Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.operation import Operation
from web_algebra.rfc3986 import resolve
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
                    "description": "URL path segment (optional). Defaults to a random UUID. A document that already exists at this path is replaced.",
                },
                "description": {
                    "type": "string",
                    "description": "Description (optional)",
                },
                "block": {
                    "type": "string",
                    "description": "URI of the container's first content block (optional). Without it, the block lists the container's children.",
                },
                "mode": {
                    "type": "string",
                    "description": "URI of the layout mode (e.g. ac:GridMode) the children are listed in (optional; ignored when block is given).",
                },
                "primary_topic": {
                    "type": "string",
                    "description": "URI reference of what the container is about, resolved against its URI (optional), e.g. #this.",
                },
            },
            "required": ["parent", "title"],
        }

    def execute(
        self,
        parent_uri: URIRef,
        title: Literal,
        slug: Optional[Literal] = None,
        description: Optional[Literal] = None,
        block: Optional[URIRef] = None,
        mode: Optional[URIRef] = None,
        primary_topic: Optional[Literal] = None,
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
        for name, term, typ in (("block", block, URIRef), ("mode", mode, URIRef), ("primary_topic", primary_topic, Literal)):
            if term is not None and not isinstance(term, typ):
                raise TypeError(
                    f"CreateContainer.execute expects {name} to be {typ.__name__} or None, got {type(term)}"
                )

        # URL-encode slug, or mint a fresh one - a lowercase UUID, as the LinkedDataHub CLI does - so that
        # leaving it out never lands on an existing document; deriving it from the title did, on a repeated title
        slug_str = urllib.parse.quote(str(slug) if slug else str(uuid.uuid4()), safe="")

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
                "dh": "https://w3id.org/atomgraph/linkeddatahub/document-hierarchy#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "dct": "http://purl.org/dc/terms/",
                "sioc": "http://rdfs.org/sioc/ns#",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "spin": "http://spinrdf.org/spin#",
                "ac": "https://w3id.org/atomgraph/client#",
                "foaf": "http://xmlns.com/foaf/0.1/",
            },
            "@id": url,
            "@type": "dh:Container",
            "dct:title": Operation.jsonld_text(title),
        }
        # the first content block, as the LinkedDataHub CLI writes it: the given
        # block; else a view of the children in the given mode; else the
        # children view (formal-semantics.md Appendix A)
        if block is not None:
            data["rdf:_1"] = {"@id": str(block)}
        elif mode is not None:
            data["rdf:_1"] = {
                "@type": "ldh:Object",
                "rdf:value": {"@type": "ldh:View", "spin:query": {"@id": "ldh:SelectChildren"}, "ac:mode": {"@id": str(mode)}},
            }
        else:
            data["rdf:_1"] = {"@type": "ldh:Object", "rdf:value": {"@id": "ldh:ChildrenView"}}

        if description:
            data["dct:description"] = Operation.jsonld_text(description)
        if primary_topic is not None:
            # a URI reference resolved against the document (RFC 3986)
            data["foaf:primaryTopic"] = {"@id": resolve(url, str(primary_topic))}

        # Convert the document to a Graph and call parent PUT operation
        graph = self.to_graph(data, base=url)

        # Call parent PUT execute method
        return super().execute(URIRef(url), graph)

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Result:
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


        # Process optional block
        block = None
        if "block" in arguments:
            block_data = Operation.process_json(
                self.settings, arguments["block"], self.context, variable_stack
            )
            block = Operation.json_to_rdflib(block_data)
            if not isinstance(block, URIRef):
                raise TypeError(
                    f"ldh-CreateContainer operation expects 'block' to be URIRef, got {type(block)}"
                )

        # Process optional mode
        mode = None
        if "mode" in arguments:
            mode_data = Operation.process_json(
                self.settings, arguments["mode"], self.context, variable_stack
            )
            mode = Operation.json_to_rdflib(mode_data)
            if not isinstance(mode, URIRef):
                raise TypeError(
                    f"ldh-CreateContainer operation expects 'mode' to be URIRef, got {type(mode)}"
                )

        # Process optional primary_topic
        primary_topic = None
        if "primary_topic" in arguments:
            primary_topic_data = Operation.process_json(
                self.settings, arguments["primary_topic"], self.context, variable_stack
            )
            primary_topic = Operation.json_to_rdflib(primary_topic_data)
            if not isinstance(primary_topic, Literal):
                raise TypeError(
                    f"ldh-CreateContainer operation expects 'primary_topic' to be Literal, got {type(primary_topic)}"
                )

        return self.execute(parent_uri, title, slug, description, block, mode, primary_topic)

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

        block = URIRef(arguments["block"]) if "block" in arguments else None
        mode = URIRef(arguments["mode"]) if "mode" in arguments else None
        primary_topic = (
            Literal(arguments["primary_topic"], datatype=XSD.string)
            if "primary_topic" in arguments
            else None
        )
        result = self.execute(parent_uri, title, slug, description, block, mode, primary_topic)

        # Extract URL from PUT result
        url_binding = result.bindings[0]["url"]
        return [
            types.TextContent(
                type="text", text=f"Container created successfully at: {url_binding}"
            )
        ]
