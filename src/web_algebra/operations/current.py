from typing import Any
from web_algebra.exceptions import NoFocusError
from web_algebra.focus import Focus
from web_algebra.operation import Operation


class Current(Operation):
    """
    Returns the current ForEach sequence item (like XSLT's current() or select=".").
    This allows capturing the current item in sequence-based ForEach operations.
    """

    @classmethod
    def description(cls) -> str:
        return """Returns the current ForEach sequence item.
        
        Similar to XSLT's current() function or select=".", this returns the current
        item from a ForEach sequence operation. Used to access the current sequence
        item within ForEach operation processing.
        
        Returns the current sequence item directly."""

    @classmethod
    def inputSchema(cls) -> dict:
        return {"type": "object", "properties": {}, "additionalProperties": False}

    def execute(self, current_item: Any) -> Any:
        """Pure function: return current sequence item"""
        return current_item

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Any:
        """JSON execution: return the current focus item"""
        # The focus is established by ForEach (formal-semantics.md §3.5);
        # Current yields its item.
        if isinstance(self.context, Focus):
            return self.execute(self.context.item)

        # No focus established — the interpreter's default context is an
        # empty dict.
        if self.context is None or (
            isinstance(self.context, dict) and not self.context
        ):
            raise NoFocusError(
                "Current requires an iteration focus (only ForEach establishes one)"
            )

        return self.execute(self.context)
