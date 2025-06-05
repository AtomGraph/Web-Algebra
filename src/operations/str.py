from typing import Any
from operation import Operation

class Str(Operation):
    """
    A base class for string operations.
    This class serves as a foundation for various string manipulation operations.
    """

    @property
    def description(self) -> str:
        return "Base class for string operations. This class provides a common interface and shared functionality for all string-related operations."
    
    @property
    def inputSchema(self):
        """
        Returns the JSON schema of the operation's input arguments.
        """
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "The input string to process"},
            },
            "required": ["input"],
        }
    
    def execute(self, arguments: dict[str, Any]) -> str:
        """
        Executes the string operation.
        :param arguments: A dictionary containing:
            - `input`: The input string to process.
        :return: The processed string.
        """
        input: Any = Operation.execute_json(self.settings, arguments["input"], self.context)
        
        if not isinstance(input, (str, dict)):
            raise ValueError("Input must be a string or an RDF term (dict).")
        
        if isinstance(input, dict):
            if "type" in input and "value" in input:
                # Handle the case where input is a SPARQL result binding
                input = input["value"]
            else:
                raise ValueError("Input must be an RDF term (dict with 'type' and 'value').")

        
        # Placeholder for actual string processing logic
        return input