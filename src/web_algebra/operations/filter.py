from typing import Any, Mapping
from rdflib import Literal
from rdflib.term import Node
from rdflib.namespace import XSD
from rdflib.query import Result, ResultRow
from web_algebra.exceptions import VariableNotFoundError
from web_algebra.operation import Operation


class Filter(Operation):
    """
    Selection by position from a sequence, or by name from a row, XPath-style
    (formal-semantics.md §4.1): `$seq[2]` and `$row?url`.
    """

    @classmethod
    def description(cls) -> str:
        return """Selects an item by position, or a value by name, XPath-style.

        - An integer expression selects by 1-based position from a sequence or
          from a SPARQL result's rows (a result yields a row): like `$seq[2]`.
        - A string expression on a row (a SPARQL binding) yields the term bound
          to that variable name, given bare or as ?name / $name: like `$row?url`.

        Filter(Filter(PUT(...), 1), "url") is the URI a write reports."""

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {
                    "description": "A sequence, a SPARQL result, or one row of a result."
                },
                "expression": {
                    "description": "An integer position (1-based) on a sequence or result, or a variable name on a row."
                },
            },
            "required": ["input", "expression"],
            "additionalProperties": False,
        }

    def execute(self, input_data: Any, expression: Any) -> Any:
        """Pure function: select by position or look up by name"""
        position = self._position(expression)
        name = self._name(expression)
        if position is None and name is None:
            raise TypeError(
                f"Filter expects an integer position or a string name, got {expression!r}"
            )

        if self._is_binding(input_data):
            if name is None:
                raise TypeError(
                    "Filter: a position selects from a sequence; on a row, name the variable to look up"
                )
            return self._lookup(input_data, name)

        if isinstance(input_data, Result):
            items = list(input_data)
        elif isinstance(input_data, list):
            items = input_data
        else:
            raise TypeError(
                f"Filter expects a sequence, a Result or a Binding as input, got {type(input_data).__name__}"
            )

        if position is None:
            raise TypeError(
                "Filter: a name looks a variable up on a row; on a sequence or result, give a position"
            )
        if position < 1:
            raise ValueError("Position must be >= 1 (XSLT-style 1-based indexing)")
        if position > len(items):
            raise ValueError(
                f"Position {position} exceeds number of items ({len(items)})"
            )
        return items[position - 1]

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Any:
        """JSON execution: evaluate both operands, then select"""
        input_data = Operation.process_json(
            self.settings, arguments["input"], self.context, variable_stack
        )
        expression = Operation.process_json(
            self.settings, arguments["expression"], self.context, variable_stack
        )
        return self.execute(input_data, expression)

    @staticmethod
    def _position(expression: Any):
        """The expression as a position: an xsd:integer Literal (what a JSON
        integer coerces to, §2.2) or a plain int from the pure layer."""
        if isinstance(expression, bool):
            return None
        if isinstance(expression, int):
            return expression
        if isinstance(expression, Literal) and expression.datatype == XSD.integer:
            return int(expression)
        return None

    @staticmethod
    def _name(expression: Any):
        """The expression as a variable name, without SPARQL's `?`/`$` sigil."""
        if isinstance(expression, Literal):
            if not Operation.is_string_literal(expression):
                return None
            expression = str(expression)
        # URIRef and BNode are str subclasses, but not names
        elif not isinstance(expression, str) or isinstance(expression, Node):
            return None
        return expression[1:] if expression[:1] in ("?", "$") else expression

    @staticmethod
    def _is_binding(value: Any) -> bool:
        return isinstance(value, (ResultRow, Mapping))

    @staticmethod
    def _lookup(row: Any, name: str) -> Any:
        if isinstance(row, ResultRow):
            value = row.asdict().get(name)
            names = list(row.labels)
        else:
            value = row.get(name)
            names = list(row.keys())
        if value is None:
            raise VariableNotFoundError(
                f"Filter: the row has no binding for {name}; it binds {names}"
            )
        return value
