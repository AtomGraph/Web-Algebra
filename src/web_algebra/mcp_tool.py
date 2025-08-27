from abc import ABC, abstractmethod
from typing import Any


class MCPTool(ABC):
    """
    Interface for operations that can be exposed as MCP (Model Context Protocol) tools.

    Operations implementing this interface can be called directly from MCP clients
    like Claude Desktop, providing standalone utility functionality.
    """

    @abstractmethod
    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """
        Execute the operation as an MCP tool with plain arguments.

        Args:
            arguments: Plain dictionary arguments from MCP client
            context: Optional context (usually None for MCP calls)

        Returns:
            List of MCP content objects (TextContent, ImageContent, etc.)
        """
        pass
