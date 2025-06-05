from typing import Any
import logging
from operation import Operation

class ForEach(Operation):
    """
    Executes an operation (or a sequence of operations) for each row in a table.
    """

    @property
    def description(self) -> str:
        return "Executes an operation for each row in a table. The operation can be a single operation or a list of operations. Each row is processed independently, and the results are collected in a list."
    
    @property
    def inputSchema(self):
        """
        Returns the JSON schema of the operation's input arguments.
        """
        return {
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "SELECT query to execute"},
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

        results = []
        for row in bindings:
            result = Operation.execute_json(self.settings, op, context=row)
            results.append(result)

        return results
