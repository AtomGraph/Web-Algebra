"""OperationKind orders by blast radius, not by its string values.

OperationKind is implementation, not language (formal-semantics.md does not
define it), so this test sits outside tests/unit/ and may name the module.
"""

import pytest

from web_algebra.operation import OperationKind

READ, WRITE, DESTRUCTIVE = OperationKind.READ, OperationKind.WRITE, OperationKind.DESTRUCTIVE


@pytest.mark.parametrize(
    "lower, higher", [(READ, WRITE), (WRITE, DESTRUCTIVE), (READ, DESTRUCTIVE)]
)
def test_every_comparison_orders_by_blast_radius(lower, higher):
    assert lower < higher
    assert lower <= higher
    assert higher > lower
    assert higher >= lower
    assert not higher < lower
    assert not lower > higher


def test_a_kind_is_neither_above_nor_below_itself():
    for kind in OperationKind:
        assert kind <= kind
        assert kind >= kind
        assert not kind < kind
        assert not kind > kind


def test_the_worst_of_several_kinds_is_the_most_destructive():
    assert max(READ, DESTRUCTIVE, WRITE) is DESTRUCTIVE
    assert min(WRITE, DESTRUCTIVE, READ) is READ
    assert sorted([DESTRUCTIVE, READ, WRITE]) == [READ, WRITE, DESTRUCTIVE]
