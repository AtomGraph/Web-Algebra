"""Spec: formal-semantics.md §4.1 "ForEach — evaluate an operation once per
item of a sequence or per row of a SPARQL result", §3.8 (FOREACH), and the
update rule of §3.6.
Abstract: (Sequence α + Result) × Operation⟨quoted⟩ → Sequence β
- Interpreter-level special form: execute_json only, no pure layer (§4.1).
- Iterates a Sequence item-by-item, a Result row-by-row in result order.
- Each iteration runs in a fresh variable scope under the focus (item i, i, n).
- An array `operation` evaluates as a sequence form within the iteration's
  scope: the iteration's value is the concatenation of its element values.
- The result is the concatenation of the iteration values in item order
  (§3.1): a sequence-valued iteration contributes its items, a Unit-valued
  one nothing; a Result is one item, never dissolved into rows.
- §3.6: two iterations of one ForEach updating the same URI (the URI the
  write reports, §4.4) raise ValueError, when the second write is reported;
  one iteration may write a URI repeatedly; an update inside a nested ForEach
  counts for every enclosing iteration.
"""

from __future__ import annotations

import pytest
from rdflib import Literal
from rdflib.namespace import XSD
from rdflib.query import Result

from tests.http_stub import StubResponse, default_handler
from web_algebra.json_result import JSONResult
from web_algebra.operation import Operation


def _str_current() -> dict:
    return {"@op": "Str", "args": {"input": {"@op": "Current", "args": {}}}}


def _table(*values: str) -> JSONResult:
    return JSONResult.from_json(
        {
            "head": {"vars": ["x"]},
            "results": {
                "bindings": [{"x": {"type": "literal", "value": v}} for v in values]
            },
        }
    )


class TestForEachJson:
    def test_empty_sequence(self, settings):
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json({"select": [], "operation": _str_current()})
        assert result == []

    def test_length_matches_input(self, settings):
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {"select": ["a", "b", "c"], "operation": _str_current()}
        )
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(item, Literal) for item in result)
        assert [str(item) for item in result] == ["a", "b", "c"]

    def test_non_iterable_select_raises(self, settings):
        # §4.1: any other `select` value raises TypeError
        op = Operation.get("ForEach")(settings=settings)
        with pytest.raises(TypeError):
            op.execute_json(
                {
                    "select": "not-a-list-or-result",
                    "operation": {"@op": "Current", "args": {}},
                }
            )

    def test_unit_valued_iterations_contribute_nothing(self, settings):
        # §4.1: a Unit-valued iteration (None) contributes nothing — Variable
        # returns Unit, so an all-Variable operation yields the empty sequence.
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {
                "select": ["a", "b"],
                "operation": {
                    "@op": "Variable",
                    "args": {"name": "x", "value": {"@op": "Current", "args": {}}},
                },
            }
        )
        assert result == []

    def test_sequence_valued_iterations_contribute_their_items(self, settings):
        # §4.1/§3.1: the result is the concatenation of the iteration values —
        # a nested ForEach's sequence contributes its items, flat.
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {
                "select": ["a", "b"],
                "operation": {
                    "@op": "ForEach",
                    "args": {"select": ["x", "y"], "operation": _str_current()},
                },
            }
        )
        # §4.2: Str returns simple literals
        assert result == [Literal("x"), Literal("y"), Literal("x"), Literal("y")]

    def test_operation_array_yields_concatenation_of_its_values(self, settings):
        # §4.1: an array operation's value is the concatenation of its element
        # values (§3.2) — a Variable leaves no item, every other element does.
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {
                "select": ["a", "b"],
                "operation": [
                    {
                        "@op": "Variable",
                        "args": {"name": "x", "value": {"@op": "Current", "args": {}}},
                    },
                    {"@op": "Str", "args": {"input": {"@op": "Value", "args": {"name": "$x"}}}},
                    "!",
                ],
            }
        )
        bang = Literal("!", datatype=XSD.string)
        assert result == [Literal("a"), bang, Literal("b"), bang]

    def test_operation_array_of_units_contributes_nothing(self, settings):
        # §3.2: a Variable leaves no item, so an array of Variables is ()
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {
                "select": ["a"],
                "operation": [
                    {"@op": "Variable", "args": {"name": "x", "value": "v"}},
                    {"@op": "Variable", "args": {"name": "y", "value": "w"}},
                ],
            }
        )
        assert result == []

    def test_result_valued_iterations_are_not_dissolved(self, settings):
        # §3.1: a Result is a value in its own right; concatenation never
        # dissolves it into its rows
        op = Operation.get("ForEach")(settings=settings)
        t1, t2 = _table("a", "b"), _table("c")
        result = op.execute_json(
            {"select": [t1, t2], "operation": {"@op": "Current", "args": {}}}
        )
        assert len(result) == 2
        assert all(isinstance(item, Result) for item in result)
        assert [len(list(item)) for item in result] == [2, 1]

    def test_iteration_scope_does_not_leak(self, settings):
        # §3.4: each iteration runs in a fresh scope — bindings made inside
        # do not survive the ForEach.
        op = Operation.get("ForEach")(settings=settings)
        stack = [{}]
        op.execute_json(
            {
                "select": ["a"],
                "operation": [
                    {"@op": "Variable", "args": {"name": "x", "value": "v"}},
                    {"@op": "Current", "args": {}},
                ],
            },
            stack,
        )
        assert stack == [{}]

    def test_result_rows_iterate_in_result_order(self, settings):
        # §4.1: a Result iterates row-by-row in result order
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {
                "select": _table("a", "b", "c"),
                "operation": {"@op": "Value", "args": {"name": "x"}},
            }
        )
        assert [str(v) for v in result] == ["a", "b", "c"]


