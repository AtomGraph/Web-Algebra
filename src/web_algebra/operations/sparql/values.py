from typing import Any, List, Optional
from rdflib import URIRef, Literal, BNode
from rdflib.namespace import XSD
from rdflib.query import Result
from rdflib.term import Node
from mcp import types
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation
from web_algebra.json_result import JSONResult
from web_algebra.sparql_restrict import restrict


class Values(Operation, MCPTool):
    """
    Restricts variables of a SPARQL query or update to the rows of a result set
    (formal-semantics.md §4.3, binding restriction): the variables stay
    variables, and an inline `VALUES` block with the rows is joined into every
    group of the query, subqueries that do not project a column keeping their
    own copy. `Substitute` is the one-row, one-column case.

    Example: Values("DESCRIBE ?s WHERE { ?s ?p ?o }", <result over ?s>) produces
    "DESCRIBE ?s WHERE { VALUES (?s) { (<a>) (<b>) } ?s ?p ?o }".
    """

    @classmethod
    def description(cls) -> str:
        return """Restricts variables of a SPARQL query or update to the rows of a SPARQL result set, so one query is constrained by, or batched over, the results of another: an inline VALUES block with the rows is joined into every group of the query. The variables stay variables (still projected, still in templates). Columns default to the result's variables; vars selects and orders them; a row that does not bind a column leaves it free (UNDEF). Subqueries that do not project a column keep their own copy; the query must not assign a restricted variable itself (AS or VALUES). Blank nodes are rejected. Substitute is the one-variable, one-value case."""

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
                    "description": "The SPARQL query or update whose variables are restricted. It must not assign them itself (AS, VALUES).",
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
        """Pure function: restrict `query`'s variables to the rows of `data`."""
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

        table = []
        for row in rows:
            cells = [row.get(col) for col in columns]
            for term in cells:
                if isinstance(term, BNode):
                    raise ValueError(
                        "Values: blank nodes are not allowed in a SPARQL VALUES data block"
                    )
                if term is not None and not isinstance(term, (URIRef, Literal)):
                    raise TypeError(
                        f"Values expects RDF terms (URIRef/Literal) in bindings, got {type(term)}"
                    )
            table.append(cells)

        # binding restriction (formal-semantics.md §4.3): the columns stay
        # variables, restricted to the rows in every group of the query
        return Literal(restrict(str(query), columns, table), datatype=XSD.string)

    @classmethod
    def render_values(cls, columns: List[str], rows: List[dict]) -> str:
        """Render a SPARQL VALUES block from column names and normalised rows.
        Shared with the schema operations' `bindings` scope (§4.6)."""
        if len(columns) == 1:
            col = columns[0]
            cells = " ".join(cls._format_term(row.get(col)) for row in rows)
            return f"VALUES ?{col} {{ {cells} }}"

        header = " ".join(f"?{col}" for col in columns)
        tuples = " ".join(
            "( " + " ".join(cls._format_term(row.get(col)) for col in columns) + " )"
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

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Literal:
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
