import logging
from typing import Any, ClassVar, Type, Union
from rdflib import URIRef, Literal, Graph
from rdflib.namespace import XSD
from mcp import types
from web_algebra.mcp_tool import MCPTool
from web_algebra.client_operation import ClientOperation
from web_algebra.operation import Operation
from web_algebra.client import SPARQLClient
from web_algebra.query_source import QuerySource


class DESCRIBE(QuerySource, ClientOperation, Operation, MCPTool):
    """
    Executes a SPARQL DESCRIBE query against a specified endpoint and returns a JSON-LD response.
    """

    client_class: ClassVar[Type] = SPARQLClient


    @classmethod
    def description(cls) -> str:
        return "Executes a SPARQL DESCRIBE query over an endpoint or over a graph in hand."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string", "description": "SPARQL endpoint URL (or give 'graph')"},
                "graph": {"description": "A graph to query locally (or give 'endpoint')"},
                "query": {"type": "string"},
            },
            "required": ["query"],
            "oneOf": [{"required": ["endpoint"]}, {"required": ["graph"]}],
        }

    def execute(self, source: Union[URIRef, Graph], query: Literal) -> Graph:
        """Pure function: execute a SPARQL DESCRIBE query over `source`, an
        endpoint URI or a Graph (formal-semantics.md §4.3)"""
        self.check_source(source, query)
        query_str = str(query)

        if isinstance(source, Graph):
            logging.info("Executing SPARQL DESCRIBE over a graph with query:\n%s", query_str)
            return source.query(query_str).graph

        endpoint_url = str(source)
        logging.info(
            "Executing SPARQL DESCRIBE on %s with query:\n%s", endpoint_url, query_str
        )

        # Execute using the SPARQL client and get JSON-LD response
        json_ld_response = self.client.query(endpoint_url, query_str)

        # Convert JSON-LD response to RDF Graph
        return self.to_graph(json_ld_response)

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Graph:
        """JSON execution: process arguments and return Graph (same as execute)"""
        source = self.resolve_source(arguments, variable_stack)
        query = self.resolve_query(arguments, variable_stack)
        return self.execute(source, query)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        endpoint = URIRef(arguments["endpoint"])
        query = Literal(arguments["query"], datatype=XSD.string)

        result_graph = self.execute(endpoint, query)

        # Convert Graph back to JSON-LD for MCP response
        json_ld_data = result_graph.serialize(format="json-ld")

        return [types.TextContent(type="text", text=json_ld_data)]
