from typing import Any
from mcp import types
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
        """JSON execution: return current context item"""
        # No iteration context established (formal-semantics.md §3.5) — the
        # interpreter's default context is an empty dict.
        if self.context is None or (
            isinstance(self.context, dict) and not self.context
        ):
            raise ValueError(
                "Current requires an iteration context (only ForEach establishes one)"
            )

        return self.execute(self.context)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        # For MCP, we just return a placeholder since context handling is JSON-specific
        return [types.TextContent(type="text", text="Current context accessed")]
