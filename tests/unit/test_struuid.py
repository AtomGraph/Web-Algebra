"""Spec: formal-semantics.md §4.2 "StrUUID" (deprecated alias `STRUUID`)
Abstract: () → Literal
Python:   def execute(self) -> Literal
"""

from __future__ import annotations

from rdflib import Literal

from web_algebra.operation import Operation


class TestStrUUIDPure:
    def test_returns_literal(self, settings):
        op = Operation.get("StrUUID")(settings=settings)
        result = op.execute()
        assert isinstance(result, Literal)

    def test_two_calls_differ(self, settings):
        op = Operation.get("StrUUID")(settings=settings)
        a = op.execute()
        b = op.execute()
        assert str(a) != str(b)

    def test_uuid_format(self, settings):
        # §4.2: simple literal per `simple literal STRUUID()`, holding an
        # RFC 4122 version-4 UUID in lowercase hyphenated form
        import re

        op = Operation.get("StrUUID")(settings=settings)
        result = op.execute()
        assert result.datatype is None and result.language is None
        assert re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
            str(result),
        )


class TestStrUUIDJson:
    def test_empty_args_via_json(self, settings):
        # () → Literal — JSON layer should accept an empty args dict
        op = Operation.get("StrUUID")(settings=settings)
        result = op.execute_json({})
        assert isinstance(result, Literal)


class TestSTRUUIDAlias:
    """§4 Names: a deprecated alias names the same operation and is accepted
    wherever the name is."""

    UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"

    def test_the_alias_evaluates_in_a_plan(self, settings):
        import re

        result = Operation.process_json(settings, {"@op": "STRUUID", "args": {}})
        assert isinstance(result, Literal)
        assert re.fullmatch(self.UUID, str(result))

    def test_the_alias_names_the_same_operation(self, settings):
        assert Operation.get("STRUUID") is Operation.get("StrUUID")

    def test_the_alias_inside_a_composition(self, settings):
        result = Operation.process_json(
            settings,
            {"@op": "Concat", "args": {"inputs": ["id-", {"@op": "STRUUID", "args": {}}]}},
        )
        assert str(result).startswith("id-") and len(str(result)) == 3 + 36
