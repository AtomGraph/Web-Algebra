from typing import Any
from urllib.parse import urljoin
from operation import Operation

class ResolveURI(Operation):
    """
    Resolves a relative URI against a base URI.
    """

    @property
    def description(self) -> str:
        return """
        Creates a new URI relative to the base URL. The relative URI **must** be pre-encoded.
        """
    
    def execute(self, arguments: dict[str, Any]) -> str:
        """
        Resolves a relative URI against a base URI.
        :param arguments: A dictionary containing:
            - `base`: The base URI to resolve against.
            - `relative`: The relative URI to resolve.
        :return: The resolved absolute URI as a string.
        """
        base: str = arguments["base"]
        value: str = arguments["relative"]

        if not isinstance(base, str):
            raise ValueError("Replace 'base' must resolve to a string.")
        if not isinstance(value, str):
            raise ValueError("Replace 'value' must resolve to a string.")

        return str(urljoin(self.base, value))
