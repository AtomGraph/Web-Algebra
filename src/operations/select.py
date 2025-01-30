from typing import Any
import logging
import requests
from operation import Operation

class SELECT(Operation):
    """
    Executes a SPARQL SELECT query against a specified endpoint.
    """

    def __init__(self, context: dict = None, endpoint: str = None, query: dict = None):
        """
        Initialize the SELECT operation.
        :param context: Execution context.
        :param endpoint: The SPARQL endpoint to query.
        :param query: The SPARQL query (may be a string or a nested operation).
        """
        super().__init__(context)

        if endpoint is None:
            raise ValueError("SELECT operation requires 'endpoint' to be set.")
        if query is None:
            raise ValueError("SELECT operation requires 'query' to be set.")
        
        self.endpoint = endpoint
        self.query = query  # ✅ Could be a raw string or a nested operation

    def execute(self) -> list:
        """
        Executes a SPARQL SELECT query and returns results as a list of dictionaries.
        :return: A list of dictionaries representing SPARQL results.
        """
        logging.info(f"Resolving SPARQL query for endpoint: {self.endpoint}")

        # ✅ Resolve `query` dynamically
        resolved_query = self.resolve_arg(self.query)
        logging.info(f"Executing SPARQL SELECT on {self.endpoint} with query:\n{resolved_query}")

        # ✅ Perform the SPARQL query
        headers = {"Accept": "application/sparql-results+json"}
        params = {"query": resolved_query}

        response = requests.get(self.endpoint, headers=headers, params=params, timeout=10)
        response.raise_for_status()  # ✅ Let exceptions propagate naturally

        # ✅ Parse JSON response
        sparql_json = response.json()
        results = sparql_json["results"]["bindings"]

        logging.info(f"SPARQL SELECT query returned {len(results)} results.")
        return results
