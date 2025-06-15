from typing import Sequence, List, Type
import logging
from mcp import Tool
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, ImageContent, EmbeddedResource, Resource
from pydantic import AnyUrl
from web_algebra.main import LinkedDataHubSettings, list_operation_subclasses
import web_algebra.operations
from web_algebra.operation import Operation
from web_algebra.operations.construct import CONSTRUCT
import web_algebra.operations.select

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)



async def serve() -> None:
    server = Server("web-algebra", "1.0.0")
    settings = LinkedDataHubSettings(cert_pem_path = "/Users/Martynas.Jusevicius/WebRoot/LinkedDataHub/ssl/owner/cert.pem", cert_password = "Marchius")

    def register(classes: List[Type[Operation]]):
        for cls in classes:
            Operation.register(cls)

    register(list_operation_subclasses(web_algebra.operations, Operation))

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        tools = []

        for tool_class in Operation.list_operations():
            tools.append(
                Tool(
                    name=tool_class.name(),
                    description=tool_class.description(),
                    inputSchema=tool_class.inputSchema(),
                )
            )

        return tools

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        tool_class =  Operation.get(name)
        tool = tool_class(settings=settings)
        return tool.run(arguments)
    
    @server.list_resources()
    async def list_resources() -> Sequence[EmbeddedResource]:
        resources = []

        select = web_algebra.operations.select.SELECT(settings=settings)
        args = {
            "query": """
                PREFIX  sp:  <http://spinrdf.org/sp#>
                PREFIX dct: <http://purl.org/dc/terms/>

                SELECT DISTINCT  ?query ?title ?text
                WHERE
                { GRAPH ?g
                    {   ?query  dct:title ?title ;
                            sp:text ?text
                    }
                }
            """,
            "endpoint": "https://localhost:4443/sparql",
            }
        
        result = select.execute(args)
        bindings = result["results"]["bindings"]
        logger.info(bindings)
        
        for binding in bindings:
            query = binding["query"]["value"]
            title = binding["title"]["value"]
            #text = binding["text"]["value"]
            resources.append(
                Resource(
                    uri=AnyUrl(query),
                    name=title,
                    #description=text,
                    mimeType="application/sparql-query",
                )
            )
    
        return resources
    
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        logger.info("Starting server with stdio")
        await server.run(read_stream, write_stream, options)
