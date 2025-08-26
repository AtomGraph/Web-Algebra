from typing import Any
import logging
import re
import rdflib
from rdflib import Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.operation import Operation


class Replace(Operation):
    """
    Replaces occurrences of a specified pattern in an input string with a given replacement.
    Aligns with SPARQL's REPLACE() function.
    """

    @classmethod
    def description(cls) -> str:
        return """Replaces occurrences of a specified pattern in an input string with a given replacement. This operation aligns with SPARQL's REPLACE() function, allowing for flexible string manipulation using regular expressions.
        
        Note: this function should not be used to build URIs! That should be done using EncodeForURI()/ResolveURI().
        """

    @classmethod
    def inputSchema(cls) -> dict:
        """
        Returns the JSON schema of the operation's input arguments.
        """
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "The input string to process",
                },
                "pattern": {
                    "type": "string",
                    "description": "The pattern to be replaced (regular expression)",
                },
                "replacement": {
                    "type": "string",
                    "description": "The replacement value",
                },
            },
            "required": ["input", "pattern", "replacement"],
        }

    def execute(
        self,
        input_str: rdflib.Literal,
        pattern: rdflib.Literal,
        replacement: rdflib.Literal,
    ) -> rdflib.Literal:
        """Pure function: replace pattern in string with RDFLib terms"""
        # Following SPARQL semantics: accept both xsd:string and rdf:langString (language-tagged literals)
        def is_string_compatible(lit):
            return isinstance(lit, Literal) and (
                lit.datatype == XSD.string or  # xsd:string
                (lit.datatype is None and hasattr(lit, 'lang') and lit.lang is not None) or  # rdf:langString
                (lit.datatype is None and (not hasattr(lit, 'lang') or lit.lang is None))  # plain literal
            )
        
        if not is_string_compatible(input_str):
            raise TypeError(
                f"Replace operation expects input to be string-compatible Literal, got {type(input_str)} with datatype {getattr(input_str, 'datatype', None)}"
            )
        if not is_string_compatible(pattern):
            raise TypeError(
                f"Replace operation expects pattern to be string-compatible Literal, got {type(pattern)} with datatype {getattr(pattern, 'datatype', None)}"
            )
        if not is_string_compatible(replacement):
            raise TypeError(
                f"Replace operation expects replacement to be string-compatible Literal, got {type(replacement)} with datatype {getattr(replacement, 'datatype', None)}"
            )

        input_value = str(input_str)
        pattern_value = str(pattern)
        replacement_value = str(replacement)

        logging.info(
            "Resolving Replace arguments: input=%s, pattern=%s, replacement=%s",
            input_value,
            pattern_value,
            replacement_value,
        )

        formatted_string = re.sub(pattern_value, replacement_value, input_value)

        logging.info("Formatted result: %s", formatted_string)
        return Literal(formatted_string, datatype=XSD.string)

    def execute_json(
        self, arguments: dict, variable_stack: list = []
    ) -> rdflib.Literal:
        """JSON execution: process arguments with strict type checking"""
        # Process input - allow implicit string conversion
        input_data = Operation.process_json(
            self.settings, arguments["input"], self.context, variable_stack
        )
        input_literal = Operation.to_string_literal(input_data)

        # Process pattern - allow implicit string conversion
        pattern_data = Operation.process_json(
            self.settings, arguments["pattern"], self.context, variable_stack
        )
        pattern_literal = Operation.to_string_literal(pattern_data)

        # Process replacement - allow implicit string conversion
        replacement_data = Operation.process_json(
            self.settings, arguments["replacement"], self.context, variable_stack
        )
        replacement_literal = Operation.to_string_literal(replacement_data)

        return self.execute(input_literal, pattern_literal, replacement_literal)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        input_str = Literal(arguments["input"], datatype=XSD.string)
        pattern = Literal(arguments["pattern"], datatype=XSD.string)
        replacement = Literal(arguments["replacement"], datatype=XSD.string)

        result = self.execute(input_str, pattern, replacement)

        return [types.TextContent(type="text", text=str(result))]
