from typing import Any, Callable, ClassVar, List, Optional
import logging

from web_algebra.operation import Operation


class Iterate(Operation):
    """
    Stateful iteration with parameter passing between iterations, inspired by
    XSLT 3.0's xsl:iterate. Shared with the REST-VKG (Java/XML) Web Algebra.
    """

    # Normative iteration cap (formal-semantics.md §4.1): reaching it stops
    # the loop — it is not an error — and keeps the algebra terminating.
    MAX_ITERATIONS: ClassVar[int] = 1000

    @classmethod
    def description(cls) -> str:
        return """Stateful iteration with parameter passing between iterations, inspired by XSLT 3.0's xsl:iterate.

        `params` are evaluated once and bound as variables (read via $name).
        Each iteration evaluates `operation`; afterwards the `next-iteration`
        members are evaluated in the iteration's environment and rebind the
        parameters. `break` compares a loop variable against a value and
        stops the loop when it matches. Without `next-iteration`, exactly one
        iteration runs. Returns the sequence of iteration values. Useful for
        cursor- or URL-driven pagination."""

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "params": {
                    "type": "object",
                    "description": "Initial parameters: name → form, evaluated once in the enclosing environment and bound as loop variables",
                },
                "operation": {
                    "description": "Operation(s) evaluated each iteration (quoted)"
                },
                "next-iteration": {
                    "type": "object",
                    "description": "name → form, evaluated after each iteration in the iteration's environment to rebind the loop parameters (quoted)",
                },
                "break": {
                    "type": "object",
                    "description": "Loop exit test: {name, equals} or {name, not-equals}; the named loop variable's lexical form is compared with the value",
                },
            },
            "required": ["operation"],
        }

    def execute(self, *args) -> Any:
        raise NotImplementedError(
            "Iterate is an interpreter-level special form; use execute_json"
        )

    def execute_json(self, arguments: dict, variable_stack: list = None) -> List[Any]:
        """JSON execution: run the parameterized loop (formal-semantics.md
        §3.8 (ITERATE))."""
        if variable_stack is None:
            variable_stack = []

        params_arg = arguments.get("params", {})
        if not isinstance(params_arg, dict):
            raise TypeError(
                f"Iterate expects 'params' to be an object of name → form, got {type(params_arg)}"
            )
        operation = arguments["operation"]  # quoted
        next_arg = arguments.get("next-iteration")  # quoted
        if next_arg is not None and not isinstance(next_arg, dict):
            raise TypeError(
                f"Iterate expects 'next-iteration' to be an object of name → form, got {type(next_arg)}"
            )
        break_test = self._parse_break(arguments.get("break"), variable_stack)

        # params: eager, evaluated in the enclosing environment
        params = {
            name: Operation.process_json(
                self.settings, form, self.context, variable_stack
            )
            for name, form in params_arg.items()
        }

        results: List[Any] = []
        # The loop scope holds the iteration parameters across iterations.
        variable_stack.append(dict(params))
        try:
            iteration = 0
            while iteration < self.MAX_ITERATIONS:
                iteration += 1
                logging.info("Iterate: iteration %d", iteration)

                # Fresh body scope per iteration (§3.4); the enclosing focus,
                # if any, remains visible (Iterate establishes none).
                variable_stack.append({})
                try:
                    value = self._evaluate_body(operation, variable_stack)
                    if value is not None:
                        results.append(value)

                    if next_arg is None:
                        # No next-iteration: exactly one iteration.
                        break

                    # next-iteration members: evaluated in the iteration's
                    # environment (loop params + body bindings), in document
                    # order, each visible to the ones after it.
                    new_params = {}
                    for name, form in next_arg.items():
                        new_value = Operation.process_json(
                            self.settings, form, self.context, variable_stack
                        )
                        new_params[name] = new_value
                        self.set_variable(name, new_value, variable_stack)
                finally:
                    variable_stack.pop()

                # Rebind the loop parameters for the next iteration.
                variable_stack[-1].update(new_params)

                if break_test is not None and break_test():
                    logging.info("Iterate: break condition met after %d iterations", iteration)
                    break
            else:
                logging.warning(
                    "Iterate: reached the iteration cap (%d)", self.MAX_ITERATIONS
                )
        finally:
            variable_stack.pop()

        return results

    def _evaluate_body(self, operation: Any, variable_stack: list) -> Any:
        """Evaluate the quoted operation (form or array of forms); array
        operands yield the last non-Unit value, as in ForEach."""
        if isinstance(operation, list):
            last_result = None
            for op in operation:
                result = Operation.process_json(
                    self.settings, op, self.context, variable_stack
                )
                if result is not None:
                    last_result = result
            return last_result
        return Operation.process_json(
            self.settings, operation, self.context, variable_stack
        )

    def _parse_break(
        self, break_arg: Any, variable_stack: list
    ) -> Optional[Callable[[], bool]]:
        """Build the break test: lexical-form (in)equality between a loop
        variable and an eagerly evaluated comparison value. A missing
        variable compares as the empty string (REST-VKG parity)."""
        if break_arg is None:
            return None
        if not isinstance(break_arg, dict) or "name" not in break_arg:
            raise TypeError(
                "Iterate 'break' must be an object with 'name' and exactly one of 'equals'/'not-equals'"
            )
        has_equals = "equals" in break_arg
        has_not_equals = "not-equals" in break_arg
        if has_equals == has_not_equals:
            raise ValueError(
                "Iterate 'break' requires exactly one of 'equals'/'not-equals'"
            )
        name = break_arg["name"]
        comparison_form = break_arg["equals" if has_equals else "not-equals"]
        comparison = Operation.process_json(
            self.settings, comparison_form, self.context, variable_stack
        )
        comparison_lex = str(comparison)

        def test() -> bool:
            try:
                value = self.get_variable(name, variable_stack)
            except ValueError:
                value = ""
            lexical = str(value) if value is not None else ""
            matches = lexical == comparison_lex
            return matches if has_equals else not matches

        return test
