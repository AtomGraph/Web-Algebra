from typing import Any
from mcp import types
from web_algebra.operation import Operation


class Variable(Operation):
    """
    Sets a variable in the current scope, similar to XSLT's <xsl:variable>.
    Variables follow lexical scoping rules like XSLT.
    """

    @classmethod
    def description(cls) -> str:
        return "Sets a variable in the current scope, similar to XSLT's <xsl:variable>"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The variable name to assign to.",
                },
                "value": {
                    "description": "The expression/operation to evaluate and assign to the variable."
                },
            },
            "required": ["name", "value"],
            "additionalProperties": False,
        }

    def execute(self, name: str, value: Any, variable_stack: list) -> None:
        """Pure function: store name/value in variable stack"""
        self.set_variable(name, value, variable_stack)
        return None

    def execute_json(self, arguments: dict, variable_stack: list = []) -> None:
        """JSON execution: evaluate value expression and store variable"""
        name: str = arguments["name"]
        value_expr = arguments["value"]

        # Evaluate the value expression in the current context
        value = Operation.process_json(
            self.settings, value_expr, self.context, variable_stack
        )

        # Call pure function to store the variable
        return self.execute(name, value, variable_stack)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → confirmation"""
        return [types.TextContent(type="text", text="Variable set successfully")]
