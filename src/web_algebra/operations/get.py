import json
import logging
from rdflib import Graph
from typing import Any
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from pydantic import ConfigDict
from web_algebra.operation import Operation
from web_algebra.client import LinkedDataClient

class GET(Operation):
    """
    Fetch RDF data from a given URL and return it as a Python dict with the JSON-LD response.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_post_init(self, __context: Any) -> None:
        self.client = LinkedDataClient(
            cert_pem_path=getattr(self.settings, 'cert_pem_path', None),
            cert_password=getattr(self.settings, 'cert_password', None),
            verify_ssl=False  # Optionally disable SSL verification
        )

    @classmethod
    def description(cls) -> str:
        return "Fetch RDF data from a given URL and return it as a Python dict with the JSON-LD response."
    
    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch RDF data from. This should be a valid URL pointing to RDF content."
                }
            },
            "required": ["url"]
        }
    
    def execute(self, arguments: dict[str, Any]) -> dict:
        """
        Fetch RDF data from the specified URL and return a Python dict representing JSON-LD.
        :param arguments: A dictionary containing:
            - `url`: The URL to fetch RDF data from.
        :return: A Python dict of JSON-LD data from the resolved URL.
        """
        url: str = Operation.execute_json(self.settings, arguments["url"], self.context)
        logging.info("Executing GET operation with URL: %s", url)

        graph: Graph = self.client.get(url)  # Let exceptions propagate
        logging.info("Successfully fetched RDF data from %s.", url)

        logging.info("Returning RDF data as a Python dict of JSON-LD (%s triple(s))", len(graph))
        jsonld_str = graph.serialize(format="json-ld", encoding="utf-8")
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
