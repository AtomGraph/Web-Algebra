from typing import Any, List, Dict
from mcp import types
from web_algebra.operation import Operation
from rdflib.query import Result
from rdflib.term import Node


class Bindings(Operation):
    """
    Extracts the sequence of binding dictionaries from SPARQL Result.
    Converts Result table format to sequence for use with ForEach.
    """

    @classmethod
    def description(cls) -> str:
        return "Extracts the sequence of binding dictionaries from SPARQL Result"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "table": {"description": "SPARQL Result to extract bindings from"}
            },
            "required": ["table"],
        }

    def execute(self, table: Result) -> List[Dict[str, Node]]:
        """Pure function: extract bindings from Result"""
        if not isinstance(table, Result):
            raise TypeError(
                f"Bindings operation expects table to be Result, got {type(table)}"
            )

        return table.bindings

    def execute_json(
        self, arguments: dict, variable_stack: list = []
    ) -> List[Dict[str, Node]]:
        """JSON execution: process arguments with strict type checking"""
        # Process table
        table_data = Operation.process_json(
            self.settings, arguments["table"], self.context, variable_stack
        )
        if not isinstance(table_data, Result):
            raise TypeError(
                f"Bindings operation expects 'table' to be Result, got {type(table_data)}"
            )

        return self.execute(table_data)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        # For MCP, just return summary
        return [
            types.TextContent(
                type="text", text="Extracted bindings from SPARQL results"
            )
        ]
