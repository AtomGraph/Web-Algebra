from rdflib import Literal
from rdflib.namespace import XSD

from web_algebra.exceptions import NoFocusError
from web_algebra.focus import Focus
from web_algebra.operation import Operation


class Last(Operation):
    """
    Returns the size of the iterated sequence, per XPath's fn:last().
    """

    @classmethod
    def description(cls) -> str:
        return """Returns the size of the sequence being iterated, per XPath's fn:last().

        Only meaningful inside ForEach, which establishes the focus
        (item, position, size)."""

    @classmethod
    def inputSchema(cls) -> dict:
        return {"type": "object", "properties": {}, "additionalProperties": False}

    def execute(self, focus: Focus) -> Literal:
        """Pure function: focus → iteration size as xsd:integer"""
        if not isinstance(focus, Focus):
            raise NoFocusError(
                "Last requires an iteration focus (only ForEach establishes one)"
            )
        return Literal(focus.size, datatype=XSD.integer)

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Literal:
        """JSON execution: read the size from the current focus"""
        return self.execute(self.context)
