import json
import logging
from rdflib import Graph
from typing import Union, Any, ClassVar
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from pydantic import Field, ConfigDict
from operation import Operation
from client import LinkedDataClient

class GET(Operation):
    """
    Fetch RDF data from a given URL and return it as a Python dict of JSON-LD.
    """

    #client: LinkedDataClient = Field(init=False)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_post_init(self, __context: Any) -> None:
        self.client = LinkedDataClient(
            cert_pem_path=getattr(self.settings, 'cert_pem_path', None),
            cert_password=getattr(self.settings, 'cert_password', None),
            verify_ssl=False  # Optionally disable SSL verification
        )

    def execute(self, arguments: dict[str, Any]) -> dict:
        """
        Fetch RDF data from the specified URL and return a Python dict representing JSON-LD.
        :return: A Python dict of JSON-LD data from the resolved URL.
        """
        url = arguments["url"]
        logging.info(f"Executing GET operation with URL: %s", url)

        graph: Graph = self.client.get(url)  # Let exceptions propagate
        logging.info(f"Successfully fetched RDF data from {url}.")

        jsonld_str = graph.serialize(format="json-ld")
        jsonld_data = json.loads(jsonld_str)

        logging.info("Returning RDF data as a Python dict of JSON-LD: %s", jsonld_data)
        return jsonld_data

    async def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        return [types.TextContent(type="text", text=str(self.process(arguments)))]
