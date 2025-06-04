from typing import Any
import logging
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from operation import Operation

class ForEach(Operation):
    """
    Executes an operation (or a sequence of operations) for each row in a table.
    """

    #table: dict  # The JSON operation that produces a table (not resolved yet)
    #operation: Any  # A single operation or a list of operations to apply to each row

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
        :return: A list of results, where each item corresponds to the result(s) for a row.
        """
        logging.info("Resolving ForEach 'table': %s", arguments["table"])

        # ✅ Resolve `table` dynamically
        resolved_table = self.resolve_arg(arguments["table"])

        logging.info(f"ForEach resolved table: {resolved_table} (Type: %s)", type(resolved_table))

        if not isinstance(resolved_table, list):
            raise ValueError("ForEach 'table' must be a list of dictionaries.")

        results = []
        for index, row in enumerate(resolved_table):
            if not isinstance(row, dict):
                raise ValueError("Each row in ForEach 'table' must be a dictionary.")

            logging.info(f"Processing row {index + 1}/{len(resolved_table)}: {row}")

            if isinstance(self.operation, list):
                row_results = [self.execute_json(op, row) for op in self.operation]
            else:
                row_results = self.execute_json(self.operation, row)

            results.append(row_results)

        logging.info("ForEach execution completed.")
        return results
