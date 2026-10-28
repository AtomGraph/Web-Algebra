from typing import Any, ClassVar, Optional
import logging
import urllib.parse
import uuid
from rdflib import URIRef, Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.operation import Operation
from web_algebra.rfc3986 import resolve
from web_algebra.operation import OperationKind
from web_algebra.operations.linked_data.put import PUT
from web_algebra.operations.linkeddatahub.create import create, if_absent_flag
from rdflib.query import Result


class CreateContainer(PUT):
    # creates only, with If-None-Match: *: a document already at the URI is left as it is, so
    # nothing is ever removed
    kind: ClassVar[OperationKind] = OperationKind.WRITE

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
        - LinkedDataHub automatically manages parent-child relationships (sioc:has_parent) based on URI hierarchy
        - It only creates: a document already at the URI is left as it is and the operation fails, unless
          if_absent is true, which accepts it as the result (like mkdir -p). To replace a document, PUT it."""

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
                    "description": "URL path segment (optional). Defaults to a random UUID.",
                },
                "description": {
                    "type": "string",
                    "description": "Description (optional)",
                },
                "children_view": {
                    "type": "boolean",
                    "description": "Optional: whether the container's first content block lists its children (the shared ldh:ChildrenView). It does unless this is false; the content is then added with ldh-AddObjectBlock and ldh-AddXHTMLBlock, as to any document.",
                },
                "primary_topic": {
                    "type": "string",
                    "description": "URI reference of what the container is about, resolved against its URI (optional), e.g. #this.",
                },
                "if_absent": {
                    "type": "boolean",
                    "description": "Optional: whether a document already at the URI counts as success, left as it is (like mkdir -p). Without it the operation fails there.",
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
        children_view: Optional[Literal] = None,
        primary_topic: Optional[Literal] = None,
        if_absent: Optional[Literal] = None,
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
        if children_view is not None and not (
            isinstance(children_view, Literal) and children_view.datatype == XSD.boolean
        ):
            raise TypeError(
                f"CreateContainer.execute expects children_view to be an xsd:boolean Literal, got {children_view!r}"
            )
        if primary_topic is not None and not isinstance(primary_topic, Literal):
            raise TypeError(
                f"CreateContainer.execute expects primary_topic to be Literal or None, got {type(primary_topic)}"
            )

        if_absent = if_absent_flag(if_absent, "CreateContainer.execute")

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
                "foaf": "http://xmlns.com/foaf/0.1/",
            },
            "@id": url,
            "@type": "dh:Container",
            "dct:title": Operation.jsonld_text(title),
        }
        # the first content block, as the LinkedDataHub CLI writes it: the children
        # view, unless children_view is false (formal-semantics.md Appendix A)
        if children_view is None or children_view.toPython():
            data["rdf:_1"] = {"@type": "ldh:Object", "rdf:value": {"@id": "ldh:ChildrenView"}}

        if description:
            data["dct:description"] = Operation.jsonld_text(description)
        if primary_topic is not None:
            # a URI reference resolved against the document (RFC 3986)
            data["foaf:primaryTopic"] = {"@id": resolve(url, str(primary_topic))}

        # Convert the document to a Graph and call parent PUT operation
        graph = self.to_graph(data, base=url)

        return create(self, URIRef(url), graph, if_absent)

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


        # Process optional children_view
        children_view = None
        if "children_view" in arguments:
            children_view = Operation.json_to_rdflib(Operation.process_json(
                self.settings, arguments["children_view"], self.context, variable_stack
            ))

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

        # Process optional if_absent
        if_absent = None
        if "if_absent" in arguments:
            if_absent = Operation.json_to_rdflib(Operation.process_json(
                self.settings, arguments["if_absent"], self.context, variable_stack
            ))

        return self.execute(parent_uri, title, slug, description, children_view, primary_topic, if_absent)

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

        children_view = (
            Literal(bool(arguments["children_view"])) if "children_view" in arguments else None
        )
        primary_topic = (
            Literal(arguments["primary_topic"], datatype=XSD.string)
            if "primary_topic" in arguments
            else None
        )
        if_absent = Literal(bool(arguments["if_absent"])) if "if_absent" in arguments else None
        result = self.execute(parent_uri, title, slug, description, children_view, primary_topic, if_absent)

        # Extract URL from PUT result; a 412 is the existing document if_absent accepted
        url_binding = result.bindings[0]["url"]
        created = int(result.bindings[0]["status"]) != 412
        return [
            types.TextContent(
                type="text",
                text=f"Container created successfully at: {url_binding}" if created
                else f"A document already exists at {url_binding}; left as it is",
            )
        ]
