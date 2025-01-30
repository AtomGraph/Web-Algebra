from typing import Any
import logging
import requests
from rdflib import Graph
from operation import Operation

class CONSTRUCT(Operation):
    """
    Executes a SPARQL CONSTRUCT query against a specified endpoint and returns the result as a Turtle-formatted string.
    """

    def __init__(self, context: dict = None, endpoint: str = None, query: dict = None):
        """
        Initialize the CONSTRUCT operation.
        :param context: Execution context.
        :param endpoint: The SPARQL endpoint to query.
        :param query: The SPARQL CONSTRUCT query (may be a string or a nested operation).
        """
        super().__init__(context)

        if endpoint is None:
            raise ValueError("CONSTRUCT operation requires 'endpoint' to be set.")
        if query is None:
            raise ValueError("CONSTRUCT operation requires 'query' to be set.")

        self.endpoint = endpoint
        self.query = query  # ✅ Could be a raw string or a nested operation

    def execute(self) -> str:
        """
        Executes a SPARQL CONSTRUCT query and returns the RDF data as a Turtle string.
        :return: A string containing the RDF data in Turtle format.
        """
        logging.info(f"Resolving SPARQL CONSTRUCT query for endpoint: {self.endpoint}")

        # ✅ Resolve `query` dynamically
        resolved_query = self.resolve_arg(self.query)
        logging.info(f"Executing SPARQL CONSTRUCT on {self.endpoint} with query:\n{resolved_query}")

        # ✅ Perform the SPARQL query
        headers = {"Accept": "application/n-triples"}  # Request N-Triples response
        params = {"query": resolved_query}

        response = requests.get(self.endpoint, headers=headers, params=params, timeout=10)
        response.raise_for_status()  # ✅ Let exceptions propagate naturally

        # ✅ Load response into an RDFLib Graph
        graph = Graph()
        graph.parse(data=response.text, format="nt")  # Load N-Triples into the graph

        # ✅ Serialize graph to Turtle string
        turtle_data = graph.serialize(format="turtle")
        logging.info(f"SPARQL CONSTRUCT query returned {len(graph)} triples.")

        return turtle_data  # ✅ Return Turtle string instead of Graph
