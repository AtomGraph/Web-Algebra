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
                        "table": {"type": "string", "description": "SELECT SQL query to execute"},
                    },
                    "required": ["table", "operation"],
                }


    def execute(
        self,
        arguments: dict[str, Any]
    ) -> Any:
        """
        Executes the operation(s) for each row in the resolved table.
        :param arguments: A dictionary containing:
            - `table`: A list of dictionaries representing the table rows.
            - `operation`: The operation(s) to execute for each row. This can be a single operation or a list of operations.
        :return: A list of results, where each item corresponds to the result(s) for a row.
        """
        table: list = arguments["table"]
        operation: Operation = arguments["operation"]
        logging.info("ForEach table: {%s} (Type: %s)", table, type(table))

        if not isinstance(table, list):
            raise ValueError("ForEach 'table' must be a list of dictionaries.")

        results = []
        for index, row in enumerate(table):
            if not isinstance(row, dict):
                raise ValueError("Each row in ForEach 'table' must be a dictionary.")

            logging.info(f"Processing row {index + 1}/{len(table)}: {row}")

            if isinstance(operation, list):
                row_results = [self.execute_json(op, row) for op in operation]
            else:
                row_results = self.execute_json(operation, row)

            results.append(row_results)

        logging.info("ForEach execution completed.")
        return results
