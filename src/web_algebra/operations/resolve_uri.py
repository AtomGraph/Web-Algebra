from typing import Any
from urllib.parse import urljoin
from rdflib import URIRef, Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation


class ResolveURI(Operation, MCPTool):
    """
    Resolves a relative URI against a base URI.
    """

    @classmethod
    def description(cls) -> str:
        return """
        Creates a new URI relative to the base URL. The relative URI **must** be pre-encoded.
        """

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "base": {
                    "type": "string",
                    "description": "The base URI to resolve against.",
                },
                "relative": {
                    "type": "string",
                    "description": "The relative URI to resolve.",
                },
            },
            "required": ["base", "relative"],
        }

    def execute(self, base: URIRef, relative: Literal) -> URIRef:
        """Pure function: resolve relative URI against base with RDFLib terms"""
        if not isinstance(base, URIRef):
            raise TypeError(
                f"ResolveURI.execute expects base to be URIRef, got {type(base)}"
            )
        if not isinstance(relative, Literal):
            raise TypeError(
                f"ResolveURI.execute expects relative to be Literal, got {type(relative)}"
            )

        base_str = str(base)
        relative_str = str(relative)
        resolved_uri = urljoin(base_str, relative_str)
        return URIRef(resolved_uri)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> URIRef:
        """JSON execution: process arguments and call pure function"""
        # Process base URI
        base_data = Operation.process_json(
            self.settings, arguments["base"], self.context, variable_stack
        )
        base = Operation.json_to_rdflib(base_data)
        if not isinstance(base, URIRef):
            raise TypeError(
                f"ResolveURI operation expects 'base' to be URIRef, got {type(base)}"
            )

        # Process relative URI
        relative_data = Operation.process_json(
            self.settings, arguments["relative"], self.context, variable_stack
        )
        relative = Operation.json_to_rdflib(relative_data)
        if not isinstance(relative, Literal):
            raise TypeError(
                f"ResolveURI operation expects 'relative' to be Literal, got {type(relative)}"
            )

        return self.execute(base, relative)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        base = URIRef(arguments["base"])
        relative = Literal(arguments["relative"], datatype=XSD.string)

        result = self.execute(base, relative)
        return [types.TextContent(type="text", text=str(result))]
