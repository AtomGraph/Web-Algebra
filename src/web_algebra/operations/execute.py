from typing import Any
from mcp import types
from web_algebra.operation import Operation


class Execute(Operation):
    """
    Execute a (potentially nested) operation from its JSON representation.
    """

    @classmethod
    def description(cls) -> str:
        return "Executes a (potentially nested) operation from its JSON representation. The operation is expected to be an instance of the Operation class."

    @classmethod
    def inputSchema(cls) -> dict:
        """
        Returns the JSON schema of the operation's input arguments.
        """
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "object",
                    "description": "An instance of an Operation to execute.",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Type of the operation",
                        },
                    },
                    "required": ["type"],
                }
            },
            "required": ["operation"],
        }

    def execute(self, operation: Any) -> Any:
        """Pure function: execute operation with RDFLib terms"""
        if not isinstance(operation, dict) or "@op" not in operation:
            raise TypeError(
                f"Execute.execute expects operation dict with '@op' key, got {type(operation)}"
            )

        # Delegate to Operation.process_json for nested operation execution
        return Operation.process_json(self.settings, operation, self.context)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Any:
        """JSON execution: pass raw operation to execute"""
        # Don't process the operation argument - execute() expects raw operation dict
        return self.execute(arguments["operation"])

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        result = self.execute(arguments["operation"])
        return [types.TextContent(type="text", text=str(result))]
