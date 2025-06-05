import json
import logging
from rdflib import Graph
from typing import Any
from operation import Operation

class Merge(Operation):
    """
    Merges a list of JSON-LD dicts into a single RDFLib Graph.
    """

    @property
    def description(self) -> str:
        return "Merges a list of JSON-LD objects into a single RDF graph."

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
