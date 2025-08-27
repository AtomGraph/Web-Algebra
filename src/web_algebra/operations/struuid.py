import logging
import uuid
from typing import Any
from rdflib import Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.operation import Operation
from web_algebra.mcp_tool import MCPTool


class STRUUID(Operation, MCPTool):
    """
    Generates a fresh UUID (Universally Unique Identifier) as a string, following SPARQL's STRUUID() behavior.
    """

    @classmethod
    def description(cls) -> str:
        return "Generates a fresh UUID (Universally Unique Identifier) as a string, following the behavior of SPARQL's STRUUID(). Each invocation produces a new unique identifier."

    @classmethod
    def inputSchema(cls) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    def execute(self) -> Literal:
        """Pure function: generate UUID with RDFLib terms"""
        # Generate a new UUID4 (random UUID)
        generated_uuid = str(uuid.uuid4())

        logging.info("Generated UUID: %s", generated_uuid)
        return Literal(generated_uuid, datatype=XSD.string)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Literal:
        """JSON execution: process arguments and call pure function"""
        return self.execute()

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        result = self.execute()
        return [types.TextContent(type="text", text=str(result))]
