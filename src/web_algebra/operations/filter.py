from typing import Any, Union
from mcp import types
from web_algebra.operation import Operation


class Filter(Operation):
    """
    Filters SPARQL results using filter expressions, similar to XSLT predicates.
    Currently supports positional filtering (e.g., [1], [2]) with future extensibility.
    """

    @classmethod
    def description(cls) -> str:
        return """Filters SPARQL results using filter expressions, similar to XSLT predicates.
        
        Currently supports positional access:
        - Numeric values select by position (1-based, following XSLT convention)
        - Returns the filtered SPARQL results with matching bindings
        
        Future versions may support field-based and complex filter expressions."""

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {"description": "SPARQL results to filter."},
                "expression": {
                    "description": "Filter expression. Supports positional integers (1-based index) and will support more expression types in the future."
                },
            },
            "required": ["input", "expression"],
            "additionalProperties": False,
        }

    def execute(self, input_data: Any, expression: Any) -> Union[list, Any]:
        """Pure function: filter any iterable with filter expression"""
        # Convert any iterable to list for processing
        if hasattr(input_data, "__iter__"):
            items = list(input_data)
        else:
            raise TypeError(f"Filter expects iterable input, got {type(input_data)}")

        # Handle different expression types
        if isinstance(expression, int):
            # Positional filtering (current implementation)
            filtered_items = self._apply_positional_filter(items, expression)
        else:
            # Future: could support other expression types (boolean expressions, etc.)
            raise NotImplementedError(
                f"Filter expression type {type(expression)} not yet supported"
            )

        # Return single item directly if only one result (XSLT semantics)
        if len(filtered_items) == 1:
            return filtered_items[0]
        return filtered_items

    def execute_json(
        self, arguments: dict, variable_stack: list = []
    ) -> Union[list, Any]:
        """JSON execution: process arguments with support for both Result and sequence"""
        # Process input
        input_data = Operation.process_json(
            self.settings, arguments["input"], self.context, variable_stack
        )

        # Process expression
        expression_data = Operation.process_json(
            self.settings, arguments["expression"], self.context, variable_stack
        )
        if not isinstance(expression_data, int):
            raise TypeError(
                f"Filter operation expects 'expression' to be int, got {type(expression_data)}"
            )

        return self.execute(input_data, expression_data)

    def _apply_positional_filter(self, bindings: list, position: int) -> list:
        """
        Apply positional filter (1-based indexing like XSLT).

        :param bindings: List of RDFLib term bindings
        :param position: 1-based position to select
        :return: List containing single binding at the specified position
        """
        if position < 1:
            raise ValueError("Position must be >= 1 (XSLT-style 1-based indexing)")

        if position > len(bindings):
            raise ValueError(
                f"Position {position} exceeds number of bindings ({len(bindings)})"
            )

        # Convert to 0-based index for Python list access and return as list
        return [bindings[position - 1]]

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        # Convert plain args to RDFLib terms
        input_json = arguments["input"]
        from web_algebra.json_result import JSONResult

        input_result = JSONResult.from_json(input_json)
        expression = arguments["expression"]

        result = self.execute(input_result, expression)

        # Return summary for MCP
        return [
            types.TextContent(
                type="text", text=f"Filtered to {len(result.bindings)} result(s)"
            )
        ]
