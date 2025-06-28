from typing import Any
import logging
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from web_algebra.operation import Operation
from web_algebra.client import SPARQLClient

class SELECT(Operation):
    """
    Executes a SPARQL SELECT query against a specified endpoint.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = SPARQLClient(
            cert_pem_path=getattr(self.settings, 'cert_pem_path', None),
            cert_password=getattr(self.settings, 'cert_password', None),
            verify_ssl=False  # Optionally disable SSL verification
        )

    @classmethod
    def description(cls) -> str:
        return "Executes a SPARQL SELECT query against a specified endpoint and returns results as a list of dictionaries."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "The SPARQL endpoint URL to query."
                },
                "query": {
                    "type": "string",
                    "description": "The SPARQL SELECT query string to execute."
                }
            },
            "required": ["endpoint", "query"]
        }
    
    def execute(self, arguments: dict[str, Any]) -> list:
        """
        Executes a SPARQL SELECT query and returns results as a list of dictionaries.
        :param arguments: A dictionary containing:
            - `endpoint`: The SPARQL endpoint URL to query.
            - `query`: The SPARQL SELECT query string to execute.
        :return: A list of dictionaries representing SPARQL results.
        """
        endpoint: str = Operation.execute_json(self.settings, arguments["endpoint"], self.context)
        query: str = Operation.execute_json(self.settings, arguments["query"], self.context)
        
        logging.info("Executing SPARQL SELECT on %s with query:\n%s", endpoint, query)

        results = self.client.query(endpoint, query)
        logging.info("SPARQL SELECT query returned %s bindings.", len(results["results"]["bindings"]))
        return results

    def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        return [types.TextContent(type="text", text=sparql_json_to_csv(self.execute(arguments)))]

import csv
import io

def sparql_json_to_csv(result_json: dict) -> str:
    vars = result_json.get("head", {}).get("vars", [])
    rows = result_json.get("results", {}).get("bindings", [])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(vars)

    for row in rows:
        writer.writerow([
            row.get(var, {}).get("value", "") for var in vars
        ])

    return output.getvalue()
