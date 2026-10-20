"""Spec: formal-semantics.md §3.5, §4.1 Value.
- Value with an unprefixed name looks the name up in the focus item; a miss -
  including a variable that a Binding leaves unbound (an OPTIONAL that did not
  match) - raises ValueError.
"""

from __future__ import annotations

import pytest
from rdflib import URIRef

from web_algebra.operation import Operation

EX = "http://example.org/"
DATA = {"@id": EX + "s", EX + "p": "o"}
QUERY = f"SELECT ?s ?o WHERE {{ ?s <{EX}p> ?x OPTIONAL {{ ?s <{EX}q> ?o }} }}"


def _for_each(settings, name):
    return Operation.process_json(
        settings,
        {
            "@op": "ForEach",
            "args": {
                "select": {"@op": "SELECT", "args": {"graph": DATA, "query": QUERY}},
                "operation": {"@op": "Value", "args": {"name": name}},
            },
        },
    )


def test_a_bound_variable_is_read(settings):
    assert _for_each(settings, "s") == [URIRef(EX + "s")]


def test_an_unbound_variable_is_a_miss(settings):
    with pytest.raises(ValueError):
        _for_each(settings, "o")


def test_a_name_the_row_does_not_project_is_a_miss(settings):
    with pytest.raises(ValueError):
        _for_each(settings, "nope")
