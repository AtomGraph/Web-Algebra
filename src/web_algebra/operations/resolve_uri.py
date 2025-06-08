from typing import Any
from urllib.parse import urljoin
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from web_algebra.operation import Operation

class ResolveURI(Operation):
    """
    Resolves a relative URI against a base URI.
    """

    @classmethod
    def description(cls) -> str:
        return """
        Creates a new URI relative to the base URL. The relative URI **must** be pre-encoded.
        """
    
    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "base": {
                    "type": "string",
                    "description": "The base URI to resolve against."
                },
                "relative": {
                    "type": "string",
                    "description": "The relative URI to resolve."
                }
            },
            "required": ["base", "relative"]
        }
    
    def execute(self, arguments: dict[str, Any]) -> str:
        """
        Resolves a relative URI against a base URI.
        :param arguments: A dictionary containing:
            - `base`: The base URI to resolve against.
            - `relative`: The relative URI to resolve.
        :return: The resolved absolute URI as a string.
        """
        base: str = Operation.execute_json(self.settings, arguments["base"], self.context)
        value: str = Operation.execute_json(self.settings, arguments["relative"], self.context)

        if not isinstance(base, str):
            raise ValueError("Replace 'base' must resolve to a string.")
        if not isinstance(value, str):
            raise ValueError("Replace 'value' must resolve to a string.")

        return str(urljoin(self.base, value))

    async def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        return [types.TextContent(type="text", text=self.execute(arguments))]
