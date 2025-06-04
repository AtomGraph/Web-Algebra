import logging
from urllib.parse import quote
from typing import Any
from operation import Operation

class EncodeForURI(Operation):
    """
    URL-encodes a string to make it safe for use in URIs, following SPARQL's `ENCODE_FOR_URI` behavior.
    """    
    @property
    def description(self) -> str:
        return "Encodes a string to be URI-safe, following SPARQL's `ENCODE_FOR_URI` behavior. It encodes characters that are not allowed in URIs, such as spaces, slashes, and colons."
    
    def execute(self, arguments: dict[str, Any]) -> str:
        """        Executes the EncodeForURI operation.
        :param arguments: A dictionary containing the input string to encode.
        :return: A string with the encoded URI string."""
        input: Any = arguments("input")
        logging.info("Resolving input for EncodeForURI: %s", input)

        if isinstance(input, dict):
            if "value" not in input:
                raise ValueError(f"EncodeForURI expected a 'value' key, found: {input}")
            input = input["value"]  # Extract the string

        # ✅ Ensure we now have a string
        if not isinstance(input, str):
            raise ValueError(f"EncodeForURI operation requires 'input' to be a string, found: {input}")

        # ✅ Encode using XPath encode-for-uri() behavior (encode slashes, colons, etc.)
        encoded_value = quote(input, safe="")  # 🔥 No safe characters

        logging.info("Encoded URI: %s", encoded_value)
        return encoded_value
