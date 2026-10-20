"""Static checks and the summary a client shows before approving a document.

Two jobs, one walk of the same tree:

* **validation** — does every `@op` name an operation that exists, and does it
  carry the arguments that operation declares required? This is what the repair
  loop feeds back to the model, and what `POST /executions` re-runs so that what
  was displayed is what runs.
* **summarisation** — one row per top-level form saying what it does (read,
  write, destructive), which nested operation does the damage, and what it
  addresses. This is what the chat UI renders as pills. The client never parses
  the DSL; it reads these rows.

Neither job executes anything, so neither can be fooled into a request. They
know only the operation registry and the shape of the document.
"""

from typing import Any, List, Optional

from pydantic import BaseModel

from web_algebra.operation import Operation, OperationKind

# Argument names that address something on the network, in the order a summary
# prefers them. `endpoint` first because a query op's endpoint is the thing a
# reader wants to see (which origin is being asked); `url` and the document
# arguments of the LinkedDataHub operations follow.
TARGET_ARGS = ("endpoint", "url", "document", "parent", "target")


class Diagnostic(BaseModel):
    """One reason a document is not executable."""

    path: str  # JSON Pointer into the submitted document, e.g. /0/args/select
    op: Optional[str] = None  # the `@op` name at that path, when there is one
    message: str


class OperationSummary(BaseModel):
    """One row of the plan summary — a top-level form, described."""

    index: int
    op: str  # the top-level operation's name
    via: Optional[str] = None  # the nested operation that does the writing, if any
    kind: OperationKind
    target: Optional[str] = None


class ValidationResult(BaseModel):
    valid: bool
    diagnostics: List[Diagnostic] = []


def as_forms(document: Any) -> List[Any]:
    """The document's top-level forms.

    A plan is a sequence of operations, and a single operation is a plan of one
    — `main.py` has always accepted both, and the LLM emits both.
    """
    if isinstance(document, list):
        return document
    return [document]


# --- validation --------------------------------------------------------------


def validate(document: Any) -> ValidationResult:
    """Check every `@op` in `document` against the operation registry."""
    diagnostics: List[Diagnostic] = []
    for index, form in enumerate(as_forms(document)):
        _validate_node(form, f"/{index}", diagnostics)
    return ValidationResult(valid=not diagnostics, diagnostics=diagnostics)


def _validate_node(node: Any, path: str, out: List[Diagnostic]) -> None:
    if isinstance(node, dict):
        if "@op" in node:
            _validate_operation(node, path, out)
            return
        # every other dict — a JSON-LD body, a binding object, a bare `@id`
        # reference — is data that may still embed operations in its values
        for key, value in node.items():
            _validate_node(value, f"{path}/{_escape(key)}", out)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _validate_node(item, f"{path}/{index}", out)


def _validate_operation(node: dict, path: str, out: List[Diagnostic]) -> None:
    name = node["@op"]
    if not isinstance(name, str):
        out.append(Diagnostic(path=path, message="@op must be an operation name"))
        return

    operation_cls = Operation.get(name)
    if operation_cls is None:
        out.append(
            Diagnostic(
                path=path,
                op=name,
                message=f"Unknown operation '{name}'. Use one of the documented operations.",
            )
        )
        return

    arguments = node.get("args", {})
    if not isinstance(arguments, dict):
        out.append(
            Diagnostic(path=f"{path}/args", op=name, message="args must be an object")
        )
        return

    for missing in _missing_arguments(operation_cls, arguments):
        out.append(
            Diagnostic(
                path=f"{path}/args",
                op=name,
                message=f"Missing required argument '{missing}' of {name}",
            )
        )

    for key, value in arguments.items():
        _validate_node(value, f"{path}/args/{_escape(key)}", out)


