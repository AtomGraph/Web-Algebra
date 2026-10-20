"""Per-execution state, and the registry the HTTP service runs executions in.

The command line evaluates one document per process and exits, so settings that
live on the module and a `context` shared by every `Operation` ever constructed
were harmless there. A service does not have that luxury: several executions
run in one process at once, each with its own credentials, its own variable
scopes, and its own account of what it changed. All of that moves onto
`ExecutionContext`, created per execution and reachable from every operation in
it through `self.settings`.

Two deliberate limits, both visible in what the API reports:

* **Steps are the document's top-level forms.** Evaluating the document as one
  value would give no progress at all; evaluating every nested form as a step
  would report `ForEach` bodies as hundreds of rows. The top level is the unit
  the plan was approved in, so it is the unit progress is reported in.
* **Cancellation is cooperative and lands between steps.** An operation already
  waiting on a remote endpoint is not interrupted; the execution stops before
  the next step instead.
"""

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from rdflib import Graph

from web_algebra.main import LinkedDataHubSettings
from web_algebra.operation import Operation, OperationKind
from web_algebra.validation import OperationSummary, as_forms, summarize


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Step(BaseModel):
    """One top-level form, and how it went."""

    index: int
    op: str
    via: Optional[str] = None
    kind: OperationKind
    target: Optional[str] = None
    status: StepStatus = StepStatus.PENDING
    started: Optional[str] = None
    ended: Optional[str] = None
    detail: Optional[str] = None  # why it failed, in the terms the failure came in

    @classmethod
    def of(cls, summary: OperationSummary) -> "Step":
        return cls(**summary.model_dump())


