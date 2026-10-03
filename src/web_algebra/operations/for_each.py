from typing import Any, Callable, Dict, List, Union
import logging
from web_algebra.exceptions import SameTargetError
from web_algebra.focus import Focus, report_write
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
        
        Returns the concatenation of the iteration values, in item order."""

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
        """Interpreter-level special form — no pure form (formal-semantics.md §4.1).

        `ForEach` evaluates a *quoted* operand once per item under a per-item
        focus and variable scope; that requires the interpreter, so it has no
        pure `execute()` and lives entirely in `execute_json`.
        """
        raise NotImplementedError(
            "ForEach is an interpreter-level special form (formal-semantics.md "
            "§4.1); use execute_json"
        )

    def execute_json(self, arguments: dict, variable_stack: list = None) -> List[Any]:
        """JSON execution: apply operations to each item in sequence or SPARQL results"""
        if variable_stack is None:
            variable_stack = []
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

        results: List[Any] = []
        size = len(items)
        # §3.6: the iterations' writes go through one gate, which refuses a
        # URI that two iterations write (XSLT's XTDE1490). Within one
        # iteration the sequence form orders the writes, so repeats are fine.
        writers: Dict[str, int] = {}
        for position, item in enumerate(items, start=1):
            logging.info("Processing item: %s", item)

            # The focus (item, position, size) per formal-semantics.md §3.5,
            # accessed by Current/Position/Last and focus-item Value lookups.
            focus = Focus(
                item=item,
                position=position,
                size=size,
                written=self._gate(writers, position),
            )

            # Each iteration runs in a fresh variable scope
            # (formal-semantics.md §3.4): bindings made inside one iteration
            # do not leak into the next.
            variable_stack.append({})
            try:
                # An array operand is a sequence constructor evaluated within
                # the iteration's scope; either way the iteration's value is
                # concatenated into the result (§3.1, §4.1).
                forms = operation if isinstance(operation, list) else [operation]
                for form in forms:
                    Operation.concatenate(
                        results,
                        Operation.process_json(
                            self.settings,
                            form,
                            context=focus,
                            variable_stack=variable_stack,
                        ),
                    )
            finally:
                variable_stack.pop()

        return results

    def _gate(self, writers: Dict[str, int], position: int) -> Callable[[str], None]:
        """The write gate of iteration `position`. An update inside a nested
        ForEach counts for every enclosing iteration too, so the report is
        passed on to the gate of the focus this ForEach runs under."""

        def written(url: str) -> None:
            other = writers.setdefault(url, position)
            if other != position:
                raise SameTargetError(
                    f"ForEach wrote {url} from iterations {other} and {position}: "
                    "two iterations updating one URI are an error "
                    "(formal-semantics.md §3.6)"
                )
            report_write(self.context, url)

        return written
