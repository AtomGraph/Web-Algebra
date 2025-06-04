from typing import Any
from operation import Operation

class ValueOf(Operation):
    """
    Retrieves a value from the execution context based on a given variable (key).
    """

    var: str  # The key whose value should be retrieved from the context

    def execute(self) -> str:
        """
        Retrieves a value from the execution context.
        :return: The value corresponding to the key.
        :raises ValueError: If the key is not found.
        """

        if self.var not in self.context:
            raise ValueError(f"Key '{self.var}' not found in context.")

        return self.context[self.var] # because SPARQL results binding is a dict: {'type': 'literal', 'xml:lang': 'en', 'value': 'Whatever'}
