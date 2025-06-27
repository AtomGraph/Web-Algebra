from typing import Any
import logging
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types

from web_algebra.operation import Operation

class ForEach(Operation):
    """
    Executes a WebAlgebra operation (or a sequence of operations) for each row in a table.
    """

    @classmethod
    def description(cls) -> str:
        return "Executes a WebAlgebra operation for each row in a SPARQL results bindings table. The operation can be a single operation or a list of operations. Each row is processed independently, and the results are collected in a list."
    
    @classmethod
    def inputSchema(cls) -> dict:
        """
        Returns the JSON schema of the operation's input arguments.
        """
        return {
                    "type": "object",
                    "properties": {
                        "table": {
                            "type": "object",
                            "description": "A table represented as a list of dictionaries, where each dictionary is a row with key-value pairs.",
                            "properties": {
                                "results": {
                                    "type": "object",
                                    "properties": {
                                        "bindings": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "description": "A row in the table, represented as a dictionary of key-value pairs."
                                            }
                                        }
                                    },
                                    "required": ["bindings"]
                                }
                            },
                            "required": ["results"]
                        },
                        "operation": {
                            "oneOf": [
                                {"type": "string", "description": "Single operation to execute for each row"},
                                {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of operations to execute for each row"
                                }
                            ],
                            "description": "Operation(s) to execute for each row in the table"
                        }
                    },
                    "required": ["table", "operation"],
                }


    def execute(
        self,
        arguments: dict[str, Any]
    ) -> list:
        """
        Executes the operation(s) for each row in the resolved table.
        :param arguments: A dictionary containing:
            - `table`: A list of dictionaries representing the table rows.
            - `operation`: The operation(s) to execute for each row. This can be a single operation or a list of operations.
        :return: A list of results, where each item corresponds to the result(s) for a row.
        """
        table = Operation.execute_json(self.settings, arguments["table"], self.context)
        bindings = table["results"]["bindings"]
        op = arguments["operation"]  # raw!

        logging.info("Executing ForEach operation on %d rows with operation: %s", len(bindings), op)

        results = []
        for row in bindings:
            logging.info("Processing row: %s", row)
            result = Operation.execute_json(self.settings, op, context=row)
            results.append(result)

        return results

    def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        results = self.execute(arguments)
        return [types.TextContent(type="text", text=str(result)) for result in results]
