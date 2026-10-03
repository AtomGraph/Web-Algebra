from typing import Any, ClassVar, Type, Union
import logging
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import XSD
from rdflib.query import Result
from mcp import types
from web_algebra.mcp_tool import MCPTool
from web_algebra.client_operation import ClientOperation
from web_algebra.operation import Operation
from web_algebra.client import SPARQLClient
from web_algebra.json_result import JSONResult
from web_algebra.query_source import QuerySource


class SELECT(QuerySource, ClientOperation, Operation, MCPTool):
    """
    Executes SPARQL SELECT queries over an endpoint or a graph
    """

    client_class: ClassVar[Type] = SPARQLClient


    @classmethod
    def description(cls) -> str:
        return "Executes a SPARQL SELECT query over an endpoint or over a graph in hand"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string", "description": "SPARQL endpoint URL (or give 'graph')"},
                "graph": {"description": "A graph to query locally (or give 'endpoint')"},
                "query": {"type": "string", "description": "SPARQL SELECT query"},
            },
            "required": ["query"],
            "oneOf": [{"required": ["endpoint"]}, {"required": ["graph"]}],
        }

    def execute(self, source: Union[URIRef, Graph], query: Literal) -> Result:
        """Pure function: execute a SPARQL SELECT query over `source`, an
        endpoint URI or a Graph (formal-semantics.md §4.3)"""
        # Strict Type Checking before any network side effect.
        self.check_source(source, query)
        query_str = str(query)

        if isinstance(source, Graph):
            logging.info("Executing SPARQL SELECT over a graph with query:\n%s", query_str)
            result = source.query(query_str)
            return JSONResult(
                vars=[str(var) for var in result.vars],
                bindings=[
                    {str(var): term for var, term in row.items() if term is not None}
                    for row in result.bindings
                ],
            )

        endpoint_url = str(source)
        logging.info(
            "Executing SPARQL SELECT on %s with query:\n%s", endpoint_url, query_str
        )

        # Execute using the SPARQL client
        sparql_json = self.client.query(endpoint_url, query_str)
        logging.info(
            "SPARQL SELECT query returned %d bindings.",
            len(sparql_json.get("results", {}).get("bindings", [])),
        )

        return JSONResult.from_json(sparql_json)

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Result:
        """JSON execution: process arguments with strict type checking"""
        source = self.resolve_source(arguments, variable_stack)
        query = self.resolve_query(arguments, variable_stack)
        return self.execute(source, query)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        endpoint = URIRef(arguments["endpoint"])
        query = Literal(arguments["query"], datatype=XSD.string)

        result = self.execute(endpoint, query)

        import json

        return [
            types.TextContent(
                type="text",
                text=json.dumps(result.to_json()),
            )
        ]
