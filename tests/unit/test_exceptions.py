"""The interpreter's exception taxonomy (src/web_algebra/exceptions.py).

Each interpreter-level error is a `WebAlgebraError` *and* the built-in the
spec's error table (formal-semantics.md §3.7) mandates — so callers may
`except WebAlgebraError` while the normative built-in contract still holds.
"""

from __future__ import annotations

import pytest

from web_algebra.exceptions import (
    InvalidFormError,
    NoFocusError,
    UnknownOperationError,
    VariableNotFoundError,
    WebAlgebraError,
)
from web_algebra.operation import Operation


class TestTaxonomyIsBackwardCompatible:
    def test_unknown_operation_is_web_algebra_error_and_value_error(self, settings):
        # §3.7: unknown `@op` → ValueError
        with pytest.raises(UnknownOperationError) as exc:
            Operation.process_json(settings, {"@op": "NoSuchOperation"})
        assert isinstance(exc.value, WebAlgebraError)
        assert isinstance(exc.value, ValueError)

    def test_null_form_is_web_algebra_error_and_type_error(self, settings):
        # §3.7: null form → TypeError
        with pytest.raises(InvalidFormError) as exc:
            Operation.process_json(settings, None)
        assert isinstance(exc.value, WebAlgebraError)
        assert isinstance(exc.value, TypeError)

    def test_missing_variable_is_web_algebra_error_and_value_error(self, settings):
        # §3.7: unknown variable in `$name` lookup → ValueError
        op = Operation.get("Value")(settings=settings)
        with pytest.raises(VariableNotFoundError) as exc:
            op.execute("$missing", {}, [])
        assert isinstance(exc.value, WebAlgebraError)
        assert isinstance(exc.value, ValueError)

    def test_no_focus_is_web_algebra_error_and_value_error(self, settings):
        # §3.5/§3.7: Current outside an iteration focus → ValueError
        op = Operation.get("Current")(settings=settings)
        with pytest.raises(NoFocusError) as exc:
            op.execute_json({})
        assert isinstance(exc.value, WebAlgebraError)
        assert isinstance(exc.value, ValueError)

    def test_web_algebra_error_catches_the_family(self, settings):
        # a caller can classify "ill-formed document" with one except clause
        with pytest.raises(WebAlgebraError):
            Operation.process_json(settings, {"@op": "NoSuchOperation"})
