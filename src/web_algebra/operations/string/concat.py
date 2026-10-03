from typing import Any, List
from rdflib import Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation


class Concat(Operation, MCPTool):
    """
    Concatenates string literals, per SPARQL 1.1 CONCAT().
    """

    @classmethod
    def description(cls) -> str:
        return "Concatenates multiple string values into a single string, per SPARQL's CONCAT() function: if all inputs carry the same language tag the result carries it too, otherwise the result is a simple (xsd:string) literal."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "inputs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of string values to concatenate.",
                }
            },
            "required": ["inputs"],
        }

    def execute(self, inputs: List[Literal]) -> Literal:
        """Pure function: concatenate literals with RDFLib terms"""
        if not isinstance(inputs, list):
            raise TypeError(f"Concat.execute expects inputs to be list, got {type(inputs)}")

        for input_literal in inputs:
            if not isinstance(input_literal, Literal):
                raise TypeError(f"Concat.execute expects all inputs to be Literal, got {type(input_literal)}")

        result_str = "".join(str(input_literal) for input_literal in inputs)

        # SPARQL 1.1 CONCAT() result kind (formal-semantics.md §4.2): all
        # inputs typed xsd:string → xsd:string; all inputs carrying the same
        # language tag → that tag; anything else → simple literal.
        datatypes = {input_literal.datatype for input_literal in inputs}
        languages = {input_literal.language for input_literal in inputs}
        if inputs and datatypes == {XSD.string}:
            return Literal(result_str, datatype=XSD.string)
        if inputs and len(languages) == 1 and None not in languages:
            return Literal(result_str, lang=next(iter(languages)))
        return Literal(result_str)

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Literal:
        """JSON execution: process arguments and call pure function"""
        inputs_data = arguments["inputs"]
        
        processed_inputs = []
        for input_item in inputs_data:
            # Process each input (may contain nested operations)
            processed_input = Operation.process_json(
                self.settings, input_item, self.context, variable_stack
            )
            # Convert to string literal
            input_literal = self.to_string_literal(processed_input)
            processed_inputs.append(input_literal)

        return self.execute(processed_inputs)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        inputs = [Literal(inp, datatype=XSD.string) for inp in arguments["inputs"]]
        
        result = self.execute(inputs)
        return [types.TextContent(type="text", text=str(result))]