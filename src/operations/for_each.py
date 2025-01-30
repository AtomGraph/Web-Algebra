import logging
from operation import Operation

class ForEach(Operation):
    def __init__(self, context: dict = None, table: dict = None, operation: dict = None):
        """
        Initialize ForEach with execution context.
        :param context: The current execution context.
        :param table: The JSON operation that produces a table (not resolved yet).
        :param operation: The JSON operation to apply to each row.
        """
        super().__init__(context)

        if table is None:
            raise ValueError("ForEach operation requires 'table' to be set.")
        if operation is None:
            raise ValueError("ForEach operation requires 'operation' to be set.")
        
        self.table = table  # ✅ Store JSON representation, do NOT resolve yet
        self.operation = operation  # ✅ Store JSON representation, do NOT resolve yet


    def execute(self):
        """
        Executes the operation for each row in the resolved table.

        :return: A list of results from applying the operation to each row.
        :raises ValueError: If the resolved table is not a list of dictionaries.
        """
        logging.info(f"Resolving ForEach 'table': {self.table}")

        # ✅ Resolve `table` dynamically using
        resolved_table = self.resolve_arg(self.table)

        logging.info(f"ForEach resolved table: {resolved_table} (Type: {type(resolved_table)})")

        if not isinstance(resolved_table, list):
            raise ValueError("ForEach 'table' must be a list of dictionaries.")

        results = []
        for index, row in enumerate(resolved_table):
            if not isinstance(row, dict):
                raise ValueError("Each row in ForEach 'table' must be a dictionary.")

            logging.info(f"Processing row {index + 1}/{len(resolved_table)}: {row}")

            # ✅ Resolve `operation` for each row dynamically
            result = self.execute_json(self.operation, row)
            logging.info(f"Row {index + 1} result: {result}")
            results.append(result)

        logging.info("ForEach execution completed.")
        return results
