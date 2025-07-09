import logging
import uuid
from typing import Any
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from web_algebra.operation import Operation

class STRUUID(Operation):
    """
    Generates a fresh UUID (Universally Unique Identifier) as a string, following SPARQL's STRUUID() behavior.
    """

    @classmethod
    def description(cls) -> str:
        return "Generates a fresh UUID (Universally Unique Identifier) as a string, following the behavior of SPARQL's STRUUID(). Each invocation produces a new unique identifier."
    
    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def execute(self, arguments: dict[str, Any]) -> str:
        """
        Executes the STRUUID operation.
        :param arguments: An empty dictionary (no arguments required).
        :return: A string containing a freshly generated UUID in standard format.
        """
        # Generate a new UUID4 (random UUID)
        generated_uuid = str(uuid.uuid4())
        
        logging.info("Generated UUID: %s", generated_uuid)
        return generated_uuid

    def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        return [types.TextContent(type="text", text=self.execute(arguments))]
