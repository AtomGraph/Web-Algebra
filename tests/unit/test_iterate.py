"""Spec: formal-semantics.md §4.1 "Iterate — stateful iteration with
parameter passing between iterations" and §3.8 (ITERATE).
Abstract: (Name ⇀ Value) × Operation⟨quoted⟩
          × Maybe (Name ⇀ Operation⟨quoted⟩) × Maybe Break → Sequence β
- params bound as loop variables; without next-iteration exactly one
  iteration runs; next-iteration members are evaluated in the iteration's
  environment (loop params + body bindings) and rebind the parameters;
  break compares a loop variable's lexical form after rebinding; the
  iteration count is capped at 1000 (normative); Unit-valued iterations are
  dropped; Iterate establishes no focus.
"""

from __future__ import annotations

import pytest
from rdflib import Literal

from web_algebra.operation import Operation


def _str_of(name: str) -> dict:
    return {"@op": "Str", "args": {"input": {"@op": "Value", "args": {"name": name}}}}


class TestIterateJson:
    def test_single_iteration_without_next_iteration(self, settings):
        # §4.1: without next-iteration, exactly one iteration runs;
        # params are bound as variables and read via $name
        op = Operation.get("Iterate")(settings=settings)
        result = op.execute_json(
            {"params": {"url": "https://ex/items"}, "operation": _str_of("$url")}
        )
        assert result == [Literal("https://ex/items")]

    def test_next_iteration_rebinds_until_break(self, settings):
        # §3.8 (ITERATE): body → next-iteration → rebind → break test
        op = Operation.get("Iterate")(settings=settings)
        result = op.execute_json(
            {
                "params": {"s": ""},
                "operation": _str_of("$s"),
                "next-iteration": {
                    "s": {
                        "@op": "Concat",
                        "args": {
                            "inputs": [{"@op": "Value", "args": {"name": "$s"}}, "a"]
                        },
                    }
                },
                "break": {"name": "s", "equals": "aaa"},
            }
        )
        assert [str(v) for v in result] == ["", "a", "aa"]

    def test_not_equals_break(self, settings):
        # §4.1: break with not-equals stops as soon as the variable differs
        op = Operation.get("Iterate")(settings=settings)
        result = op.execute_json(
            {
                "params": {"s": "go"},
                "operation": _str_of("$s"),
                "next-iteration": {"s": "stop"},
                "break": {"name": "s", "not-equals": "go"},
            }
        )
        assert [str(v) for v in result] == ["go"]

    def test_body_bindings_visible_to_next_iteration(self, settings):
        # §4.1: next-iteration members are evaluated in the iteration's
        # environment — the loop parameters plus the body's bindings
        op = Operation.get("Iterate")(settings=settings)
        result = op.execute_json(
            {
                "params": {"url": "a"},
                "operation": [
                    {
                        "@op": "Variable",
                        "args": {
                            "name": "page",
                            "value": {
                                "@op": "Concat",
                                "args": {
                                    "inputs": [
                                        {"@op": "Value", "args": {"name": "$url"}},
                                        "!",
                                    ]
                                },
                            },
                        },
                    },
                    _str_of("$page"),
                ],
                "next-iteration": {"url": {"@op": "Value", "args": {"name": "$page"}}},
                "break": {"name": "url", "equals": "a!!!"},
            }
        )
        assert [str(v) for v in result] == ["a!", "a!!", "a!!!"]

    def test_unit_valued_iterations_are_dropped(self, settings):
        # §4.1: Unit-valued iterations are dropped from the output
        op = Operation.get("Iterate")(settings=settings)
        result = op.execute_json(
            {
                "params": {"x": "v"},
                "operation": {
                    "@op": "Variable",
                    "args": {"name": "y", "value": "w"},
                },
            }
        )
        assert result == []

    def test_loop_scope_does_not_leak(self, settings):
        # §3.4: the loop scope (params) and body bindings cease to exist
        # after the Iterate
        op = Operation.get("Iterate")(settings=settings)
        stack: list = [{}]
        op.execute_json(
            {"params": {"url": "a"}, "operation": _str_of("$url")}, stack
        )
        assert stack == [{}]

    def test_iteration_cap_stops_the_loop(self, settings):
        # §4.1: the iteration count is bounded by a normative cap of 1000;
        # reaching it stops the loop and is not an error
        op = Operation.get("Iterate")(settings=settings)
        result = op.execute_json(
            {
                "params": {"s": "x"},
                "operation": _str_of("$s"),
                "next-iteration": {"s": {"@op": "Value", "args": {"name": "$s"}}},
                "break": {"name": "s", "equals": "never"},
            }
        )
        assert len(result) == 1000

    def test_enclosing_focus_remains_visible(self, settings):
        # §4.1: Iterate establishes no focus; the enclosing one is visible
        for_each = Operation.get("ForEach")(settings=settings)
        result = for_each.execute_json(
            {
                "select": ["a"],
                "operation": {
                    "@op": "Iterate",
                    "args": {
                        "operation": {
                            "@op": "Str",
                            "args": {"input": {"@op": "Current", "args": {}}},
                        }
                    },
                },
            }
        )
        assert result == [[Literal("a")]]

    def test_missing_operation_raises_key_error(self, settings):
        # §3.7: missing required argument key → KeyError
        op = Operation.get("Iterate")(settings=settings)
        with pytest.raises(KeyError):
            op.execute_json({"params": {"x": "v"}})

    def test_break_requires_exactly_one_comparison(self, settings):
        # §4.1: exactly one of equals/not-equals → ValueError otherwise
        op = Operation.get("Iterate")(settings=settings)
        with pytest.raises(ValueError):
            op.execute_json(
                {
                    "operation": _str_of("$s"),
                    "params": {"s": "x"},
                    "break": {"name": "s"},
                }
            )
        with pytest.raises(ValueError):
            op.execute_json(
                {
                    "operation": _str_of("$s"),
                    "params": {"s": "x"},
                    "break": {"name": "s", "equals": "a", "not-equals": "b"},
                }
            )

    def test_malformed_arguments_raise_type_error(self, settings):
        # §3.7: argument of the wrong type → TypeError
        op = Operation.get("Iterate")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json({"operation": _str_of("$s"), "params": "not-an-object"})
        with pytest.raises(TypeError):
            op.execute_json(
                {"operation": _str_of("$s"), "break": "not-an-object"}
            )
