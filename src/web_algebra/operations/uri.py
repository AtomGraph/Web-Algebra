from typing import Any
import rdflib
from rdflib import URIRef
from mcp import types
from web_algebra.operation import Operation


class Uri(Operation):
    """
    Converts any RDF term to a URI reference (like SPARQL's URI() function)
    """

    @classmethod
    def description(cls) -> str:
        return "Converts any RDF term to a URI reference (like SPARQL's URI() function)"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {"description": "The input value to convert to URI"},
            },
            "required": ["input"],
        }

    def execute(self, term: rdflib.term.Node) -> rdflib.URIRef:
        """Pure function: RDFLib term → URI reference"""
        if not isinstance(term, rdflib.term.Node):
            raise TypeError(
                f"Uri operation expects input to be RDFLib term, got {type(term)}"
            )

        return URIRef(str(term))

    def execute_json(self, arguments: dict, variable_stack: list = []) -> rdflib.URIRef:
        """JSON execution: processes JSON args, returns RDFLib URI reference"""
        # Process the input argument through the JSON system
        input_data = Operation.process_json(
            self.settings, arguments["input"], self.context, variable_stack
        )

        # Expect RDFLib term directly
        if not isinstance(input_data, rdflib.term.Node):
            raise TypeError(
                f"Uri operation expects input to be RDFLib term, got {type(input_data)}"
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
