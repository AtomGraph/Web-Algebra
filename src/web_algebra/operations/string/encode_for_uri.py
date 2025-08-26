import logging
from urllib.parse import quote
from typing import Any
from rdflib import Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.operation import Operation


class EncodeForURI(Operation):
    """
    URL-encodes a string to make it safe for use in URIs, following SPARQL's `ENCODE_FOR_URI` behavior.
    """

    @classmethod
    def description(cls) -> str:
        return "Encodes a string to be URI-safe, following SPARQL's `ENCODE_FOR_URI` behavior. It encodes characters that are not allowed in URIs, such as spaces, slashes, and colons."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "The string to encode for use in a URI.",
                }
            },
            "required": ["input"],
        }

    def execute(self, input_str: Literal) -> Literal:
        """Pure function: encode string for URI with RDFLib terms"""
        if not isinstance(input_str, Literal):
            raise TypeError(
                f"EncodeForURI.execute expects input_str to be Literal, got {type(input_str)}"
            )

        input_value = str(input_str)
        logging.info("Encoding input for URI: %s", input_value)

        # Encode using XPath encode-for-uri() behavior (encode slashes, colons, etc.)
        encoded_value = quote(input_value, safe="")  # No safe characters

        logging.info("Encoded URI: %s", encoded_value)
        return Literal(encoded_value, datatype=XSD.string)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Literal:
        """JSON execution: process arguments and call pure function"""
        input_data = Operation.process_json(
            self.settings, arguments["input"], self.context, variable_stack
        )
        # Allow implicit string conversion
        input_literal = Operation.to_string_literal(input_data)

        return self.execute(input_literal)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        input_str = Literal(arguments["input"], datatype=XSD.string)

        result = self.execute(input_str)
        return [types.TextContent(type="text", text=str(result))]
