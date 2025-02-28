from typing import Any
from operation import Operation

class ValueOf(Operation):
    """
    Retrieves a value from the execution context based on a given variable (key).
    """

    def __init__(self, context: dict = None, var: str = None):
        """
        Initialize ValueOf with execution context.
        :param context: The execution context.
        :param var: The key whose value should be retrieved.
        """
        super().__init__(context)

        if var is None:
            raise ValueError("ValueOf operation requires 'key' to be set.")
        
        self.var = var

    def execute(self) -> str:
        """
        Retrieves a value from the execution context.
        :return: The value corresponding to the key.
        :raises ValueError: If the key is not found.
        """

        if self.var not in self.context:
            raise ValueError(f"Key '{self.var}' not found in context.")

        return self.context[self.var] # because SPARQL results binding is a dict: {'type': 'literal', 'xml:lang': 'en', 'value': 'Whatever'}
