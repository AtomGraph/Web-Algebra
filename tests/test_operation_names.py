"""formal-semantics.md §4 "Names": every operation's name is PascalCase, an
acronym (URI, UUID, SPARQL, XHTML) kept whole; upper case only for the HTTP
methods and the SPARQL query forms; an extension family's prefix before a
PascalCase name. Checked over every registered operation, so a new one cannot
drift from the rule."""

from __future__ import annotations

import re

import pytest

import web_algebra.operations
from web_algebra.main import list_operation_subclasses, register
from web_algebra.operation import Operation

# parametrized over the registry, so it is filled before collection
register(list_operation_subclasses(web_algebra.operations, Operation))

PROTOCOL = {"GET", "POST", "PUT", "PATCH", "DELETE", "SELECT", "CONSTRUCT", "DESCRIBE"}
PASCAL = r"(?:[A-Z][a-z0-9]+|URI|UUID|SPARQL|XHTML)+"
NAME = re.compile(rf"(?:ldh-)?{PASCAL}")


@pytest.mark.parametrize("name", sorted(Operation.registry))
def test_the_name_follows_the_rule(name):
    assert name in PROTOCOL or NAME.fullmatch(name), name


@pytest.mark.parametrize("function, name", [("STR", "Str"), ("CONCAT", "Concat"), ("REPLACE", "Replace"),
                                            ("ENCODE_FOR_URI", "EncodeForURI"), ("STRUUID", "StrUUID"),
                                            ("NOW", "Now"), ("URI", "URI")])
def test_a_function_is_named_in_pascal_case(function, name):
    assert name in Operation.registry, f"{function}() is the operation {name}"


def test_protocol_operations_keep_upper_case():
    assert PROTOCOL <= set(Operation.registry)
