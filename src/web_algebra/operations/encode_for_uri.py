import logging
from urllib.parse import quote
from typing import Any
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from web_algebra.operation import Operation

class EncodeForURI(Operation):
    """
    URL-encodes a string to make it safe for use in URIs, following SPARQL's `ENCODE_FOR_URI` behavior.
    """

    @property
    def description(self) -> str:
        return "Encodes a string to be URI-safe, following SPARQL's `ENCODE_FOR_URI` behavior. It encodes characters that are not allowed in URIs, such as spaces, slashes, and colons."
    
    @property
    def inputSchema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "The string to encode for use in a URI."
                }
            },
            "required": ["input"]
        }
    
    def execute(self, arguments: dict[str, Any]) -> str:
        """        Executes the EncodeForURI operation.
        :param arguments: A dictionary containing the input string to encode.
            - `input`: The string to encode for use in a URI. This can be a nested operation producing a string.
        :return: A string with the encoded URI string."""
        input: Any = Operation.execute_json(self.settings, arguments["input"], self.context)
        logging.info("Resolving input for EncodeForURI: %s", input)

        if isinstance(input, dict):
            if "value" not in input:
                raise ValueError(f"EncodeForURI expected a 'value' key, found: {input}")
            input = input["value"]  # Extract the string

        # ✅ Ensure we now have a string
        if not isinstance(input, str):
            raise ValueError(f"EncodeForURI operation requires 'input' to be a string, found: {input}")

        # ✅ Encode using XPath encode-for-uri() behavior (encode slashes, colons, etc.)
        encoded_value = quote(input, safe="")  # 🔥 No safe characters

        logging.info("Encoded URI: %s", encoded_value)
        return encoded_value

    async def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        return [types.TextContent(type="text", text=self.execute(arguments))]
