import logging
from typing import Optional

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import XSD
from rdflib.query import Result

from web_algebra.client_operation import ClientOperation
from web_algebra.exceptions import WriteRefusedError
from web_algebra.json_result import JSONResult

PRECONDITION_FAILED = 412


def create(op: ClientOperation, url: URIRef, graph: Graph, if_absent: Optional[Literal]) -> Result:
    """Write `graph` as a new document at `url`, never replacing one.

    The `PUT` carries `If-None-Match: *` (formal-semantics.md Appendix A), as
    LinkedDataHub's CLI create commands and its client's create forms send it,
    so a server refuses it `412` where a document already exists and leaves
    that document as it is. That refusal is the operation's error, unless
    `if_absent` is true: then the existing document is the result, as an
    existing directory is for `mkdir -p`. Nothing was written, so it is not
    reported to an enclosing `ForEach` as a write (§3.6).
    """
    try:
        response = op.client.create(str(url), graph)
    except WriteRefusedError as e:
        if e.status != PRECONDITION_FAILED:
            raise
        if if_absent is None or not if_absent.toPython():
            raise WriteRefusedError(
                e.method, e.url, e.status,
                "a document already exists at this URI and was left as it is; "
                "pass if_absent to accept one that does",
            ) from None
        logging.info("A document already exists at <%s>; left as it is", url)
        return JSONResult(
            vars=["status", "url"],
            bindings=[{"status": Literal(e.status, datatype=XSD.integer), "url": url}],
        )

    logging.info("PUT operation status: %s", response.status)
    return op.written_response(response)


def if_absent_flag(value: Optional[Literal], op_name: str) -> Optional[Literal]:
    """`if_absent` as an operation takes it: absent, or an xsd:boolean Literal."""
    if value is not None and not (isinstance(value, Literal) and value.datatype == XSD.boolean):
        raise TypeError(f"{op_name} expects if_absent to be an xsd:boolean Literal, got {value!r}")
    return value
