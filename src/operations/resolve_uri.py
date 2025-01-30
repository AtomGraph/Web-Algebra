from typing import Any
from urllib.parse import urljoin
from operation import Operation

class ResolveURI(Operation):
    """
    Resolves a relative URI against a base URI.
    """

    def __init__(self, context: dict = None, base: str = None, relative: dict = None):
        """
        Initialize ResolveURI with execution context.
        :param context: The execution context.
        :param base: The base URL.
        :param relative: The JSON operation dict representing the relative part (e.g., ValueOf).
        """
        super().__init__(context)

        if base is None:
            raise ValueError("ResolveURI operation requires 'base' to be set.")
        if relative is None:
            raise ValueError("ResolveURI operation requires 'relative' to be set.")
                             
        self.base = base
        self.relative = relative  # ✅ May be a string or a nested operation

    def execute(self) -> str:
        """
        Resolves a relative URI against a base URI.
        :return: The resolved absolute URI as a string.
        """
        # ✅ Resolve `relative` dynamically
        relative_value = self.resolve_arg(self.relative)
        return str(urljoin(self.base, relative_value))
