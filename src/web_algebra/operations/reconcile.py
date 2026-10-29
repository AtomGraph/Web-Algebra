import json
import logging
from decimal import Decimal
from typing import Any, ClassVar, Optional, Type

from mcp import types
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
from rdflib.query import Result

from web_algebra.client import ReconciliationClient
from web_algebra.client_operation import ClientOperation
from web_algebra.json_result import JSONResult
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation
from web_algebra.rfc3986 import resolve


class Reconcile(ClientOperation, Operation, MCPTool):
    """The candidates a reconciliation service offers for a name, as a Result
    (formal-semantics.md §4.7).

    Speaks the W3C Entity Reconciliation Service API to the service at
    `endpoint`: its manifest gives the `identifierSpace` the candidate ids are
    local to, and the query goes as the `queries` form field. One row per
    candidate, best first, binding `entity` (the id resolved against the
    identifier space), `name`, `description` (when the service gives one),
    `score` (xsd:decimal) and `match` (xsd:boolean).
    """

    client_class: ClassVar[Type] = ReconciliationClient

    VARS: ClassVar[list] = ["entity", "name", "description", "score", "match"]

    @classmethod
    def description(cls) -> str:
        return (
            "The entities a reconciliation service (the W3C Reconciliation Service API) offers for a "
            "name, as a result: one row per candidate, best first, binding ?entity (a URI), ?name, "
            "?description, ?score and ?match. `type` is one of the service's type ids, `limit` caps "
            "the rows. Wikidata's service is https://wikidata-reconciliation.wmcloud.org/en/api, "
            "whose type ids are Wikidata items (Q515 city, Q6256 country, Q43229 organization)."
        )

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string", "description": "The reconciliation service's URL."},
                "query": {"type": "string", "description": "The name to reconcile."},
                "type": {"type": "string", "description": "Optional: one of the service's type ids, e.g. Q515."},
                "limit": {"type": "integer", "description": "Optional: at most this many candidates."},
            },
            "required": ["endpoint", "query"],
        }

    def execute(
        self,
        endpoint: URIRef,
        query: Literal,
        type: Optional[Literal] = None,
        limit: Optional[Literal] = None,
    ) -> Result:
        if not isinstance(endpoint, URIRef):
            raise TypeError(f"Reconcile.execute expects endpoint to be URIRef, got {endpoint!r}")
        if not Operation.is_string_compatible(query):
            raise TypeError(f"Reconcile.execute expects query to be a string Literal, got {query!r}")
        if type is not None and not Operation.is_string_compatible(type):
            raise TypeError(f"Reconcile.execute expects type to be a string Literal, got {type!r}")
        if limit is not None and not (isinstance(limit, Literal) and isinstance(limit.toPython(), int)):
            raise TypeError(f"Reconcile.execute expects limit to be an xsd:integer Literal, got {limit!r}")

        q0: dict = {"query": str(query)}
        if type is not None and str(type).strip():
            q0["type"] = str(type).strip()
        if limit is not None:
            q0["limit"] = limit.toPython()

        identifier_space = self.client.manifest(str(endpoint)).get("identifierSpace")
        if not identifier_space:
            raise ValueError(f"The reconciliation service at {endpoint} declares no identifierSpace in its manifest")

        logging.info("Reconcile %s against %s", q0, endpoint)
        candidates = (self.client.reconcile(str(endpoint), {"q0": q0}).get("q0") or {}).get("result") or []

        rows = []
        for candidate in candidates:
            if candidate.get("id") is None:
                continue
            row = {"entity": URIRef(resolve(identifier_space, str(candidate["id"])))}
            if candidate.get("name") is not None:
                row["name"] = Literal(str(candidate["name"]))
            if candidate.get("description"):
                row["description"] = Literal(str(candidate["description"]))
            if candidate.get("score") is not None:
                row["score"] = Literal(Decimal(str(candidate["score"])), datatype=XSD.decimal)
            row["match"] = Literal(bool(candidate.get("match", False)), datatype=XSD.boolean)
            rows.append(row)

        return JSONResult(vars=self.VARS, bindings=rows)

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Result:
        def argument(name: str):
            if name not in arguments:
                return None
            return Operation.json_to_rdflib(
                Operation.process_json(self.settings, arguments[name], self.context, variable_stack)
            )

        endpoint = argument("endpoint")
        if not isinstance(endpoint, URIRef):
            raise TypeError(f"Reconcile operation expects 'endpoint' to be URIRef, got {type(endpoint)}")
        return self.execute(endpoint, argument("query"), argument("type"), argument("limit"))

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        result = self.execute(
            URIRef(arguments["endpoint"]),
            Literal(arguments["query"], datatype=XSD.string),
            Literal(arguments["type"], datatype=XSD.string) if arguments.get("type") else None,
            Literal(int(arguments["limit"]), datatype=XSD.integer) if arguments.get("limit") is not None else None,
        )
        return [types.TextContent(type="text", text=json.dumps(result.to_json()))]
