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
  would contradict the normative contract.
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
