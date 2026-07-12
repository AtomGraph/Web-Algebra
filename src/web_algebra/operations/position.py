from rdflib import Literal
from rdflib.namespace import XSD

from web_algebra.focus import Focus
from web_algebra.operation import Operation


class Position(Operation):
    """
    Returns the 1-based position of the current focus item, per XPath's
    fn:position().
    """

    @classmethod
    def description(cls) -> str:
        return """Returns the 1-based position of the current iteration item, per XPath's fn:position().

        Only meaningful inside ForEach, which establishes the focus
        (item, position, size); within a focus, 1 <= position <= size."""

    @classmethod
    def inputSchema(cls) -> dict:
        return {"type": "object", "properties": {}, "additionalProperties": False}

    def execute(self, focus: Focus) -> Literal:
        """Pure function: focus → 1-based position as xsd:integer"""
        if not isinstance(focus, Focus):
            raise ValueError(
                "Position requires an iteration focus (only ForEach establishes one)"
            )
        return Literal(focus.position, datatype=XSD.integer)

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Literal:
        """JSON execution: read the position from the current focus"""
        return self.execute(self.context)
