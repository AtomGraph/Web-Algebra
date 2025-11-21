from typing import Any, Optional
import logging
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
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
                    "description": "The URI of the document to append the SELECT query to.",
                },
                "query": {
                    "type": "string",
                    "description": "The SPARQL SELECT query string.",
                },
                "title": {
                    "type": "string",
                    "description": "Title of the SELECT query.",
                },
                "description": {
                    "type": "string",
                    "description": "Optional description of the SELECT query.",
                },
                "fragment": {
                    "type": "string",
                    "description": "Optional fragment identifier for the query URI (e.g., 'my-query' creates #my-query).",
                },
                "service": {
                    "type": "string",
                    "description": "Optional URI of the SPARQL service/endpoint specific to this query. Note: the service URI is _not_ the SPARQL endpoint URL but an instance of `sd:Service` that describes the SPARQL service capabilities (and contains the endpoint URL).",
                },
            },
            "required": ["url", "query", "title"],
        }

    def execute_json(self, arguments: dict[str, str], variable_stack: list = []) -> Any:
        """JSON execution: process arguments and delegate to execute()"""
        # Process required arguments
        url_data = Operation.process_json(
            self.settings, arguments["url"], self.context, variable_stack
        )
        if not isinstance(url_data, URIRef):
            raise TypeError(
                f"AddSelect operation expects 'url' to be URIRef, got {type(url_data)}"
            )

        query_data = Operation.process_json(
            self.settings, arguments["query"], self.context, variable_stack
        )
        query_literal = self.to_string_literal(query_data)

        title_data = Operation.process_json(
            self.settings, arguments["title"], self.context, variable_stack
        )
        title_literal = self.to_string_literal(title_data)

        # Process optional arguments
        description_literal = None
        if "description" in arguments:
            description_data = Operation.process_json(
                self.settings, arguments["description"], self.context, variable_stack
            )
            description_literal = self.to_string_literal(description_data)

        fragment_literal = None
        if "fragment" in arguments:
            fragment_data = Operation.process_json(
                self.settings, arguments["fragment"], self.context, variable_stack
            )
            fragment_literal = self.to_string_literal(fragment_data)

        service_uri = None
        if "service" in arguments:
            service_data = Operation.process_json(
                self.settings, arguments["service"], self.context, variable_stack
            )
            if not isinstance(service_data, URIRef):
                raise TypeError(
                    f"AddSelect operation expects 'service' to be URIRef, got {type(service_data)}"
                )
            service_uri = service_data

        return self.execute(
            url_data,
            query_literal,
            title_literal,
            description_literal,
            fragment_literal,
            service_uri,
        )

    def execute(
        self,
        url: URIRef,
        query: Literal,
        title: Literal,
        description: Optional[Literal] = None,
        fragment: Optional[Literal] = None,
        service: Optional[URIRef] = None,
    ) -> Any:
        """Pure function: create SPARQL SELECT query with RDFLib terms"""
        if not isinstance(url, URIRef):
            raise TypeError(
                f"AddSelect.execute expects url to be URIRef, got {type(url)}"
            )
        if not isinstance(query, Literal) or query.datatype != XSD.string:
            raise TypeError(
                f"AddSelect.execute expects query to be string Literal, got {type(query)}"
            )
        if not isinstance(title, Literal) or title.datatype != XSD.string:
            raise TypeError(
                f"AddSelect.execute expects title to be string Literal, got {type(title)}"
            )
        if description is not None and (
            not isinstance(description, Literal) or description.datatype != XSD.string
        ):
            raise TypeError(
                f"AddSelect.execute expects description to be string Literal, got {type(description)}"
            )
        if fragment is not None and (
            not isinstance(fragment, Literal) or fragment.datatype != XSD.string
        ):
            raise TypeError(
                f"AddSelect.execute expects fragment to be string Literal, got {type(fragment)}"
            )
        if service is not None and not isinstance(service, URIRef):
            raise TypeError(
                f"AddSelect.execute expects service to be URIRef, got {type(service)}"
            )

        url_str = str(url)
        query_str = str(query)
        title_str = str(title)
        description_str = str(description) if description else None
        fragment_str = str(fragment) if fragment else None
        service_str = str(service) if service else None

        logging.info(
            "Creating SELECT query for document <%s> with title '%s'",
            url_str,
            title_str,
        )

        # Create subject URI (fragment or blank node) - matching shell script logic
        if fragment_str:
            subject_id = f"#{fragment_str}"  # relative URI that will be resolved against the request URI
        else:
            subject_id = "_:subject"

        # Build JSON-LD structure for the SELECT query - matching shell script output
        data = {
            "@context": {
                "ldh": "https://w3id.org/atomgraph/linkeddatahub#",
                "dct": "http://purl.org/dc/terms/",
                "sp": "http://spinrdf.org/sp#",
            },
            "@id": subject_id,
            "@type": "sp:Select",
            "dct:title": title_str,
            "sp:text": query_str,
        }

        # Add optional properties - matching shell script conditional logic
        if service_str:
            data["ldh:service"] = {"@id": service_str}

        if description_str:
            data["dct:description"] = description_str

        logging.info(f"Posting SELECT query with JSON-LD data: {data}")

        # POST the JSON-LD content to the target URI
        # Convert JSON-LD dict to Graph
        import json
        from rdflib import Graph

        graph = Graph()
        graph.parse(data=json.dumps(data), format="json-ld", publicID=url_str)
        return super().execute(url, graph)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        from mcp import types

        # Convert plain arguments to RDFLib terms
        url = URIRef(arguments["url"])
        query = Literal(arguments["query"], datatype=XSD.string)
        title = Literal(arguments["title"], datatype=XSD.string)

        description = None
        if "description" in arguments:
            description = Literal(arguments["description"], datatype=XSD.string)

        fragment = None
        if "fragment" in arguments:
            fragment = Literal(arguments["fragment"], datatype=XSD.string)

        service = None
        if "service" in arguments:
            service = URIRef(arguments["service"])

        # Call pure function
        result = self.execute(url, query, title, description, fragment, service)

        # Return status for MCP response
        status_binding = result.bindings[0]["status"]
        return [types.TextContent(type="text", text=f"SELECT query added - status: {status_binding}")]
