"""Spec: formal-semantics.md §2.2 (an array is a sequence form, whose value is
the concatenation of its element values), §3.1 (sequences are flat), §4.2
Concat - `inputs` is a sequence form: an element whose value is a sequence
contributes its items, like `fn:string-join(($values, ", "))`.
"""

from __future__ import annotations

from web_algebra.operation import Operation


def _concat(settings, inputs):
    return str(Operation.process_json(settings, {"@op": "Concat", "args": {"inputs": inputs}}))


def test_a_sequence_valued_element_contributes_its_items(settings):
    each = {"@op": "ForEach", "args": {"select": ["a", "b", "c"], "operation": {"@op": "Current", "args": {}}}}
    assert _concat(settings, [each, "!"]) == "abc!"


def test_a_nested_array_is_the_same_flat_sequence(settings):
    assert _concat(settings, [["a", "b"], "c", [["d"]]]) == "abcd"


def test_an_empty_sequence_contributes_nothing(settings):
    nothing = {"@op": "ForEach", "args": {"select": [], "operation": {"@op": "Current", "args": {}}}}
    assert _concat(settings, ["a", nothing, "b"]) == "ab"


def test_unit_contributes_nothing(settings):
    unit = {"@op": "Variable", "args": {"name": "x", "value": "ignored"}}
    assert _concat(settings, ["a", unit, "b"]) == "ab"
