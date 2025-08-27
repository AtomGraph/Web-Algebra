import logging
from typing import Any
from rdflib import URIRef, Literal, BNode
from rdflib.plugins.sparql import prepareQuery
from rdflib.namespace import XSD
from mcp import types
import re
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation


class Substitute(Operation, MCPTool):
    """
    Replaces variable placeholders in a SPARQL query with actual values from a given set of bindings.
    For example, Replace("DESCRIBE ?x", "x", URI("new_value")) produces "DESCRIBE <new_value>".
    """

    """
    Note: not a safe replacement atm, can lead to invalid SPARQL queries!
    """

    @classmethod
    def description(cls) -> str:
        return """Replaces variable placeholders in a SPARQL query with actual values from a given set of bindings. This operation allows for dynamic query construction by substituting variables with specific values, enabling flexible SPARQL query execution.
        For example, Replace("DESCRIBE ?x", "x", URI("new_value")) produces "DESCRIBE <new_value>"."""

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
        if not isinstance(binding_value, (URIRef, Literal, BNode)):
            raise TypeError(
                f"Substitute.execute expects binding_value to be URIRef, Literal, or BNode, got {type(binding_value)}"
            )

        query_str = str(query)
        var_str = str(var)

        logging.info("Substituting variable %s in SPARQL query", var_str)

        pss = ParameterizedSparqlString(query_str)
        pss.set_param(var_str, binding_value)
        substituted_query = pss.to_string()

        return Literal(substituted_query, datatype=XSD.string)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Literal:
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


class ParameterizedSparqlString:
    def __init__(self, command, base_uri=None, prefixes=None):
        self.command = command
        self.base_uri = base_uri
        self.params = {}
        self.positional_params = {}
        self.prefixes = prefixes or {}

    def set_base_uri(self, base_uri):
        self.base_uri = base_uri

    def add_prefix(self, prefix, uri):
        self.prefixes[prefix] = uri

    def set_param(self, var, value):
        if var.startswith("?"):
            var = var[1:]
        self.params[var] = self._validate_value(value)

    def set_param_positional(self, index, value):
        self.positional_params[index] = self._validate_value(value)

    def clear_param(self, var):
        self.params.pop(var, None)

    def clear_param_positional(self, index):
        self.positional_params.pop(index, None)

    def clear_params(self):
        self.params.clear()
        self.positional_params.clear()

    def _validate_value(self, value):
        if isinstance(value, (URIRef, Literal, BNode)):
            return value
        raise ValueError("Invalid RDFLib node type for parameter substitution.")

    def _safe_replace(self, query, var, value):
        safe_value = self._format_node(value)
        pattern = re.compile(rf"([?$]{var})([^\w]|$)")
        return pattern.sub(rf"{safe_value}\2", query)

    def _format_node(self, node):
        if isinstance(node, URIRef):
            return f"<{node}>"
        elif isinstance(node, Literal):
            if node.language:
                return f'"{node}"@{node.language}'
            elif node.datatype:
                return f'"{node}"^^<{node.datatype}>'
            else:
                return f'"{node}"'
        elif isinstance(node, BNode):
            return f"_: {node}"
        else:
            raise ValueError("Unsupported RDFLib node type")

    def __str__(self):
        return self.to_string()

    def to_string(self):
        query = self.command
        for var, value in self.params.items():
            query = self._safe_replace(query, var, value)

        positional_pattern = re.compile(r"\?(\s|[;,.])")
        index = 0
        adj = 0

        def replace_positional(match):
            nonlocal index, adj, query
            if index in self.positional_params:
                node_str = self._format_node(self.positional_params[index])
                index += 1
                return node_str + match.group(1)
            index += 1
            return match.group(0)

        query = positional_pattern.sub(replace_positional, query)

        prefix_decls = "\n".join(
            [f"PREFIX {p}: <{u}>" for p, u in self.prefixes.items()]
        )

        if self.base_uri:
            query = f"BASE <{self.base_uri}>\n" + query

        return prefix_decls + "\n" + query

    def as_query(self):
        """Parses the SPARQL string into a prepared query."""
        return prepareQuery(self.to_string(), initNs=self.prefixes)

    def copy(self):
        new_instance = ParameterizedSparqlString(
            self.command, self.base_uri, self.prefixes.copy()
        )
        new_instance.params = self.params.copy()
        new_instance.positional_params = self.positional_params.copy()
        return new_instance
