import logging
from typing import Any
from rdflib import Variable, URIRef, Literal, BNode
from rdflib import URIRef, Literal, BNode
from rdflib.plugins.sparql import prepareQuery
from mcp import types
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
import re
from web_algebra.operation import Operation

class Substitute(Operation):
    """
    Replaces variable placeholders in a SPARQL query with actual values from a given set of bindings.
    """
    """
    Note: not a safe replacement atm, can lead to invalid SPARQL queries!
    """

    @property
    def description(self) -> str:
        return "Replaces variable placeholders in a SPARQL query with actual values from a given set of bindings. This operation allows for dynamic query construction by substituting variables with specific values, enabling flexible SPARQL query execution."
    
    @property
    def inputSchema(self):
        """
        Returns the JSON schema of the operation's input arguments.
        """
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SPARQL query with variable placeholders"},
                "binding": {
                    "type": "object",
                    "properties": {
                        "var": {"type": "string", "description": "Variable to substitute in the query"},
                        "value": {"type": ["string", "number", "boolean"], "description": "Value to substitute for the variable"},
                        "type": {"type": "string", "enum": ["uri", "bnode", "literal"], "description": "Type of the value"}
                    },
                    "required": ["var", "value", "type"]
                }
            },
            "required": ["query", "binding"]
        }
    
    def execute(self, arguments: dict[str, Any]) -> str:
        """
        Performs variable substitution in a SPARQL query.
        :param arguments: A dictionary containing:
            - `query`: The SPARQL query string with variable placeholders.
            - `var`: The variable to substitute in the query (e.g., "?x").
            - `binding`: A dictionary containing the value to substitute for the variable, with keys:
        :return: The SPARQL query with the variable substituted with the provided value.
        """
        query: str = Operation.execute_json(self.settings, arguments["query"], self.context)
        var: str = Operation.execute_json(self.settings, arguments["var"], self.context)
        binding: dict = Operation.execute_json(self.settings, arguments["binding"], self.context)

        if not isinstance(binding, dict):
            raise ValueError(f"Substitute operation requires 'binding' to be a dictionary, found: {binding}")

        binding = (
            URIRef(binding["value"]) if binding["type"] == "uri" else
            BNode(binding["value"]) if binding["type"] == "bnode" else
            Literal(binding["value"])
        )

        pss = ParameterizedSparqlString(query)
        pss.set_param(var, binding)
        substituted_query = pss.to_string()
        return substituted_query

    async def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        return [types.TextContent(type="text", text=self.execute(arguments))]

from rdflib import URIRef, Literal, BNode
from rdflib.plugins.sparql import prepareQuery
import re

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
        pattern = re.compile(rf'([?$]{var})([^\w]|$)')
        return pattern.sub(rf'{safe_value}\2', query)

    def _format_node(self, node):
        if isinstance(node, URIRef):
            return f'<{node}>'
        elif isinstance(node, Literal):
            if node.language:
                return f'"{node}"@{node.language}'
            elif node.datatype:
                return f'"{node}"^^<{node.datatype}>'
            else:
                return f'"{node}"'
        elif isinstance(node, BNode):
            return f'_: {node}'
        else:
            raise ValueError("Unsupported RDFLib node type")
    
    def __str__(self):
        return self.to_string()
    
    def to_string(self):
        query = self.command
        for var, value in self.params.items():
            query = self._safe_replace(query, var, value)
        
        positional_pattern = re.compile(r'\?(\s|[;,.])')
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
        
        prefix_decls = '\n'.join([f'PREFIX {p}: <{u}>' for p, u in self.prefixes.items()])
        
        if self.base_uri:
            query = f'BASE <{self.base_uri}>\n' + query
        
        return prefix_decls + '\n' + query
    
    def as_query(self):
        """Parses the SPARQL string into a prepared query."""
        return prepareQuery(self.to_string(), initNs=self.prefixes)
    
    def copy(self):
        new_instance = ParameterizedSparqlString(self.command, self.base_uri, self.prefixes.copy())
        new_instance.params = self.params.copy()
        new_instance.positional_params = self.positional_params.copy()
        return new_instance