class WriteLog:
    """Every document an execution changed, in the order it first changed one.

    Written from the HTTP clients (which report each completed mutating request)
    and read from the polling thread, so every access takes the lock. Ordered
    and de-duplicated because it is shown as a list of links: a `ForEach` that
    `PATCH`es the same document twice is one row, and the first row is the first
    thing that changed.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._documents: List[str] = []

    def record(self, method: str, url: str) -> None:
        with self._lock:
            if url not in self._documents:
                self._documents.append(url)

    def documents(self) -> List[str]:
        with self._lock:
            return list(self._documents)


class ExecutionSettings(LinkedDataHubSettings):
    """The settings one execution owns.

    `recorder` is the seam that turns a write into a reported change: the
    clients each operation builds take it off here, so nothing in the operation
    layer has to know it is running inside a service.

    TLS verification is on by default here — the opposite of the command line —
    with `ca_bundle` naming the authority that signs a LinkedDataHub's
    development certificate. Verifying against a named bundle is the point: the
    sidecar reaches its own instance and public endpoints alike, and turning
    verification off for the first would turn it off for the second.
    """

    verify_ssl: bool = True
    ca_bundle: Optional[str] = None
    recorder: Any = Field(default=None, exclude=True)


class ExecutionContext:
    """Everything one execution owns: settings, variable scopes, steps, writes."""

    def __init__(
        self,
        plan: Any,
        settings: ExecutionSettings,
        identifier: Optional[str] = None,
    ) -> None:
        self.id = identifier or uuid.uuid4().hex
        self.plan = plan
        self.forms = as_forms(plan)
        self.settings = settings
        # the clients every operation builds report their writes here, because
        # `ClientOperation` hands them `settings.recorder`
        self.writes = WriteLog()
        settings.recorder = self.writes
        # one scope for the whole document, which is what `Operation.process_json`
        # pushes around a sequence: a variable bound in step N is visible to N+1
        self.variable_stack: List[dict] = [{}]
        self.steps: List[Step] = [Step.of(summary) for summary in summarize(plan)]
        self.status = ExecutionStatus.RUNNING
        self.error: Optional[str] = None
        self.result: Optional[str] = None
        self.created = _now()
        # a monotonic stamp for the registry's TTL: `created` is for reading,
        # and a wall clock that steps backwards must not resurrect a record
        self.created_at = time.monotonic()
        self.cancelled = threading.Event()

    # --- running -------------------------------------------------------------

    def run(self, from_step: int = 0) -> None:
        """Evaluate the document's forms in order, stopping at the first failure.

        No transactionality: a failure leaves everything the earlier steps wrote
        in place, which is why the steps and the write log are reported as they
        are rather than rolled back.
        """
        for step in self.steps[:from_step]:
            if step.status is StepStatus.PENDING:
                step.status = StepStatus.SKIPPED

        for step in self.steps[from_step:]:
            if self.cancelled.is_set():
                self._skip_from(step.index)
                self.status = ExecutionStatus.CANCELLED
                return

            step.status = StepStatus.RUNNING
            step.started = _now()
            try:
                value = Operation.process_json(
                    self.settings, self.forms[step.index], {}, self.variable_stack
                )
            except Exception as error:  # an operation's failure is the step's failure
                step.status = StepStatus.FAILED
                step.ended = _now()
                step.detail = _detail(error)
                logging.exception("Execution %s failed at step %s", self.id, step.index)
                self._skip_from(step.index + 1)
                self.status = ExecutionStatus.FAILED
                self.error = f"{step.op}: {step.detail}"
                return

            step.status = StepStatus.SUCCEEDED
            step.ended = _now()
            self.result = _render(value)

        self.status = ExecutionStatus.SUCCEEDED

    def _skip_from(self, index: int) -> None:
        for step in self.steps[index:]:
            if step.status is StepStatus.PENDING:
                step.status = StepStatus.SKIPPED

    def cancel(self) -> None:
        self.cancelled.set()

    # --- reporting -----------------------------------------------------------

    def snapshot(self) -> dict:
        """What `GET /executions/{id}` answers — safe to build while running."""
        return {
            "id": self.id,
            "status": self.status.value,
            "steps": [step.model_dump() for step in self.steps],
            "affected_documents": self.writes.documents(),
            "result": self.result,
            "error": self.error,
        }


class ExecutionRegistry:
    """Running and recently finished executions, kept in memory.

    Memory only, and deliberately: an execution record is worth keeping until
    the browser that started it has read the outcome, and no longer. Durable
    records of what an agent did belong in LinkedDataHub as provenance, written
    through the ordinary API, not in this process's heap.
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._executions: Dict[str, ExecutionContext] = {}

    def submit(
        self, plan: Any, settings: ExecutionSettings, from_step: int = 0
    ) -> ExecutionContext:
        """Register an execution and start running it on its own thread."""
        execution = ExecutionContext(plan, settings)
        with self._lock:
            self._sweep()
            self._executions[execution.id] = execution

        thread = threading.Thread(
            target=execution.run,
            kwargs={"from_step": from_step},
            name=f"web-algebra-{execution.id[:8]}",
            daemon=True,
        )
        thread.start()
        return execution

    def get(self, identifier: str) -> Optional[ExecutionContext]:
        with self._lock:
            self._sweep()
            return self._executions.get(identifier)

    def _sweep(self) -> None:
        """Drop finished executions past their TTL. Caller holds the lock."""
        cutoff = time.monotonic() - self.ttl_seconds
        for identifier, execution in list(self._executions.items()):
            if (
                execution.status is not ExecutionStatus.RUNNING
                and execution.created_at < cutoff
            ):
                del self._executions[identifier]


# --- helpers -----------------------------------------------------------------


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _detail(error: Exception) -> str:
    """The failure in the terms it arrived in.

    HTTP failures propagate unwrapped (formal-semantics.md §3.7), so their
    status is on the exception and is the most useful thing a reader can be
    told — "504" explains a remote endpoint timing out where the class name
    does not.
    """
    status = getattr(error, "code", None)
    if status is not None:
        return f"{status} {error}"
    return f"{type(error).__name__}: {error}"


def _render(value: Any) -> Optional[str]:
    """A finished step's value, as text a client can display."""
    if value is None:
        return None
    if isinstance(value, Graph):
        return value.serialize(format="json-ld")
    try:
        return json.dumps(value) if isinstance(value, (dict, list)) else str(value)
    except TypeError:
        return str(value)
