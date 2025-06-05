from typing import Any
import logging
from operation import Operation

class Var(Operation):
    """
    Retrieves a value from the execution context based on a given variable (key).
    """

    @property
    def description(self) -> str:
        return "Retrieves a value from the execution context based on a given variable (key). This operation allows for dynamic retrieval of values stored in the context, enabling flexible data access during execution."

    def execute(self, arguments: dict[str, Any]) -> str:
        """
        Retrieves a value from the execution context.
        :param arguments: A dictionary containing:
            - `var`: The key to look up in the context.
        :return: The value corresponding to the key.
        :raises ValueError: If the key is not found.
        """
        var: str = arguments["name"] # The key to look up in the context

        logging.info("Resolving Var variable: %s", var)

        if var not in self.context:
            raise ValueError("Key '%s' not found in context.", var)

        return self.context[var] # because SPARQL results binding is a dict: {'type': 'literal', 'xml:lang': 'en', 'value': 'Whatever'}
