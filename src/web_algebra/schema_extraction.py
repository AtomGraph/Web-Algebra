import logging
import re
from typing import Any, ClassVar, Optional, Type
from mcp import types
from rdflib import Graph, URIRef
from rdflib.query import Result
from web_algebra.client import SPARQLClient
from web_algebra.client_operation import ClientOperation
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation
from web_algebra.operations.sparql.values import Values

# Where an extraction query takes its scope: inside its innermost groups,
# where ?subject is bound.
SCOPE = "%SCOPE%"

# A named-graph branch of an extraction query, `UNION { GRAPH ?g {`.
_GRAPH_BRANCH = re.compile(r"UNION\s*\{\s*GRAPH\s+\?\w+\s*\{")


def without_graph_branches(query: str) -> str:
    """The query without its named-graph branches: every
    `UNION { GRAPH ?g { ... } }` removed and the default-graph branch beside
    it left standing — for an endpoint that refuses the keyword."""
    while (match := _GRAPH_BRANCH.search(query)) is not None:
        depth = 0
        i = query.index("{", match.start())
        while i < len(query):
            if query[i] == "{":
                depth += 1
            elif query[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        query = query[: match.start()] + query[i + 1 :]
    return query


class SchemaExtraction(ClientOperation, MCPTool):
    """Mixin for the schema operations (formal-semantics.md §4.6): each takes
    `endpoint`, the URI of a SPARQL endpoint, and optionally `bindings`, a
    Result whose `subject` column scopes the extraction; it queries the
    instance data there and returns an ontology Graph. *Query* effect.

    Not an `Operation` itself, so operation discovery does not register it.
    """

    client_class: ClassVar[Type] = SPARQLClient

    #: The extraction CONSTRUCT query, with `%SCOPE%` where the scope goes.
    QUERY: ClassVar[str] = ""

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string", "description": "SPARQL endpoint URL"},
                "bindings": {
                    "description": "Optional SELECT result whose ?subject column scopes the extraction to those subjects"
                },
            },
            "required": ["endpoint"],
        }

    def execute(self, endpoint: URIRef, bindings: Optional[Result] = None) -> Graph:
        """Pure function: extract over the endpoint, scoped by `bindings`"""
        return self.extract(endpoint, self.scope(endpoint, bindings))

    def extract(self, endpoint: URIRef, scope: str) -> Graph:
        """Run this extraction's query with `scope` (a VALUES block, or "")."""
        query = self.QUERY.replace(SCOPE, scope)
        if not self.client.takes_graph(str(endpoint)):
            query = without_graph_branches(query)
        logging.info("%s on %s", self.name(), endpoint)
        # POSTed as a form: a scope of a few hundred subjects makes a query that
        # a URL cannot carry
        return Operation.to_graph(self.client.query(str(endpoint), query, post=True))

    def scope(self, endpoint: Any, bindings: Optional[Result]) -> str:
        """Validate the arguments and render `bindings` as a VALUES block over
        ?subject; the empty string when unscoped (§4.6)."""
        if not isinstance(endpoint, URIRef):
            raise TypeError(
                f"{self.name()} operation expects 'endpoint' to be URIRef, got {type(endpoint)}"
            )
        if bindings is None:
            return ""
        if not isinstance(bindings, Result):
            raise TypeError(
                f"{self.name()} expects 'bindings' to be a Result, got {type(bindings).__name__}"
            )
        names = [str(var) for var in (bindings.vars or [])]
        if "subject" not in names:
            raise ValueError(
                f"{self.name()} 'bindings' must bind ?subject, the subjects to describe; it binds {names}"
            )
        rows = [
            {str(k): term for k, term in binding.items()}
            for binding in (bindings.bindings or [])
        ]
        # no subjects is a finding, not a schema: an extraction over nothing
        # would only pass an empty ontology along
        if not rows:
            raise ValueError(f"{self.name()}: the 'bindings' matched no subjects")
        return Values.render_values(["subject"], rows)

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Graph:
        """JSON execution: process arguments with strict type checking"""
        endpoint = Operation.process_json(
            self.settings, arguments["endpoint"], self.context, variable_stack
        )
        bindings = None
        if "bindings" in arguments:
            bindings = Operation.process_json(
                self.settings, arguments["bindings"], self.context, variable_stack
            )
        return self.execute(endpoint, bindings)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        graph = self.execute(URIRef(arguments["endpoint"]))
        return [types.TextContent(type="text", text=graph.serialize(format="json-ld"))]
