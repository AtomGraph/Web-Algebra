import logging
from datetime import datetime, timezone
from typing import Any
from rdflib import Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.operation import Operation
from web_algebra.mcp_tool import MCPTool


class NOW(Operation, MCPTool):
    """
    Returns the current datetime as an xsd:dateTime literal, following SPARQL's NOW() behavior.
    """

    @classmethod
    def description(cls) -> str:
        return "Returns the current datetime as an xsd:dateTime literal, following the behavior of SPARQL's NOW(). The value is timezone-aware (UTC) and represented in ISO 8601 format."

    @classmethod
    def inputSchema(cls) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    def execute(self) -> Literal:
        """Pure function: produce current datetime as xsd:dateTime literal"""
        now = datetime.now(timezone.utc).isoformat()

        logging.info("Generated NOW: %s", now)
        return Literal(now, datatype=XSD.dateTime)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Literal:
        """JSON execution: process arguments and call pure function"""
        return self.execute()

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        result = self.execute()
        return [types.TextContent(type="text", text=str(result))]
