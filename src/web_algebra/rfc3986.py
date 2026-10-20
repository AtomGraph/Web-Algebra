"""RFC 3986 §5.2 reference resolution, for a base of any scheme.

`urllib.parse.urljoin` resolves only the schemes on its own list: for any
other base (`urn:`, `tag:`, `mailto:`, a custom scheme) it returns the
reference unchanged. This is the RFC's algorithm, step for step.
"""

import re
from typing import NamedTuple, Optional

# RFC 3986 Appendix B
_URI = re.compile(r"^(?:([^:/?#]+):)?(?://([^/?#]*))?([^?#]*)(?:\?([^#]*))?(?:#(.*))?$", re.S)


class _Parts(NamedTuple):
    scheme: Optional[str]
    authority: Optional[str]
    path: str
    query: Optional[str]
    fragment: Optional[str]


def _split(uri: str) -> _Parts:
    """The five components; an undefined one is None, as distinct from empty."""
    m = _URI.match(uri)
    return _Parts(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))


def remove_dot_segments(path: str) -> str:
    """RFC 3986 §5.2.4."""
    output = []
    while path:
        if path.startswith("../"):
            path = path[3:]
        elif path.startswith("./"):
            path = path[2:]
        elif path.startswith("/./"):
            path = path[2:]
        elif path == "/.":
            path = "/"
        elif path.startswith("/../"):
            path = path[3:]
            if output:
                output.pop()
        elif path == "/..":
            path = "/"
            if output:
                output.pop()
        elif path in (".", ".."):
            path = ""
        else:
            start = 1 if path.startswith("/") else 0
            end = path.find("/", start)
            if end == -1:
                end = len(path)
            output.append(path[:end])
            path = path[end:]
    return "".join(output)


def _merge(base: _Parts, path: str) -> str:
    """RFC 3986 §5.2.3."""
    if base.authority is not None and base.path == "":
        return "/" + path
    return base.path[: base.path.rfind("/") + 1] + path


def resolve(base: str, reference: str) -> str:
    """Resolve `reference` against `base` (RFC 3986 §5.2.2, recomposed per §5.3)."""
    b, r = _split(base), _split(reference)
    if r.scheme is not None:
        scheme, authority, path, query = r.scheme, r.authority, remove_dot_segments(r.path), r.query
    else:
        scheme = b.scheme
        if r.authority is not None:
            authority, path, query = r.authority, remove_dot_segments(r.path), r.query
        else:
            authority = b.authority
            if r.path == "":
                path = b.path
                query = r.query if r.query is not None else b.query
            else:
                path = remove_dot_segments(r.path if r.path.startswith("/") else _merge(b, r.path))
                query = r.query

    result = ""
    if scheme is not None:
        result += scheme + ":"
    if authority is not None:
        result += "//" + authority
    result += path
    if query is not None:
        result += "?" + query
    if r.fragment is not None:
        result += "#" + r.fragment
    return result
