from typing import Optional

from rdflib import Literal


def fragment_id(fragment: Optional[Literal]) -> Optional[str]:
    """The fragment identifier a `fragment` argument names, without its `#`.

    A `fragment` names the resource an operation creates in the document,
    `url#fragment`, and is given with or without the leading `#`
    (formal-semantics.md Appendix A). None or empty means no fragment: the
    resource is a blank node.
    """
    if not fragment:
        return None
    return str(fragment).removeprefix("#") or None
