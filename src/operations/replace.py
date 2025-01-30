import logging
import re
from typing import Any
from operation import Operation

class Replace(Operation):
    """
    Replaces occurrences of a specified pattern in an input string with a given replacement.
    Aligns with SPARQL's REPLACE() function.
    """

    def __init__(self, context: dict = None, input: Any = None, pattern: Any = None, replacement: Any = None):
        """
        Initialize Replace with execution context.
        :param input: The input string (or a nested operation producing it).
        :param pattern: The pattern to be replaced (or a nested operation producing it).
        :param replacement: The replacement value (or a nested operation producing it).
        :param context: The execution context.
        """
        super().__init__(context)

        # ✅ Validate presence of required arguments **before** setting them
        if input is None:
            raise ValueError("Replace operation requires an 'input' string.")
        if pattern is None:
            raise ValueError("Replace operation requires a 'pattern' string.")
        if replacement is None:
            raise ValueError("Replace operation requires a 'replacement' value.")

        self.input = input
        self.pattern = pattern
        self.replacement = replacement

    def execute(self) -> str:
        """
        Performs string replacement using a regular expression.
        :return: The formatted string.
        """
        logging.info(f"Resolving Replace arguments: input={self.input}, pattern={self.pattern}, replacement={self.replacement}")

        # ✅ Resolve arguments dynamically if they are nested operations
        resolved_input = self.resolve_arg(self.input)
        resolved_pattern = self.resolve_arg(self.pattern)
        resolved_replacement = self.resolve_arg(self.replacement)

        # ✅ Ensure resolved values are strings
        if not isinstance(resolved_input, str):
            raise ValueError("Replace 'input' must resolve to a string.")
        if not isinstance(resolved_pattern, str):
            raise ValueError("Replace 'pattern' must resolve to a string.")

        logging.info(f"Replacing '{resolved_pattern}' with '{resolved_replacement}' in '{resolved_input}'")
        
        # ✅ Perform replacement using regex
        formatted_string = re.sub(resolved_pattern, str(resolved_replacement), resolved_input)

        logging.info(f"Formatted result: {formatted_string}")
        return formatted_string
