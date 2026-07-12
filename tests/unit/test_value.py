"""Spec: formal-semantics.md §4.1 "Value" with §3.4 (variable environment)
and §3.5 (context).
Abstract: String → Any
- `$name` searches variable scopes innermost to outermost; miss → ValueError.
- Unprefixed `name` looks up in the context item: Binding → bound term,
  mapping → member value, other object → attribute; miss → ValueError.
- The `$` sigil decides the lookup domain, so the two never shadow each other.
"""

from __future__ import annotations

import pytest
from rdflib import Literal

from web_algebra.operation import Operation


class TestValuePure:
    def test_lookup_in_innermost_scope(self, settings):
        # Variable System property: lexical scoping, innermost-first.
        op = Operation.get("Value")(settings=settings)
        stack = [{"x": Literal("outer")}, {"x": Literal("inner")}]
        result = op.execute("$x", {}, stack)
        assert result == Literal("inner")

    def test_lookup_falls_back_to_outer_scope(self, settings):
        op = Operation.get("Value")(settings=settings)
        stack = [{"x": Literal("outer")}, {"y": Literal("inner-only")}]
        result = op.execute("$x", {}, stack)
        assert result == Literal("outer")

    def test_mapping_context_lookup(self, settings):
        # §3.5: mapping focus item → member value
        op = Operation.get("Value")(settings=settings)
        result = op.execute("city", {"city": Literal("Vilnius")}, [])
        assert result == Literal("Vilnius")

    def test_lookup_unwraps_the_focus(self, settings):
        # §3.5: the unprefixed lookup targets the focus *item*
        from web_algebra.focus import Focus

        op = Operation.get("Value")(settings=settings)
        focus = Focus(item={"city": Literal("Vilnius")}, position=1, size=1)
        assert op.execute("city", focus, []) == Literal("Vilnius")

    def test_attribute_context_lookup(self, settings):
        # §3.5: any other object → the attribute of that name
        class Item:
            city = Literal("Kaunas")

        op = Operation.get("Value")(settings=settings)
        result = op.execute("city", Item(), [])
        assert result == Literal("Kaunas")

    def test_sigil_selects_lookup_domain(self, settings):
        # §3.4: `$name` reads the variable stack, plain `name` the context —
        # the same name in both never shadows.
        op = Operation.get("Value")(settings=settings)
        context = {"x": Literal("from-context")}
        stack = [{"x": Literal("from-stack")}]
        assert op.execute("$x", context, stack) == Literal("from-stack")
        assert op.execute("x", context, stack) == Literal("from-context")

    def test_missing_variable_raises_value_error(self, settings):
        # §3.7: unknown variable in `$name` lookup → ValueError
        op = Operation.get("Value")(settings=settings)
        with pytest.raises(ValueError):
            op.execute("$missing", {}, [])

    def test_missing_context_member_raises_value_error(self, settings):
        # §3.7: context lookup miss → ValueError
        op = Operation.get("Value")(settings=settings)
        with pytest.raises(ValueError):
            op.execute("missing", {"other": Literal("v")}, [])


class TestValueJson:
    def test_json_dispatch(self, settings):
        # §4.1 JSON: name: String (plain JSON string, `$` prefix for variables)
        op = Operation.get("Value")(settings=settings)
        result = op.execute_json(
            {"name": "$x"}, [{"x": Literal("bound")}]
        )
        assert result == Literal("bound")
