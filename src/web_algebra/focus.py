from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Focus:
    """The dynamic context of a ForEach iteration (formal-semantics.md §3.5):
    the current item, its 1-based position, and the iteration size — exactly
    XSLT's focus triple. Established only by ForEach; accessed by Current,
    Position, Last and focus-item Value lookups.
    """

    item: Any
    position: int
    size: int
