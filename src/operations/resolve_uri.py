from typing import Dict
from urllib.parse import urljoin
from operation import Operation

class ResolveURI(Operation):
    """
    Resolves a relative URI against a base URI.
    """

    base: str  # The base URL against which the relative URI is resolved
    relative: Dict  # The relative URI, which can be a string or a nested operation producing the URI

    @property
    def description(self) -> str:
        return """
        Creates a new URI relative to the base URL. The relative URI **must** be pre-encoded.
        """
    
    def execute(self) -> str:
        """
        Resolves a relative URI against a base URI.
        :return: The resolved absolute URI as a string.
        """
        # ✅ Resolve `relative` dynamically
        relative_value = self.resolve_arg(self.relative)
        return str(urljoin(self.base, relative_value))
