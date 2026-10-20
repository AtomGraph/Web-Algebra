import logging
from typing import Any
from rdflib import URIRef, Literal, BNode
from rdflib.namespace import XSD
from mcp import types
import re
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation


class Substitute(Operation, MCPTool):
    """
    Substitutes one variable of a SPARQL query with an RDF term, written in
    SPARQL syntax (formal-semantics.md §4.3). For example,
    Substitute("DESCRIBE ?x", "x", <http://ex.org/a>) produces
    "DESCRIBE <http://ex.org/a>".

    The substitution is textual: it can produce an invalid query if the name
    also occurs inside a string literal of the query. Prefer Values where it
    applies.
    """

    @classmethod
    def description(cls) -> str:
        return """Substitutes one variable of a SPARQL query (every ?var and $var occurrence) with an RDF term, written in SPARQL syntax: a URI as <iri>, a literal as an escaped quoted string with its language tag or datatype. Nothing else in the query changes, and a variable that does not occur leaves the query unchanged. A URI that is not a valid SPARQL IRI raises an error; a blank node is rejected.
        For example, Substitute("DESCRIBE ?x", "x", URI("http://ex.org/a")) produces "DESCRIBE <http://ex.org/a>"."""

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

        logging.info("Substituting variable %s in SPARQL query", name)

        term = sparql_term(binding_value)
        # the replacement is a function, so nothing in the term is read as a
        # group reference or an escape (a literal holding "\\1" stays "\\1")
        pattern = re.compile(rf"[?$]{re.escape(name)}(?![\w\u00B7\u0300-\u036F\u203F-\u2040])")
        return Literal(pattern.sub(lambda _: term, str(query)), datatype=XSD.string)

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


# characters a SPARQL IRIREF excludes: controls, space and <>"{}|^`\
_IRIREF_EXCLUDED = re.compile(r'[\x00-\x20<>"{}|^`\\]')
# SPARQL ECHAR: \t \b \n \r \f \" \\
_ECHAR = str.maketrans({"\t": "\\t", "\b": "\\b", "\n": "\\n", "\r": "\\r", "\f": "\\f", '"': '\\"', "\\": "\\\\"})


def sparql_term(node: Any) -> str:
    """A URI or Literal in SPARQL syntax (formal-semantics.md §4.3 Substitute).

    A literal is a short quoted string in which every character SPARQL ECHAR
    names is escaped, followed by its language tag or datatype.
    """
    if isinstance(node, URIRef):
        if _IRIREF_EXCLUDED.search(str(node)):
            raise ValueError(f"<{node}> is not a valid SPARQL IRI")
        return f"<{node}>"
    if isinstance(node, Literal):
        lexical = str(node).translate(_ECHAR)
        if node.language:
            return f'"{lexical}"@{node.language}'
        if node.datatype:
            return f'"{lexical}"^^{sparql_term(node.datatype)}'
        return f'"{lexical}"'
    raise TypeError(f"Cannot write {type(node).__name__} as a SPARQL term")
