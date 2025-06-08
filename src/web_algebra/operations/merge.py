import json
import logging
from typing import Any
from rdflib import Graph
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from web_algebra.operation import Operation

class Merge(Operation):
    """
    Merges a list of RDF graphs as JSON-LD dicts into a single RDF graph as JSON-LD dict.
    """

    @classmethod
    def description(cls) -> str:
        return "Merges a list of RDF graphs as JSON-LD dicts into a single RDF graph as JSON-LD dict."
    
    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "graphs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "description": "A JSON-LD object representing an RDF graph."
                    },
                    "description": "List of JSON-LD objects to merge into a single RDF graph."
                }
            },
            "required": ["graphs"]
        }

    def execute(self, arguments: dict[str, Any]) -> Graph:
        """
        :param arguments: {"data": List[Dict]} where each dict is a JSON-LD object
        :return: Merged RDFLib Graph
        """
        graphs = Operation.execute_json(self.settings, arguments["graphs"], self.context)
        if not isinstance(graphs, list):
            raise ValueError("Merge expects 'data' to be a list of JSON-LD dicts.")

        merged_graph = Graph()

        for i, data in enumerate(graphs):
            json_str = json.dumps(data)
            logging.info(f"Parsing JSON-LD object {i+1}/{len(graphs)}...")
             
            g = Graph()
            g.parse(data=json_str, format="json-ld")

            merged_graph += g

        logging.info("Returning RDF data as a Python dict of JSON-LD (%s triple(s))", len(merged_graph))
        jsonld_str = merged_graph.serialize(format="json-ld", encoding="utf-8")
        jsonld_data = json.loads(jsonld_str)
        return jsonld_data

    async def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> list[types.TextContent]:
        json_ld_data = self.execute(arguments)

        if not isinstance(json_ld_data, dict):
            raise ValueError("Expected a JSON-LD dict from execute()")

        json_str = json.dumps(json_ld_data)

        graph = Graph()
        try:
            graph.parse(data=json_str, format="json-ld")
        except Exception as e:
            logging.error("Failed to parse JSON-LD data: %s", e)
            raise

        turtle_str = graph.serialize(format="turtle")

        return [types.TextContent(type="text", text=turtle_str)]
