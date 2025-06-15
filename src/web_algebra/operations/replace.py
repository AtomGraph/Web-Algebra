from typing import Any
import logging
import re
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from web_algebra.operation import Operation

class Replace(Operation):
    """
    Replaces occurrences of a specified pattern in an input string with a given replacement.
    Aligns with SPARQL's REPLACE() function.
    """

    @classmethod
    def description(cls) -> str:
        return "Replaces occurrences of a specified pattern in an input string with a given replacement. This operation aligns with SPARQL's REPLACE() function, allowing for flexible string manipulation using regular expressions."

    @classmethod
    def inputSchema(cls) -> dict:
        """
        Returns the JSON schema of the operation's input arguments.
        """
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "The input string to process"},
                "pattern": {"type": "string", "description": "The pattern to be replaced (regular expression)"},
                "replacement": {"type": "string", "description": "The replacement value"}
            },
            "required": ["input", "pattern", "replacement"],
        }
    
    def execute(self, arguments: dict[str, Any]) -> str:
        """
        Performs string replacement using a regular expression.
        :param arguments: A dictionary containing:
            - `input`: The input string to process (can be a nested operation producing a string).
            - `pattern`: The pattern to be replaced (can be a nested operation producing a string).
            - `replacement`: The replacement value (can be a nested operation producing a string).
        :return: The formatted string.
        """
        input: str = Operation.execute_json(self.settings, arguments["input"], self.context)  # The input string to process
        pattern: str = Operation.execute_json(self.settings, arguments["pattern"], self.context) # The pattern to be replaced (or a nested operation producing it)
        replacement: str = Operation.execute_json(self.settings, arguments["replacement"], self.context) # The replacement value (or a nested operation producing it)

        logging.info("Resolving Replace arguments: input=%s, pattern=%s, replacement=%s", input, pattern, replacement)

        if not isinstance(input, str):
            raise ValueError("Replace 'input' must resolve to a string.")
        if not isinstance(pattern, str):
            raise ValueError("Replace 'pattern' must resolve to a string.")
        
        formatted_string = re.sub(pattern, str(replacement), input)

        logging.info("Formatted result: %s", formatted_string) 
        return formatted_string

    def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        return [types.TextContent(type="text", text=self.execute(arguments))]
