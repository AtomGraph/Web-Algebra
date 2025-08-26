from typing import Any
import rdflib
from rdflib import Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.operation import Operation


class Str(Operation):
    """
    Converts any RDF term to a string literal
    """

    @classmethod
    def description(cls) -> str:
        return "Converts any RDF term to a string literal"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {"description": "The input value to convert to string"},
            },
            "required": ["input"],
        }

    def execute(self, term: rdflib.term.Node) -> rdflib.Literal:
        """Pure function: RDFLib term → string literal"""
        # Check if already string-compatible
        if isinstance(term, Literal):
            if term.datatype == XSD.string:
                return term  # Already xsd:string, return as-is
            elif hasattr(term, 'lang') and term.lang is not None:
                return term  # rdf:langString (datatype=None, lang=xx), return as-is (compatible)
            elif term.datatype is None and (not hasattr(term, 'lang') or term.lang is None):
                # Plain literal without datatype or language - treat as string
                return term

        # Convert any other term to xsd:string
        return Literal(str(term), datatype=XSD.string)

    def execute_json(
        self, arguments: dict, variable_stack: list = []
    ) -> rdflib.Literal:
        """JSON execution: processes JSON args, returns RDFLib string literal"""
        # Process the input argument through the JSON system
        input_data = Operation.process_json(
            self.settings, arguments["input"], self.context, variable_stack
        )

        # Expect RDFLib term directly
        if not isinstance(input_data, rdflib.term.Node):
            raise TypeError(
                f"Str operation expects input to be RDFLib term, got {type(input_data)}"
            )

        # Call pure function
        return self.execute(input_data)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        # Convert plain input to RDFLib term
        rdflib_term = self.plain_to_rdflib(arguments["input"])

        # Call pure function
        result = self.execute(rdflib_term)

        # Convert result to plain string for MCP
        return [types.TextContent(type="text", text=str(result))]
