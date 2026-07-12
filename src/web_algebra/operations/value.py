from collections.abc import Mapping
from typing import Any
import logging
from rdflib.query import ResultRow
from mcp import types
from web_algebra.operation import Operation


class Value(Operation):
    """
    Retrieves values from variables or context, returning RDFLib terms
    """

    @classmethod
    def description(cls) -> str:
        return "Retrieves values from variables or context, returning RDFLib terms"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The variable/field name to look up. Use $ prefix for variables.",
                }
            },
            "required": ["name"],
        }

    def execute(self, name: str, context: Any, variable_stack: list) -> Any:
        """Pure function: lookup name in context or variables → value (RDFLib term or raw value)"""
        if name.startswith("$"):
            # Variable reference - return raw value, don't convert to RDFLib
            variable_name = name[1:]
            result = self.get_variable(variable_name, variable_stack)
            logging.info(
                f"Retrieved variable {variable_name} = {result} (type: {type(result)})"
            )
            return result
        else:
            # Context lookup (formal-semantics.md §3.5): Binding → bound term,
            # mapping → member value, other object → attribute.
            if isinstance(context, ResultRow):
                # SPARQL result row - access by variable name
                try:
                    return context[name]  # Already RDFLib term
                except KeyError:
                    raise ValueError(f"Variable '{name}' not found in ResultRow")
            elif isinstance(context, Mapping):
                if name in context:
                    return context[name]
                raise ValueError(f"Context member '{name}' not found in mapping")
            else:
                # Other context types
                if hasattr(context, name):
                    return getattr(context, name)
                raise ValueError(
                    f"Context variable '{name}' not found in {type(context)}"
                )

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Any:
        """JSON execution: processes JSON args, returns value (RDFLib term or raw value)"""
        if variable_stack is None:
            variable_stack = []
        var_name: str = arguments["name"]
        logging.info("Resolving Value variable: %s", var_name)

        return self.execute(var_name, self.context, variable_stack)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        # For MCP, we don't have variable stack or context, so just return the name
        return [types.TextContent(type="text", text=arguments["name"])]
