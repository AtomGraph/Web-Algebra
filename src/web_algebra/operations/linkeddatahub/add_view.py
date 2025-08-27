from typing import Any
import logging
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
from web_algebra.mcp_tool import MCPTool
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
                    "description": "The URI of the document to append the view to.",
                },
                "query": {
                    "type": "string",
                    "description": "URI of an existing sp:Select query resource to visualize (not a SPARQL query string).",
                },
                "title": {"type": "string", "description": "Title of the view."},
                "description": {
                    "type": "string",
                    "description": "Optional description of the view.",
                },
                "fragment": {
                    "type": "string",
                    "description": "Optional fragment identifier for the view URI (e.g., 'my-view' creates #my-view).",
                },
                "mode": {
                    "type": "string",
                    "description": "Optional URI of the display mode for the view.",
                    "enum": [
                        "https://w3id.org/atomgraph/client#ReadMode",
                        "https://w3id.org/atomgraph/client#ListMode",
                        "https://w3id.org/atomgraph/client#GridMode",
                        "https://w3id.org/atomgraph/client#GraphMode",
                        "https://w3id.org/atomgraph/client#MapMode",
                    ],
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
            raise TypeError(f"AddView operation expects 'url' to be URIRef, got {type(url_data)}")

        query_data = Operation.process_json(
            self.settings, arguments["query"], self.context, variable_stack
        )
        if not isinstance(query_data, URIRef):
            raise TypeError(f"AddView operation expects 'query' to be URIRef, got {type(query_data)}")

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

        mode_uri = None
        if "mode" in arguments:
            mode_data = Operation.process_json(
                self.settings, arguments["mode"], self.context, variable_stack
            )
            if not isinstance(mode_data, URIRef):
                raise TypeError(f"AddView operation expects 'mode' to be URIRef, got {type(mode_data)}")
            mode_uri = mode_data
            
        return self.execute(
            url_data, query_data, title_literal, description_literal,
            fragment_literal, mode_uri
        )

    def execute(
        self,
        url: URIRef,
        query: URIRef,
        title: Literal,
        description: Literal = None,
        fragment: Literal = None,
        mode: URIRef = None,
    ) -> Any:
        """Pure function: create SPARQL result set view with RDFLib terms"""
        if not isinstance(url, URIRef):
            raise TypeError(f"AddView.execute expects url to be URIRef, got {type(url)}")
        if not isinstance(query, URIRef):
            raise TypeError(f"AddView.execute expects query to be URIRef, got {type(query)}")
        if not isinstance(title, Literal) or title.datatype != XSD.string:
            raise TypeError(f"AddView.execute expects title to be string Literal, got {type(title)}")
        if description is not None and (not isinstance(description, Literal) or description.datatype != XSD.string):
            raise TypeError(f"AddView.execute expects description to be string Literal, got {type(description)}")
        if fragment is not None and (not isinstance(fragment, Literal) or fragment.datatype != XSD.string):
            raise TypeError(f"AddView.execute expects fragment to be string Literal, got {type(fragment)}")
        if mode is not None and not isinstance(mode, URIRef):
            raise TypeError(f"AddView.execute expects mode to be URIRef, got {type(mode)}")

        url_str = str(url)
        query_str = str(query)
        title_str = str(title)
        description_str = str(description) if description else None
        fragment_str = str(fragment) if fragment else None
        mode_str = str(mode) if mode else None

        logging.info(
            "Creating View for document <%s> with sp:Select resource <%s>", url_str, query_str
        )

        # Create subject URI (fragment or blank node) - matching shell script logic
        if fragment_str:
            subject_id = f"#{fragment_str}"  # relative URI that will be resolved against the request URI
        else:
            subject_id = "_:subject"

        # Build JSON-LD structure for the view - matching shell script output
        data = {
            "@context": {
                "ldh": "https://w3id.org/atomgraph/linkeddatahub#",
                "dct": "http://purl.org/dc/terms/",
                "spin": "http://spinrdf.org/spin#",
            },
            "@id": subject_id,
            "@type": "ldh:View",
            "dct:title": title_str,
            "spin:query": {"@id": query_str},
        }

        # Add optional properties - matching shell script conditional logic
        if description_str:
            data["dct:description"] = description_str

        if mode_str:
            # Add the ac: namespace to context when mode is used
            data["@context"]["ac"] = "https://w3id.org/atomgraph/client#"
            data["ac:mode"] = {"@id": mode_str}

        logging.info(f"Posting View with JSON-LD data: {data}")

        # POST the JSON-LD content to the target URI
        # Convert JSON-LD dict to Graph
        import json
        from rdflib import Graph
        graph = Graph()
        graph.parse(data=json.dumps(data), format="json-ld")
        return super().execute(url, graph)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        from mcp import types
        
        # Convert plain arguments to RDFLib terms
        url = URIRef(arguments["url"])
        query = URIRef(arguments["query"])
        title = Literal(arguments["title"], datatype=XSD.string)
        
        description = None
        if "description" in arguments:
            description = Literal(arguments["description"], datatype=XSD.string)
            
        fragment = None
        if "fragment" in arguments:
            fragment = Literal(arguments["fragment"], datatype=XSD.string)
            
        mode = None
        if "mode" in arguments:
            mode = URIRef(arguments["mode"])

        # Call pure function
        result = self.execute(url, query, title, description, fragment, mode)

        # Return status for MCP response
        return [types.TextContent(type="text", text=f"View added successfully")]
