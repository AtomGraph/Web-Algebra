import logging
from typing import Any
from operation import Operation

class FormatString(Operation):
    """
    Formats a string by replacing occurrences of a specified placeholder with a given replacement.
    """

    def __init__(self, context: dict = None, input: Any = None, placeholder: Any = None, replacement: Any = None):
        """
        Initialize FormatString with execution context.
        :param input: The input string to format (or a nested operation producing a string).
        :param placeholder: The placeholder string to be replaced (or a nested operation producing it).
        :param replacement: The replacement value (or a nested operation producing it).
        :param context: The execution context.
        """
        super().__init__(context)

        # ✅ Validate presence of required arguments **before** setting them
        if input is None:
            raise ValueError("FormatString operation requires an 'input' string.")
        if placeholder is None:
            raise ValueError("FormatString operation requires a 'placeholder' string.")
        if replacement is None:
            raise ValueError("FormatString operation requires a 'replacement' value.")

        self.input = input
        self.placeholder = placeholder
        self.replacement = replacement

    def execute(self) -> str:
        """
        Performs string formatting by replacing the placeholder with the replacement value.
        :return: The formatted string.
        """
        logging.info(f"Resolving FormatString arguments: input={self.input}, placeholder={self.placeholder}, replacement={self.replacement}")

        # ✅ Resolve arguments dynamically if they are nested operations
        resolved_input = self.resolve_arg(self.input)
        resolved_placeholder = self.resolve_arg(self.placeholder)
        resolved_replacement = self.resolve_arg(self.replacement)

        # ✅ Ensure resolved values are strings
        if not isinstance(resolved_input, str):
            raise ValueError("FormatString 'input' must resolve to a string.")
        if not isinstance(resolved_placeholder, str):
            raise ValueError("FormatString 'placeholder' must resolve to a string.")

        logging.info(f"Replacing '{resolved_placeholder}' with '{resolved_replacement}' in '{resolved_input}'")
        
        # ✅ Perform string replacement
        formatted_string = resolved_input.replace(f"${{{resolved_placeholder}}}", str(resolved_replacement))

        logging.info(f"Formatted result: {formatted_string}")
        return formatted_string
