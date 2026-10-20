import logging
from typing import Any
from rdflib import URIRef, Literal, BNode
from rdflib.namespace import XSD
from mcp import types
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation
from web_algebra.sparql_restrict import restrict


class Substitute(Operation, MCPTool):
    """
    Restricts one variable of a SPARQL query or update to an RDF term
    (formal-semantics.md §4.3, binding restriction): the variable stays a
    variable and can only be bound to the term. Substitute is Values over a
    one-row, one-column table.
    """

    @classmethod
    def description(cls) -> str:
        return """Gives one variable of a SPARQL query or update a value without removing the variable: an inline VALUES block restricting it to the term is joined into every group of the query, so the query stays valid, a SELECT still projects the variable and every result row still carries it. Subqueries that do not project the variable keep their own copy (it is renamed there). The query must not assign the variable itself (AS or VALUES). A URI is written as <iri>, a literal escaped; a blank node is rejected. Substitute is Values over a one-row table; use Values for several variables or rows.
        For example, Substitute("SELECT ?city ?label WHERE { ?city rdfs:label ?label }", "city", URI("http://ex.org/C")) produces "SELECT ?city ?label WHERE { VALUES (?city) { (<http://ex.org/C>) } ?city rdfs:label ?label }"."""

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
                    "description": "The SPARQL query string with variable placeholders.",
                },
                "var": {
                    "type": "string",
                    "description": "The variable to substitute in the query (e.g., '?x').",
                },
                "binding": {
                    "type": "object",
                    "properties": {
                        "value": {
                            "type": "string",
                            "description": "The value to substitute for the variable.",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["uri", "bnode", "literal"],
                            "description": "The type of the value to substitute.",
                        },
                    },
                    "required": ["value", "type"],
                    "description": "A dictionary containing the value and type to substitute for the variable.",
                },
            },
            "required": ["query", "var", "binding"],
        }

    def execute(self, query: Literal, var: Literal, binding_value: Any) -> Literal:
        """Pure function: substitute variable in SPARQL query with RDFLib terms"""
        if not isinstance(query, Literal):
            raise TypeError(
                f"Substitute.execute expects query to be Literal, got {type(query)}"
            )
        if not isinstance(var, Literal):
            raise TypeError(
                f"Substitute.execute expects var to be Literal, got {type(var)}"
            )
        if not isinstance(binding_value, (URIRef, Literal)):
            # formal-semantics.md §4.3: a blank-node label in a query is a
            # fresh variable, not a reference — substituting one is
            # meaningless, so BNode is rejected along with non-Terms.
            raise TypeError(
                f"Substitute.execute expects binding_value to be URIRef or Literal, got {type(binding_value)}"
            )

        name = str(var)
        if name[:1] in ("?", "$"):
            name = name[1:]

        logging.info("Restricting variable %s in SPARQL query", name)

        # binding restriction (formal-semantics.md §4.3): ?name stays a
        # variable, restricted to the term in every group of the query
        return Literal(restrict(str(query), [name], [[binding_value]]), datatype=XSD.string)

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Literal:
        """JSON execution: process arguments and call pure function"""
        # Process query
        query_data = Operation.process_json(
            self.settings, arguments["query"], self.context, variable_stack
        )
        query = Operation.json_to_rdflib(query_data)
        if not isinstance(query, Literal):
            raise TypeError(
                f"Substitute operation expects 'query' to be Literal, got {type(query)}"
            )

        # Process variable name
        var_data = Operation.process_json(
            self.settings, arguments["var"], self.context, variable_stack
        )
        var = Operation.json_to_rdflib(var_data)
        if not isinstance(var, Literal):
            raise TypeError(
                f"Substitute operation expects 'var' to be Literal, got {type(var)}"
            )

        # Process binding - should become RDFLib term via json_to_rdflib conversion
        binding_data = Operation.process_json(
            self.settings, arguments["binding"], self.context, variable_stack
        )
        binding_value = Operation.json_to_rdflib(binding_data)

        return self.execute(query, var, binding_value)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        query = Literal(arguments["query"], datatype=XSD.string)
        var = Literal(arguments["var"], datatype=XSD.string)

        binding_dict = arguments["binding"]
        if binding_dict["type"] == "uri":
            binding_value = URIRef(binding_dict["value"])
        elif binding_dict["type"] == "bnode":
            binding_value = BNode(binding_dict["value"])
        else:  # literal
            binding_value = Literal(binding_dict["value"])

        result = self.execute(query, var, binding_value)
        return [types.TextContent(type="text", text=str(result))]
