from typing import Any, List, Union
import logging
from mcp import types
from web_algebra.operation import Operation
from rdflib.query import Result


class ForEach(Operation):
    """
    Applies operations to each item in sequences or SPARQL results, similar to XSLT's xsl:for-each
    """

    @classmethod
    def description(cls) -> str:
        return """Applies operations to each item in sequences or SPARQL results.
        
        Similar to XSLT's <xsl:for-each select="...">, this operation can iterate over:
        - Sequences: Each item becomes the context for the operation
        - Result (SPARQL results): Each result row (ResultRow) becomes the context
        
        Returns a sequence of operation results."""

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "select": {
                    "description": "Sequence or Result to iterate over (like XSLT's select attribute)"
                },
                "operation": {"description": "Operation(s) to execute for each item"},
            },
            "required": ["select", "operation"],
        }

    def execute(
        self, select_data: Union[List[Any], Result], operation: Any
    ) -> List[Any]:
        """Pure function: apply operation to each item in sequence or SPARQL results"""
        # This is complex because we need to execute operations with context
        # For now, this will be handled in execute_json
        raise NotImplementedError(
            "ForEach pure function needs operation execution context"
        )

    def execute_json(self, arguments: dict, variable_stack: list = []) -> List[Any]:
        """JSON execution: apply operations to each item in sequence or SPARQL results"""
        # Get the select data (sequence or Result)
        select_data = Operation.process_json(
            self.settings, arguments["select"], self.context, variable_stack
        )

        operation = arguments["operation"]  # raw operation

        # Determine iteration items based on select data type
        if isinstance(select_data, list):
            # Sequence iteration
            items = select_data
            logging.info(
                "Executing ForEach operation on %d sequence items with operation: %s",
                len(items),
                operation,
            )
        elif isinstance(select_data, Result):
            # SPARQL results iteration - use built-in Result iteration
            items = list(
                select_data
            )  # Result provides iteration over ResultRow objects
            logging.info(
                "Executing ForEach operation on %d SPARQL result rows with operation: %s",
                len(items),
                operation,
            )
        else:
            raise TypeError(
                f"ForEach expects 'select' to be sequence (list) or Result, got {type(select_data)}"
            )

        results = []
        for item in items:
            logging.info("Processing item: %s", item)

            # Handle list of operations or single operation
            if isinstance(operation, list):
                # Execute operations in sequence, with item as context
                last_result = None

                for op in operation:
                    result = Operation.process_json(
                        self.settings, op, context=item, variable_stack=variable_stack
                    )
                    if result is not None:
                        last_result = result

                # Only collect the last non-None result
                if last_result is not None:
                    results.append(last_result)
            else:
                # Single operation
                result = Operation.process_json(
                    self.settings,
                    operation,
                    context=item,
                    variable_stack=variable_stack,
                )
                # Only collect non-None results
                if result is not None:
                    results.append(result)

        return results

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        return [types.TextContent(type="text", text="ForEach operation completed")]
