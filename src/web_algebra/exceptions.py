"""Web Algebra exception hierarchy.

`WebAlgebraError` is the base for every failure the interpreter raises about a
Web Algebra *document* — an unknown operation, an unresolved variable, a
missing iteration focus, an ill-formed value. Each subclass also inherits the
built-in exception that the specification's error table
(`formal-semantics.md` §3.7) mandates, so the normative contract — and the
existing `pytest.raises(TypeError | ValueError | KeyError)` assertions — keep
holding, while callers gain `except WebAlgebraError` to tell an ill-formed
document apart from an unrelated bug.

Scope: these classes cover the **interpreter / composition layer** (dispatch,
evaluation, variable and focus resolution). Individual operations validate
their own argument *types* with plain `TypeError` / `ValueError` per the
spec's Strict Type Checking property; those are not reclassified here.

Two deliberate omissions:

- There is no wrapper for HTTP/SPARQL transport failures. Spec §3.7 pins them
  to `urllib.error.HTTPError` / `URLError` propagating **unwrapped**; wrapping
  would contradict the normative contract. A *write* answered outside 2xx is
  not a transport failure but a refused write (§4.4), raised as
  `WriteRefusedError`.
- Per-operation argument type errors stay built-in `TypeError` for the same
  reason (§3.7 names them `TypeError`), and to avoid churning ~170 leaf
  validation sites whose meaning is already unambiguous.
"""


class WebAlgebraError(Exception):
    """Base for errors the Web Algebra interpreter raises about a document."""


class UnknownOperationError(WebAlgebraError, ValueError):
    """An `@op` names an operation that is not registered (spec §3.7)."""


class InvalidFormError(WebAlgebraError, TypeError):
    """A JSON value is not a valid Web Algebra form — e.g. `null` (spec §2.2, §3.7)."""


class VariableNotFoundError(WebAlgebraError, ValueError):
    """A `$name` variable lookup or a focus-item member lookup found nothing (spec §3.7)."""


class NoFocusError(WebAlgebraError, ValueError):
    """An operation that requires an iteration focus ran outside one (spec §3.5)."""


class SameTargetError(WebAlgebraError, ValueError):
    """Two iterations of one `ForEach` updated the same URI (spec §3.6) — the
    algebra's XTDE1490."""


class WriteRefusedError(ValueError):
    """A write was answered outside 2xx (spec §4.4) — as an
    `xsl:result-document` that cannot be written. Carries the status and the
    server's reason. Not a `WebAlgebraError`: the document is well-formed, the
    world refused it."""

    def __init__(self, method: str, url: str, status: int, reason: str):
        self.method = method
        self.url = url
        self.status = status
        self.reason = reason
        super().__init__(f"{method} {url} answered {status}: {reason}")
