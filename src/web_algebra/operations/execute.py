from typing import Any
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
                        "type": {"type": "string", "description": "Type of the operation"},
                    },
                    "required": ["type"]
                }
            },
            "required": ["operation"]
        }

    def execute(self, arguments: dict[str, Any]) -> Any:
        op = arguments["operation"]

        if isinstance(op, Operation):
            return op.execute_json(self.settings, op, self.context)
        else:
            raise ValueError("The 'operation' argument must be an instance of Operation.")