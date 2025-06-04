import logging
import re
from typing import Any
from operation import Operation

class Replace(Operation):
    """
    Replaces occurrences of a specified pattern in an input string with a given replacement.
    Aligns with SPARQL's REPLACE() function.
    """

    input: Any  # The input string (or a nested operation producing it)
    pattern: Any  # The pattern to be replaced (or a nested operation producing it)
    replacement: Any  # The replacement value (or a nested operation producing it)

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
