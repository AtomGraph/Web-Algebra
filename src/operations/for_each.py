from typing import Any
import logging
from operation import Operation

class ForEach(Operation):
    """
    Executes an operation (or a sequence of operations) for each row in a table.
    """

    def __init__(self, context: dict = None, table: dict = None, operation: Any = None):
        """
        Initialize ForEach with execution context.
        :param context: The current execution context.
        :param table: The JSON operation that produces a table (not resolved yet).
        :param operation: A single operation or a list of operations to apply to each row.
        """
        super().__init__(context)

        if table is None:
            raise ValueError("ForEach operation requires 'table' to be set.")
        if operation is None:
            raise ValueError("ForEach operation requires 'operation' to be set.")
        
        self.table = table
        self.operation = operation

    def execute(self)-> list:
        """
        Executes the operation(s) for each row in the resolved table.
        :return: A list of results, where each item corresponds to the result(s) for a row.
        """
        logging.info(f"Resolving ForEach 'table': {self.table}")

        # ✅ Resolve `table` dynamically
        resolved_table = self.resolve_arg(self.table)

        logging.info(f"ForEach resolved table: {resolved_table} (Type: {type(resolved_table)})")

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
