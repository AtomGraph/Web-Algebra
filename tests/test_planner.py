"""The interactive planner's reading of a model reply (web_algebra.main.parse_plan):
the plan is the reply's JSON, an object or an array of steps, whether or not the
model fenced it as a Markdown code block - the planner asks for no JSON mode,
which admits only an object."""

from __future__ import annotations

import pytest

from web_algebra.main import parse_plan

STEP = {"@op": "Str", "args": {"input": "a"}}


@pytest.mark.parametrize(
    "reply",
    [
        '{"@op": "Str", "args": {"input": "a"}}',
        '```json\n{"@op": "Str", "args": {"input": "a"}}\n```',
        '```\n{"@op": "Str", "args": {"input": "a"}}\n```',
        '  \n```json\n{"@op": "Str", "args": {"input": "a"}}\n```\n',
    ],
    ids=["bare", "json-fence", "plain-fence", "padded"],
)
def test_an_object_plan(reply):
    assert parse_plan(reply) == STEP


@pytest.mark.parametrize(
    "reply",
    ['[{"@op": "Str", "args": {"input": "a"}}]', '```json\n[\n  {"@op": "Str", "args": {"input": "a"}}\n]\n```'],
    ids=["bare", "fenced"],
)
def test_an_array_of_steps_is_a_plan(reply):
    assert parse_plan(reply) == [STEP]


@pytest.mark.parametrize("reply", ['"a"', "1", "null"])
def test_a_scalar_is_not_a_plan(reply):
    with pytest.raises(ValueError):
        parse_plan(reply)


def test_prose_around_the_fence_is_not_stripped():
    with pytest.raises(ValueError):
        parse_plan('Here is the plan:\n```json\n{"@op": "Str", "args": {"input": "a"}}\n```')
