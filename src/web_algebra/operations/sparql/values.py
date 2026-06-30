from typing import Any, List, Optional
from rdflib import URIRef, Literal, BNode
from rdflib.namespace import XSD
from rdflib.query import Result
from rdflib.term import Node
from mcp import types
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation
from web_algebra.json_result import JSONResult


class Values(Operation, MCPTool):
    """
    Appends a SPARQL `VALUES` data block, built from a result set, to a query.

    `Values` is the set-valued counterpart of `Substitute`: where `Substitute`
    injects a single term for a single variable, `Values` injects a whole solution
    sequence (rows × variables) as inline data. Every cell is serialized from its
    RDFLib term (never string-spliced), so IRIs and literals are escaped correctly.

    The block is appended as a trailing `ValuesClause` (`... WHERE { ... } VALUES
    ...`), which joins with the query's outermost group. This is the only `VALUES`
    position reachable without deconstructing the query into its algebra; interior
    placement (inside an OPTIONAL / sub-SELECT) is intentionally not supported.

    Example: Values("DESCRIBE ?s ?o WHERE { ?s ?p ?o }", <result over ?s>) produces
    "DESCRIBE ?s ?o WHERE { ?s ?p ?o } VALUES ?s { <a> <b> }".
    """

    @classmethod
    def description(cls) -> str:
        return """Appends a SPARQL VALUES data block, built from a SPARQL result set, to a query string. This is the set-valued counterpart of Substitute: it injects a whole solution sequence (rows of variable bindings) as inline data instead of a single term, enabling one query to be constrained by, or batched over, the results of another. The block is appended as a trailing VALUES clause that joins with the query's outermost group. Each value is serialized from its RDF term with correct escaping; blank nodes are rejected as they are not permitted in a VALUES block."""

    @classmethod
    def inputSchema(cls) -> dict:
        """
        Returns the JSON schema of the operation's input arguments.
        """
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The SPARQL query string to append the VALUES block to. It must not already end with a VALUES clause.",
                },
                "data": {
                    "type": "object",
                    "description": "A SPARQL result set (as produced by SELECT) whose variables and rows become the VALUES block. The variable names must match those used in the query.",
                },
                "vars": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional subset and ordering of variable names to emit as columns. Defaults to all variables of the result set.",
                },
            },
            "required": ["query", "data"],
        }

    def execute(
        self, query: Literal, data: Result, vars: Optional[List[str]] = None
    ) -> Literal:
        """Pure function: append a VALUES block rendered from `data` to `query`."""
        if not isinstance(query, Literal):
            raise TypeError(
                f"Values.execute expects query to be Literal, got {type(query)}"
            )
        if not isinstance(data, Result):
            raise TypeError(
                f"Values.execute expects data to be Result, got {type(data)}"
            )

        if vars is not None:
            columns = [str(v).lstrip("?") for v in vars]
        else:
            columns = [str(v) for v in (data.vars or [])]

        # Binding dict keys may be rdflib.Variable (from Graph.query) or str (from
        # JSONResult); normalise to plain names for lookup.
        rows = [
            {str(k): term for k, term in binding.items()}
            for binding in (data.bindings or [])
        ]

        block = self._render_values(columns, rows)
        return Literal(f"{str(query)} {block}", datatype=XSD.string)

    def _render_values(self, columns: List[str], rows: List[dict]) -> str:
        """Render a SPARQL VALUES block from column names and normalised rows."""
        if len(columns) == 1:
            col = columns[0]
            cells = " ".join(self._format_term(row.get(col)) for row in rows)
            return f"VALUES ?{col} {{ {cells} }}"

        header = " ".join(f"?{col}" for col in columns)
        tuples = " ".join(
            "( " + " ".join(self._format_term(row.get(col)) for col in columns) + " )"
            for row in rows
        )
        return f"VALUES ({header}) {{ {tuples} }}"

    @staticmethod
    def _format_term(term: Optional[Node]) -> str:
        """Serialize an RDF term to SPARQL syntax; None becomes UNDEF."""
        if term is None:
            return "UNDEF"
        if isinstance(term, BNode):
            raise ValueError(
                "Values: blank nodes are not allowed in a SPARQL VALUES data block"
            )
        if not isinstance(term, (URIRef, Literal)):
            raise TypeError(
                f"Values expects RDF terms (URIRef/Literal) in bindings, got {type(term)}"
            )
        # n3() yields correctly-escaped SPARQL syntax: <iri>, "lex", "lex"@lang,
        # "lex"^^<dt>, and bare numeric/boolean forms.
        return term.n3()

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Literal:
        """JSON execution: process arguments and delegate to execute()."""
        query_data = Operation.process_json(
            self.settings, arguments["query"], self.context, variable_stack
        )
        query = Operation.json_to_rdflib(query_data)
        if not isinstance(query, Literal):
            raise TypeError(
                f"Values operation expects 'query' to be Literal, got {type(query)}"
            )

        data = Operation.process_json(
            self.settings, arguments["data"], self.context, variable_stack
        )
        if not isinstance(data, Result):
            raise TypeError(
                f"Values operation expects 'data' to be Result, got {type(data)}"
            )

        vars = arguments.get("vars")
        if vars is not None:
            vars_data = Operation.process_json(
                self.settings, vars, self.context, variable_stack
            )
            vars = [str(v) for v in vars_data]

        return self.execute(query, data, vars)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results."""
        query = Literal(arguments["query"], datatype=XSD.string)
        data = JSONResult.from_json(arguments["data"])
        vars = arguments.get("vars")

        result = self.execute(query, data, vars)
        return [types.TextContent(type="text", text=str(result))]
