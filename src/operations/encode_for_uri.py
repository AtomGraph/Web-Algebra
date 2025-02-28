import logging
from urllib.parse import quote
from typing import Any
from operation import Operation

class EncodeForURI(Operation):
    """
    URL-encodes a string to make it safe for use in URIs, following SPARQL's `ENCODE_FOR_URI` behavior.
    """

    def __init__(self, context: dict = None, input: Any = None):
        """
        Initialize EncodeForURI with execution context.
        :param context: The execution context.
        :param input: The string to be encoded, or a nested operation producing the input string.
        """
        super().__init__(context)

        if input is None:
            raise ValueError("EncodeForURI operation requires 'input' to be set.")
        
        self.input = input  # ✅ Might be a direct string or another operation
        
    def execute(self) -> str:
        """
        Encodes a string to be URI-safe.
        :return: The encoded string.
        """
        logging.info(f"Resolving input for EncodeForURI: {self.input}")

        # ✅ Resolve `input` dynamically
        resolved_input = self.resolve_arg(self.input)

        # ✅ Extract the value if it's in RDF-style dict format
        if isinstance(resolved_input, dict):
            if "value" not in resolved_input:
                raise ValueError(f"EncodeForURI expected a 'value' key, found: {resolved_input}")
            resolved_input = resolved_input["value"]  # Extract the string

        # ✅ Ensure we now have a string
        if not isinstance(resolved_input, str):
            raise ValueError(f"EncodeForURI operation requires 'input' to be a string, found: {resolved_input}")

        # ✅ Encode using XPath encode-for-uri() behavior (encode slashes, colons, etc.)
        encoded_value = quote(resolved_input, safe="")  # 🔥 No safe characters

        logging.info(f"Encoded URI: {encoded_value}")
        return encoded_value
