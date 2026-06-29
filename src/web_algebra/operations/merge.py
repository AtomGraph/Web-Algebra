import logging
from typing import Any, List
from rdflib import Graph
from mcp import types
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation


class Merge(Operation, MCPTool):
    """
    Merges a list of RDF graphs as JSON-LD into a single RDF graph as JSON-LD.
    """

    @classmethod
    def description(cls) -> str:
        return "Merges a list of RDF graphs as JSON-LD dicts into a single RDF graph as JSON-LD."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "graphs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "description": "A JSON-LD object representing an RDF graph.",
                    },
                    "description": "List of JSON-LD objects to merge into a single RDF graph.",
                }
            },
            "required": ["graphs"],
        }

    def execute(self, graphs: List[Graph]) -> Graph:
        """Pure function: merge list of RDF graphs"""
        if not isinstance(graphs, list):
            raise TypeError(
                f"Merge operation expects graphs to be list, got {type(graphs)}"
            )

        for i, graph in enumerate(graphs):
            if not isinstance(graph, Graph):
                raise TypeError(
                    f"Merge operation expects graph {i} to be Graph, got {type(graph)}"
                )

        merged_graph = Graph()

        for i, graph in enumerate(graphs):
            logging.info(f"Merging graph {i + 1}/{len(graphs)}...")
            merged_graph += graph

        logging.info("Merged RDF data (%s triple(s))", len(merged_graph))
        return merged_graph

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Graph:
        """JSON execution: process arguments and delegate to execute()"""
        # Process graphs argument - may return dicts with processed nested operations
        graphs_data = Operation.process_json(
            self.settings, arguments["graphs"], self.context, variable_stack
        )

        if not isinstance(graphs_data, list):
            raise TypeError(
                f"Merge operation expects 'graphs' to be list, got {type(graphs_data)}"
            )

        # Convert each resolved JSON-LD item into a Graph
        graph_objects = [self.to_graph(item) for item in graphs_data]

        # Delegate to execute() with Graph objects
        return self.execute(graph_objects)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        graphs_data = arguments["graphs"]

        # Convert JSON-LD objects to RDF Graphs
        graphs = [self.to_graph(data) for data in graphs_data]

        result_graph = self.execute(graphs)

        # Convert back to JSON-LD for MCP response
        jsonld_str = result_graph.serialize(format="json-ld")

        return [types.TextContent(type="text", text=jsonld_str)]
