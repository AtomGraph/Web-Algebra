import json
import logging
import requests
from rdflib import Graph
from typing import Any, Union
from operation import Operation

class CONSTRUCT(Operation):
    """
    Executes a SPARQL CONSTRUCT query against a specified endpoint and returns a Python dict of JSON-LD.
    """

    def __init__(self, context: dict = None, endpoint: str = None, query: Union[str, dict] = None):
        """
        Initialize the CONSTRUCT operation.
        :param context: Execution context.
        :param endpoint: The SPARQL endpoint to query.
        :param query: The SPARQL CONSTRUCT query (may be a string or nested operation).
        """
        super().__init__(context)

        if endpoint is None:
            raise ValueError("CONSTRUCT operation requires 'endpoint' to be set.")
        if query is None:
            raise ValueError("CONSTRUCT operation requires 'query' to be set.")

        self.endpoint = endpoint
        self.query = query  # Could be a raw string or another operation

    def execute(self) -> dict:
        """
        Executes a SPARQL CONSTRUCT query and returns the RDF data as a Python dict of JSON-LD.
        :return: A Python dict containing the JSON-LD representation of the constructed RDF graph.
        """
        logging.info(f"Resolving SPARQL CONSTRUCT query for endpoint: {self.endpoint}")

        # 1) Resolve `query` dynamically (in case it's nested)
        resolved_query = self.resolve_arg(self.query)
        if not isinstance(resolved_query, str):
            raise ValueError("CONSTRUCT operation expects 'query' to be a string.")

        logging.info(f"Executing SPARQL CONSTRUCT on {self.endpoint} with query:\n{resolved_query}")

        # 2) Perform the SPARQL query
        headers = {"Accept": "application/n-triples"}  # Request N-Triples
        params = {"query": resolved_query}

        response = requests.get(self.endpoint, headers=headers, params=params, timeout=10)
        response.raise_for_status()  # Let exceptions propagate naturally

        # 3) Parse the response into an RDFLib Graph
        graph = Graph()
        graph.parse(data=response.text, format="nt")  # Load N-Triples

        logging.info(f"SPARQL CONSTRUCT query returned {len(graph)} triples.")

        # 4) Serialize the graph as JSON-LD (string)
        jsonld_str = graph.serialize(format="json-ld")

        # 5) Convert JSON-LD string to a Python dict
        jsonld_data = json.loads(jsonld_str)

        logging.info("Returning the constructed graph as a JSON-LD dict.")
        return jsonld_data
