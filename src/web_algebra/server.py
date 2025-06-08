from typing import Sequence, List, Type
import logging
from mcp import Tool
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, ImageContent, EmbeddedResource
from mcp.server.lowlevel.server import InitializationOptions, NotificationOptions
from web_algebra.main import LinkedDataHubSettings, list_operation_subclasses
import web_algebra.operations
from web_algebra.operation import Operation
import logging
from web_algebra.operations.construct import CONSTRUCT

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)



async def serve() -> None:
    server = Server("web-algebra", "1.0.0")
    settings = LinkedDataHubSettings(cert_pem_path = "../LinkedDataHub/ssl/owner/cert.pem", cert_password = "Marchius")

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
    
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        logger.info("Starting server with stdio")
        await server.run(read_stream, write_stream, options)