def _missing_arguments(operation_cls, arguments: dict) -> List[str]:
    """Required argument names the form does not supply.

    Reads the operation's own `inputSchema()` rather than a table kept here, so
    a new operation is validated the day it is written. A schema that declares
    no `required` list constrains nothing, which is what an operation with only
    optional arguments means.
    """
    try:
        schema = operation_cls.inputSchema()
    except Exception:  # an operation whose schema cannot be built constrains nothing
        return []
    if not isinstance(schema, dict):
        return []
    missing = [name for name in schema.get("required", []) if name not in arguments]
    # `oneOf` alternatives of `required` lists (SELECT's `endpoint` or `graph`):
    # missing when no alternative is supplied, named as the alternatives
    alternatives = [
        branch.get("required", [])
        for branch in schema.get("oneOf", [])
        if isinstance(branch, dict)
    ]
    if alternatives and not any(
        all(name in arguments for name in names) for names in alternatives
    ):
        missing.append(" or ".join("/".join(names) for names in alternatives))
    return missing


def _escape(key: str) -> str:
    """JSON Pointer escaping (RFC 6901): `~` then `/`."""
    return key.replace("~", "~0").replace("/", "~1")


# --- summarisation -----------------------------------------------------------


def summarize(document: Any) -> List[OperationSummary]:
    """One summary row per top-level form."""
    return [
        _summarize_form(form, index)
        for index, form in enumerate(as_forms(document))
    ]


def _summarize_form(form: Any, index: int) -> OperationSummary:
    name = form.get("@op") if isinstance(form, dict) else None
    own_kind = _kind_of(name)

    worst_name, worst_kind = _worst_nested(form)
    # A control form (ForEach, Iterate) is only as dangerous as its body, and the
    # body is the operation worth naming: "ForEach ▸ PATCH" says more than either
    # half alone. When the top-level operation is itself the worst thing in the
    # form there is nothing to name beside it.
    via = worst_name if worst_kind > own_kind else None
    kind = worst_kind if worst_kind > own_kind else own_kind

    return OperationSummary(
        index=index,
        op=name or "?",
        via=via,
        kind=kind,
        target=_target_of(form),
    )


def _kind_of(name: Optional[str]) -> OperationKind:
    operation_cls = Operation.get(name) if name else None
    return operation_cls.kind if operation_cls else OperationKind.READ


def _worst_nested(node: Any, depth: int = 0) -> tuple[Optional[str], OperationKind]:
    """The name and kind of the most dangerous operation anywhere in `node`.

    `depth` 0 is the form itself, which is compared separately, so it is walked
    for its arguments but does not nominate itself.
    """
    worst_name: Optional[str] = None
    worst_kind = OperationKind.READ

    if isinstance(node, dict):
        name = node.get("@op")
        if depth > 0 and isinstance(name, str):
            kind = _kind_of(name)
            if kind > worst_kind:
                worst_name, worst_kind = name, kind
        children = node.get("args", {}).values() if "@op" in node else node.values()
        for child in children:
            name, kind = _worst_nested(child, depth + 1)
            if kind > worst_kind:
                worst_name, worst_kind = name, kind
    elif isinstance(node, list):
        for item in node:
            name, kind = _worst_nested(item, depth + 1)
            if kind > worst_kind:
                worst_name, worst_kind = name, kind

    return worst_name, worst_kind


def _target_of(node: Any) -> Optional[str]:
    """The first network address the form names, outermost first.

    Only literal addresses are reported: one computed by an operation (a URL
    resolved per `ForEach` row) is not knowable without executing, and a summary
    that guessed would be worse than one that says nothing. The execution's
    `affected_documents` reports those, after the fact and from the requests
    actually sent.
    """
    if isinstance(node, dict):
        if "@op" in node:
            arguments = node.get("args", {})
            if isinstance(arguments, dict):
                for name in TARGET_ARGS:
                    uri = _as_uri(arguments.get(name))
                    if uri:
                        return uri
                for value in arguments.values():
                    nested = _target_of(value)
                    if nested:
                        return nested
            return None
        for value in node.values():
            nested = _target_of(value)
            if nested:
                return nested
    elif isinstance(node, list):
        for item in node:
            nested = _target_of(item)
            if nested:
                return nested
    return None


def _as_uri(value: Any) -> Optional[str]:
    """A URI the document states outright, in either form it can take."""
    if isinstance(value, str) and "://" in value:
        return value
    if isinstance(value, dict) and set(value.keys()) == {"@id"}:
        identifier = value["@id"]
        if isinstance(identifier, str) and "://" in identifier:
            return identifier
    return None
