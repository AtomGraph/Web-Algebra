from typing import Any
from rdflib.term import Node
from rdflib import Literal, URIRef
from mcp import types
from web_algebra.operation import Operation


class Str(Operation):
    """
    Returns the lexical form of a Literal or the codepoint representation of
    a URI as a simple literal, per SPARQL 1.1 STR().
    """

    @classmethod
    def description(cls) -> str:
        return "Returns the lexical form of a Literal or the string representation of a URI, per SPARQL's STR() function. The language tag, if any, is not carried over."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {"description": "The input value to convert to string"},
            },
            "required": ["input"],
        }

    def execute(self, term: Node) -> Literal:
        """Pure function: RDFLib term → string literal"""
        # SPARQL 1.1 STR() accepts a literal or an IRI; a blank node is a
        # type error (formal-semantics.md §4.2).
        if not isinstance(term, (URIRef, Literal)):
            raise TypeError(
                f"Str expects a URI or Literal (SPARQL STR), got {type(term).__name__}"
            )

        # The lexical form / codepoint representation as a simple literal
        # (no datatype, no language tag) — as rdflib's SPARQL engine does.
        return Literal(str(term))

    def execute_json(
        self, arguments: dict, variable_stack: list = None
    ) -> Literal:
        """JSON execution: processes JSON args, returns RDFLib string literal"""
        # Process the input argument through the JSON system
        input_data = Operation.process_json(
            self.settings, arguments["input"], self.context, variable_stack
        )

        # Expect RDFLib term directly
        if not isinstance(input_data, Node):
            raise TypeError(
                f"Str operation expects input to be RDFLib term, got {type(input_data)}"
            )

        # Call pure function
        return self.execute(input_data)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        # Convert plain input to RDFLib term
        rdflib_term = Operation.plain_to_rdflib(arguments["input"])

        # Call pure function
        result = self.execute(rdflib_term)

        # Convert result to plain string for MCP
        return [types.TextContent(type="text", text=str(result))]
