"""The HTTP service: generate a plan, validate one, execute one, watch it run.

Generation and execution are separate endpoints on purpose. The document
between them is the artifact the user reads and approves, so it has to exist as
a value the client holds — not as a step inside one call. `POST /executions`
re-validates what it is handed, so what was displayed is what runs.

The service is stateless about conversations: the client sends the whole thread
with every `POST /plans` call, and LinkedDataHub keeps the history. The only
state here is the executions in flight, which live in memory until their TTL.

The MCP server mounts unchanged at `/mcp`, so one process serves both surfaces.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Response, status
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from pydantic import BaseModel, Field

from web_algebra import llm
from web_algebra.execution import ExecutionRegistry, ExecutionSettings
from web_algebra.llm import LLMError, OpenAIProvider, Provider
from web_algebra.server import server  # registers every operation on import
from web_algebra.validation import Diagnostic, OperationSummary, summarize, validate

logger = logging.getLogger(__name__)

# How long a finished execution stays readable. Long enough that a browser that
# was closed mid-run can still be told how it ended; short enough that the
# process does not accumulate them.
EXECUTION_TTL_SECONDS = int(os.getenv("EXECUTION_TTL_SECONDS", "3600"))

registry = ExecutionRegistry(ttl_seconds=EXECUTION_TTL_SECONDS)


# --- request and response models ---------------------------------------------


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class PlanContext(BaseModel):
    """Where the user is, so the plan addresses their instance and not a guess."""

    base: Optional[str] = None
    document: Optional[str] = None
    endpoint: Optional[str] = None
    # The current document's RDF, as the client already holds it. Truncated on
    # the way in: it is context, and a large document would crowd out the
    # operation documentation that makes the plan correct.
    document_rdf: Optional[str] = None


class PlanRequest(BaseModel):
    messages: List[Message]
    context: PlanContext = PlanContext()


class PlanResponse(BaseModel):
    plan: Any
    summary: str
    ops: List[OperationSummary]
    valid: bool
    diagnostics: List[Diagnostic] = []


class ValidateRequest(BaseModel):
    plan: Any


class ValidateResponse(BaseModel):
    valid: bool
    diagnostics: List[Diagnostic] = []
    ops: List[OperationSummary] = []


class ExecutionRequest(BaseModel):
    plan: Any
    # Where to resume: a retry after a failure re-runs from the step that failed
    # rather than from the top, so the steps that already wrote do not write again.
    from_step: int = Field(default=0, ge=0)


DOCUMENT_RDF_LIMIT = int(os.getenv("DOCUMENT_RDF_LIMIT", "4096"))


# --- application -------------------------------------------------------------

session_manager = StreamableHTTPSessionManager(app=server, json_response=False)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with session_manager.run():
        yield


app = FastAPI(
    title="Web Algebra",
    description="Natural language to Web Algebra documents, and their execution.",
    version="2.0.0",
    lifespan=lifespan,
)

app.mount("/mcp", session_manager.handle_request)


# --- configuration -----------------------------------------------------------


def _secret(name: str, variable: str) -> Optional[str]:
    """A Docker secret if one is mounted, otherwise the environment variable.

    Secrets first because that is where the deployment puts credentials; the
    variable is what makes the service runnable outside a container.
    """
    path = Path("/run/secrets") / name
    if path.exists():
        return path.read_text().strip()
    return os.getenv(variable)


def _settings() -> ExecutionSettings:
    """Fresh settings per execution — see `ExecutionSettings`."""
    return ExecutionSettings(
        cert_pem_path=_secret("agent_cert", "CERT_PEM_PATH"),
        cert_password=_secret("agent_cert_password", "CERT_PASSWORD"),
        verify_ssl=os.getenv("VERIFY_SSL", "true").lower() != "false",
        ca_bundle=os.getenv("CA_BUNDLE") or None,
    )


def _provider() -> OpenAIProvider:
    api_key = _secret("openai_api_key", "OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "No LLM credentials configured: mount /run/secrets/openai_api_key",
        )
    return OpenAIProvider(api_key, model=os.getenv("OPENAI_MODEL", "gpt-4o"))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/plans", response_model=PlanResponse)
def create_plan(
    request: PlanRequest, provider: Provider = Depends(_provider)
) -> PlanResponse:
    """Turn a conversation into a Web Algebra document. Nothing is executed."""
    context = request.context.model_dump()
    if context.get("document_rdf"):
        context["document_rdf"] = context["document_rdf"][:DOCUMENT_RDF_LIMIT]

    try:
        generated = llm.generate(
            provider,
            [message.model_dump() for message in request.messages],
            context,
            llm.system_prompt(),
        )
    except LLMError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error

    return PlanResponse(
        plan=generated.plan,
        summary=generated.summary,
        ops=summarize(generated.plan),
        valid=generated.valid,
        diagnostics=generated.diagnostics,
    )


@app.post("/validate", response_model=ValidateResponse)
def validate_plan(request: ValidateRequest) -> ValidateResponse:
    """Re-check a document — a hand-edited plan, or one held from an earlier turn."""
    result = validate(request.plan)
    return ValidateResponse(
        valid=result.valid,
        diagnostics=result.diagnostics,
        ops=summarize(request.plan),
    )


@app.post("/executions", status_code=status.HTTP_202_ACCEPTED)
def create_execution(
    request: ExecutionRequest,
    response: Response,
    settings: ExecutionSettings = Depends(_settings),
) -> dict:
    """Run a document. Answers immediately; progress is read back by polling."""
    result = validate(request.plan)
    if not result.valid:
        # The client displayed this plan, so a plan that will not run must be
        # refused rather than half-run: 422 with the same diagnostics the
        # generation call would have carried.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[diagnostic.model_dump() for diagnostic in result.diagnostics],
        )

    execution = registry.submit(request.plan, settings, from_step=request.from_step)
    response.headers["Location"] = f"/executions/{execution.id}"
    return execution.snapshot()


@app.get("/executions/{identifier}")
def read_execution(identifier: str) -> dict:
    execution = registry.get(identifier)
    if execution is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such execution")
    return execution.snapshot()


@app.delete("/executions/{identifier}")
def cancel_execution(identifier: str) -> dict:
    """Ask a running execution to stop. It stops before its next step."""
    execution = registry.get(identifier)
    if execution is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such execution")
    execution.cancel()
    return execution.snapshot()
