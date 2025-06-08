from typing import Any
import logging
from web_algebra.operation import Operation

class Var(Operation):
    """
    Retrieves a value from the execution context based on a given variable (key) and returns it as an RDF term dict.
    """

    @classmethod
    def description(cls) -> str:
        return "Retrieves a value from the execution context based on a given variable (key) and returns it as an RDF term dict. This operation is useful for accessing previously stored values in the context, similar to SPARQL's `?var` syntax."

    @classmethod
    def inputSchema(cls) -> dict:
        """
        Returns the JSON schema of the operation's input arguments.
        """
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The key to look up in the context."
                }
            },
            "required": ["name"],
        }
    
    def execute(self, arguments: dict[str, Any]) -> dict:
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

        return self.context[var] # because SPARQL results binding is a dict: {'var': {'type': 'literal', 'xml:lang': 'en', 'value': 'Whatever'} }

