import logging
from typing import Any
from rdflib import Literal
from mcp import types
from web_algebra.operation import Operation
from web_algebra.mcp_tool import MCPTool


class NOW(Operation, MCPTool):
    """
    The current date and time, per SPARQL's NOW() and XPath's
    fn:current-dateTime(): fixed for an evaluation (formal-semantics.md §4.2).
    """

    @classmethod
    def description(cls) -> str:
        return "Returns the current date and time as an xsd:dateTime literal in UTC, following SPARQL's NOW(): every NOW in one run of a program returns the same value, the time the run began."

    @classmethod
    def inputSchema(cls) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    def execute(self) -> Literal:
        """Pure function: τ of the evaluation in progress as xsd:dateTime"""
        now = self.current_datetime()
        logging.info("NOW: %s", now.isoformat())
        return Literal(now)

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Literal:
        """JSON execution: no arguments"""
        return self.execute()

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: each tool call is its own evaluation"""
        result = self.execute()
        return [types.TextContent(type="text", text=str(result))]
