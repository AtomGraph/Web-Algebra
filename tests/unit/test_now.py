"""Spec: formal-semantics.md §4.2 "NOW", §3.8 (τ).
Abstract: () → Literal
Python:   def execute(self) -> Literal
JSON:     (no arguments)

NOW is the current date and time, per SPARQL NOW() and XPath
fn:current-dateTime(): an xsd:dateTime literal with a timezone, the time at
which evaluation of the document began. Every NOW in one evaluation returns
the same value — across sequence elements and ForEach / Iterate iterations;
separate evaluations each have their own; outside any evaluation it is the
time of the call.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from rdflib import Literal
from rdflib.namespace import XSD

from web_algebra.operation import Operation

NOW = {"@op": "NOW", "args": {}}


def evaluate(settings, plan):
    return Operation.process_json(settings, plan)


def as_datetime(term) -> datetime:
    assert isinstance(term, Literal)
    assert term.datatype == XSD.dateTime
    value = term.toPython()
    assert isinstance(value, datetime), f"not a valid xsd:dateTime: {term!r}"
    return value


class TestNOWPure:
    def test_returns_a_datetime_literal(self, settings):
        as_datetime(Operation.get("NOW")(settings=settings).execute())

    def test_has_a_timezone(self, settings):
        value = as_datetime(Operation.get("NOW")(settings=settings).execute())
        assert value.tzinfo is not None and value.utcoffset() is not None

    def test_is_the_time_of_the_call(self, settings):
        before = datetime.now(timezone.utc)
        value = as_datetime(Operation.get("NOW")(settings=settings).execute())
        after = datetime.now(timezone.utc)
        assert before <= value <= after

    def test_outside_an_evaluation_each_call_has_its_own_time(self, settings):
        op = Operation.get("NOW")(settings=settings)
        first = as_datetime(op.execute())
        time.sleep(0.01)
        second = as_datetime(op.execute())
        assert second > first


class TestNOWJson:
    def test_empty_args(self, settings):
        before = datetime.now(timezone.utc)
        value = as_datetime(evaluate(settings, NOW))
        after = datetime.now(timezone.utc)
        assert before <= value <= after

    def test_has_a_timezone(self, settings):
        value = as_datetime(evaluate(settings, NOW))
        assert value.utcoffset() is not None


class TestNOWIsFixedForAnEvaluation:
    def test_successive_sequence_elements(self, settings):
        result = evaluate(settings, [NOW, NOW, NOW])
        assert len(result) == 3
        assert result[0] == result[1] == result[2]

    def test_across_time_spent_in_between(self, settings):
        # the elements between the two NOWs take measurable time
        slow = {"@op": "ForEach", "args": {"select": list(range(200)), "operation": {"@op": "STRUUID", "args": {}}}}
        result = evaluate(settings, [NOW, slow, NOW])
        assert result[0] == result[-1]

    def test_every_foreach_iteration(self, settings):
        result = evaluate(settings, {"@op": "ForEach", "args": {"select": [1, 2, 3, 4], "operation": NOW}})
        assert len(result) == 4
        assert len(set(result)) == 1

    def test_foreach_iterations_and_the_enclosing_sequence(self, settings):
        result = evaluate(settings, [NOW, {"@op": "ForEach", "args": {"select": [1, 2], "operation": [NOW, NOW]}}])
        assert len(result) == 5
        assert len(set(result)) == 1

    def test_every_iterate_iteration(self, settings):
        plan = {
            "@op": "Iterate",
            "args": {
                "params": {"s": "a"},
                "operation": NOW,
                "next-iteration": {
                    "s": {"@op": "Concat", "args": {"inputs": [{"@op": "Value", "args": {"name": "$s"}}, "a"]}}
                },
                "break": {"name": "s", "equals": "aaaa"},
            },
        }
        result = evaluate(settings, plan)
        assert len(result) == 3
        assert len(set(result)) == 1

    def test_through_a_variable(self, settings):
        plan = [
            {"@op": "Variable", "args": {"name": "t", "value": NOW}},
            {"@op": "ForEach", "args": {"select": list(range(50)), "operation": {"@op": "STRUUID", "args": {}}}},
            {"@op": "Value", "args": {"name": "$t"}},
            NOW,
        ]
        result = evaluate(settings, plan)
        assert result[-2] == result[-1]

    def test_lies_within_the_evaluation(self, settings):
        before = datetime.now(timezone.utc)
        result = evaluate(settings, [NOW, NOW])
        after = datetime.now(timezone.utc)
        assert before <= as_datetime(result[0]) <= after


class TestSeparateEvaluations:
    def test_each_has_its_own_time(self, settings):
        first = as_datetime(evaluate(settings, NOW))
        time.sleep(0.01)
        second = as_datetime(evaluate(settings, NOW))
        assert second > first

    def test_a_later_evaluation_is_not_earlier(self, settings):
        first = as_datetime(evaluate(settings, [NOW, NOW])[0])
        second = as_datetime(evaluate(settings, [NOW, NOW])[0])
        assert second >= first