# --- §3.6: the xsl:result-document rule for updates inside a ForEach ---------


def _put(url: str) -> dict:
    return {
        "@op": "PUT",
        "args": {
            "url": {"@id": url},
            "data": {"@id": url, "http://example.org/p": "v"},
        },
    }


def _post(url: str) -> dict:
    return {
        "@op": "POST",
        "args": {
            "url": {"@id": url},
            "data": {"@id": url, "http://example.org/p": "v"},
        },
    }


class TestForEachSameTargetRule:
    def test_two_iterations_updating_the_same_uri_raise(self, settings, http_stub):
        # §3.6/§3.7: two iterations of one ForEach updating the same URI →
        # ValueError
        op = Operation.get("ForEach")(settings=settings)
        with pytest.raises(ValueError):
            op.execute_json(
                {"select": ["a", "b"], "operation": _put("http://example.org/doc")}
            )

    def test_second_write_has_been_performed_when_raised(self, settings, http_stub):
        # §3.6: the error is raised when the second write is reported, so
        # that write has been performed
        op = Operation.get("ForEach")(settings=settings)
        with pytest.raises(ValueError):
            op.execute_json(
                {"select": ["a", "b"], "operation": _put("http://example.org/doc")}
            )
        assert len(http_stub.with_method("PUT")) == 2

    def test_iterations_updating_distinct_uris_are_allowed(self, settings, http_stub):
        # §3.6: only the same URI twice is an error; each write's Result is
        # one item of the concatenation (§3.1)
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {
                "select": ["a", "b"],
                "operation": {
                    "@op": "PUT",
                    "args": {
                        "url": {
                            "@id": {
                                "@op": "Concat",
                                "args": {
                                    "inputs": [
                                        "http://example.org/",
                                        {"@op": "Str", "args": {"input": {"@op": "Current", "args": {}}}},
                                    ]
                                },
                            }
                        },
                        "data": {"@id": "http://example.org/x", "http://example.org/p": "v"},
                    },
                },
            }
        )
        assert len(result) == 2
        assert all(isinstance(item, Result) for item in result)
        assert len(http_stub.with_method("PUT")) == 2

    def test_one_iteration_may_write_the_same_uri_twice(self, settings, http_stub):
        # §3.6: within one iteration the sequence form orders the writes, so
        # a document may be created and then added to
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {
                "select": ["a"],
                "operation": [
                    _put("http://example.org/doc"),
                    _post("http://example.org/doc"),
                ],
            }
        )
        assert len(result) == 2
        assert http_stub.methods().count("PUT") == 1
        assert http_stub.methods().count("POST") == 1

    def test_compared_uri_is_the_reported_one_distinct_locations(
        self, settings, http_stub
    ):
        # §3.6: the URI compared is the one the write reports (§4.4 `url`) —
        # POSTs to one container that each create a child (distinct
        # Location) do not collide
        counter = {"n": 0}

        def handler(request):
            if request.get_method() == "POST":
                counter["n"] += 1
                return StubResponse(
                    201, {"Location": f"http://example.org/container/child{counter['n']}"}
                )
            return default_handler(request)

        http_stub.handler = handler
        op = Operation.get("ForEach")(settings=settings)
        result = op.execute_json(
            {"select": ["a", "b"], "operation": _post("http://example.org/container/")}
        )
        assert len(result) == 2

    def test_compared_uri_is_the_reported_one_same_location(self, settings, http_stub):
        # §3.6: writes to different request URIs that report the same URI
        # (the response Location, §4.4) collide
        def handler(request):
            if request.get_method() == "POST":
                return StubResponse(201, {"Location": "http://example.org/same"})
            return default_handler(request)

        http_stub.handler = handler
        op = Operation.get("ForEach")(settings=settings)
        with pytest.raises(ValueError):
            op.execute_json(
                {
                    "select": ["a", "b"],
                    "operation": {
                        "@op": "POST",
                        "args": {
                            "url": {
                                "@id": {
                                    "@op": "Concat",
                                    "args": {
                                        "inputs": [
                                            "http://example.org/c/",
                                            {"@op": "Str", "args": {"input": {"@op": "Current", "args": {}}}},
                                        ]
                                    },
                                }
                            },
                            "data": {"@id": "http://example.org/x", "http://example.org/p": "v"},
                        },
                    },
                }
            )

    def test_nested_for_each_write_counts_for_enclosing_iteration(
        self, settings, http_stub
    ):
        # §3.6: an update made inside a nested ForEach counts for every
        # enclosing iteration it runs in — each outer iteration's inner
        # ForEach writes the same URI once, so the outer ForEach collides
        op = Operation.get("ForEach")(settings=settings)
        with pytest.raises(ValueError):
            op.execute_json(
                {
                    "select": ["a", "b"],
                    "operation": {
                        "@op": "ForEach",
                        "args": {
                            "select": ["x"],
                            "operation": _put("http://example.org/doc"),
                        },
                    },
                }
            )

    def test_separate_for_eaches_may_write_the_same_uri(self, settings, http_stub):
        # §3.6: the rule is per ForEach — two ForEach steps of one sequence,
        # each writing the URI once, are ordered by the sequence form
        program = [
            {"@op": "ForEach", "args": {"select": ["a"], "operation": _put("http://example.org/doc")}},
            {"@op": "ForEach", "args": {"select": ["b"], "operation": _put("http://example.org/doc")}},
        ]
        result = Operation.process_json(settings, program)
        assert len(result) == 2
        assert len(http_stub.with_method("PUT")) == 2

    def test_writes_outside_any_for_each_are_unconstrained(self, settings, http_stub):
        # §3.6: the rule concerns iterations of a ForEach; a plain sequence
        # may write one URI twice
        program = [_put("http://example.org/doc"), _put("http://example.org/doc")]
        result = Operation.process_json(settings, program)
        assert len(result) == 2
