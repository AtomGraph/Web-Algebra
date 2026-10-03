from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class Focus:
    """The dynamic context of a ForEach iteration (formal-semantics.md §3.5):
    the current item, its 1-based position, and the iteration size — exactly
    XSLT's focus triple. Established only by ForEach; accessed by Current,
    Position, Last and focus-item Value lookups.

    `written` is the iteration's write gate (§3.6): every update made while
    this focus is current reports the URI it wrote, and the ForEach that
    established the focus refuses a URI that another of its iterations wrote.
    """

    item: Any
    position: int
    size: int
    written: Optional[Callable[[str], None]] = None


def report_write(context: Any, url: str) -> None:
    """Report a completed write to the iteration gate of the focus in
    `context`, if there is one; outside any ForEach writes are unconstrained."""
    if isinstance(context, Focus) and context.written is not None:
        context.written(url)
