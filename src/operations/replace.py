import logging
import re
from typing import Any
from operation import Operation

class Replace(Operation):
    """
    Replaces occurrences of a specified pattern in an input string with a given replacement.
    Aligns with SPARQL's REPLACE() function.
    """

    @property
    def description(self) -> str:
        return "Replaces occurrences of a specified pattern in an input string with a given replacement. This operation aligns with SPARQL's REPLACE() function, allowing for flexible string manipulation using regular expressions."

    def execute(self, arguments: dict[str, Any]) -> str:
        """
        Performs string replacement using a regular expression.
        :return: The formatted string.
        """
        input: Any = arguments["input"]  # The input string to process
        pattern: Any = arguments["pattern"] # The pattern to be replaced (or a nested operation producing it)
        replacement: Any = arguments["replacement"] # The replacement value (or a nested operation producing it)

        logging.info("Resolving Replace arguments: input=%s, pattern=%s, replacement=%s", input, pattern, replacement)

        if not isinstance(input, str):
            raise ValueError("Replace 'input' must resolve to a string.")
        if not isinstance(pattern, str):
            raise ValueError("Replace 'pattern' must resolve to a string.")
        
        formatted_string = re.sub(pattern, str(replacement), input)

        logging.info("Formatted result: %s", formatted_string) 
        return formatted_string
