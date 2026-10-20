"""The provider seam, and the generate-validate-repair loop around it.

One module so that swapping providers is a constructor change and nothing else:
the service holds a `Provider`, and everything above it deals in messages and
JSON. `prompts/system.md` — the operation documentation the CLI REPL has been
tuned against — is the system message here too, so generation quality starts
where the REPL left it rather than from scratch.

Tool calling is deliberately not used. Incremental tool calls would fragment a
plan into steps that are executed as they are decided, which is exactly the
property this design gives up in exchange for a document the user reads and
approves before anything runs.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel

from web_algebra.validation import Diagnostic, validate

# Appended to `prompts/system.md`. The REPL asked for a bare operation document;
# a plan carries a sentence of prose beside it, and JSON mode answers with an
# object, so the envelope is stated here rather than by editing the shared
# prompt the CLI also uses.
OUTPUT_CONTRACT = """

# Response envelope

Answer with a single JSON object with exactly these two members:

- `"plan"`: an ARRAY of operation objects, executed in order. Use an array even
  for a single operation.
- `"summary"`: one or two plain sentences, addressed to the user, saying what
  the plan will do and to what. Name what changes. Do not describe the JSON.

Return nothing else — no prose outside the object, no code fences.

# Context

The user is working in a LinkedDataHub instance. These values are given to you
and are the addresses to use unless the instruction names others:

{context}
"""

REPAIR_PROMPT = """The plan you returned is not executable. Fix these problems and return the whole envelope again:

{diagnostics}"""


class LLMError(RuntimeError):
    """The provider could not be reached, or did not answer with an object."""


class Provider(ABC):
    """A chat model that can be asked for one JSON object."""

    @abstractmethod
    def complete_json(self, messages: List[dict]) -> dict:
        """Return the model's reply, parsed. Raise `LLMError` if it is not an object."""


class OpenAIProvider(Provider):
    """OpenAI chat completions in JSON mode."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete_json(self, messages: List[dict]) -> dict:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
            )
        except Exception as error:
            raise LLMError(f"{self.model} could not be reached: {error}") from error

        content = completion.choices[0].message.content or ""
        try:
            reply = json.loads(content)
        except json.JSONDecodeError as error:
            raise LLMError(f"{self.model} did not answer with JSON: {error}") from error
        if not isinstance(reply, dict):
            raise LLMError(f"{self.model} answered with {type(reply).__name__}, not an object")
        return reply


class GeneratedPlan(BaseModel):
    """What one `POST /plans` produced, valid or not.

    An invalid plan is still returned rather than swallowed: the repair loop has
    already had its attempts, and showing the user what the model produced with
    the reasons it will not run is more use than an opaque failure.
    """

    plan: Any
    summary: str
    valid: bool
    diagnostics: List[Diagnostic] = []
    attempts: int = 1


def system_prompt(prompts_dir: Optional[Path] = None) -> str:
    """The operation documentation the model is given, without the context block."""
    directory = prompts_dir or Path(os.getenv("PROMPTS_DIR", "prompts"))
    return (directory / "system.md").read_text()


def generate(
    provider: Provider,
    messages: List[dict],
    context: dict,
    prompt: str,
    max_repairs: int = 3,
) -> GeneratedPlan:
    """Ask for a plan, and keep asking while it is not executable.

    The loop is the safety net the DSL's openness requires: an `@op` envelope
    around arbitrary JSON-LD cannot be constrained by a schema alone, so the
    validator's diagnostics go back to the model as an ordinary turn, up to
    `max_repairs` times.
    """
    conversation: List[dict] = [
        {
            "role": "system",
            "content": prompt + OUTPUT_CONTRACT.format(context=_render_context(context)),
        },
        *messages,
    ]

    last: Optional[GeneratedPlan] = None
    for attempt in range(1, max_repairs + 2):
        reply = provider.complete_json(conversation)
        plan = reply.get("plan")
        summary = str(reply.get("summary") or "").strip()
        result = validate(plan)
        last = GeneratedPlan(
            plan=plan if plan is not None else [],
            summary=summary,
            valid=result.valid and plan is not None,
            diagnostics=result.diagnostics,
            attempts=attempt,
        )
        if last.valid:
            return last

        logging.info(
            "Plan attempt %s invalid (%s diagnostics), repairing",
            attempt,
            len(result.diagnostics),
        )
        conversation.append({"role": "assistant", "content": json.dumps(reply)})
        conversation.append(
            {
                "role": "user",
                "content": REPAIR_PROMPT.format(
                    diagnostics="\n".join(
                        f"- {diagnostic.path}: {diagnostic.message}"
                        for diagnostic in result.diagnostics
                    )
                    or "- the response has no `plan` member"
                ),
            }
        )

    return last  # type: ignore[return-value]


def _render_context(context: dict) -> str:
    return "\n".join(f"- {key}: {value}" for key, value in context.items() if value)
