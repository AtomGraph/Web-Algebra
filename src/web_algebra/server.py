from typing import Sequence, List, Type
from mcp import Tool
from mcp.server import Server
from mcp.types import TextContent, ImageContent, EmbeddedResource
from web_algebra.main import LinkedDataHubSettings, list_operation_subclasses
import web_algebra.operations
from web_algebra.operation import Operation

server = Server("ldh-manager")
settings = LinkedDataHubSettings(cert_pem_path = "../LinkedDataHub/ssl/owner/cert.pem", cert_password = "Marchius")

def register(classes: List[Type[Operation]]):
    for cls in classes:
        Operation.register(cls)

register(list_operation_subclasses(web_algebra.operations, Operation))

@server.list_tools()
async def list_tools() -> list[Tool]:
    tools = []

    for tool_class in Operation.list_operations():
        tools.append(tool_class(settings))

    return tools

@server.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    tool_class = Operation.get(name)
    tool = tool_class(settings=settings)
    return tool.run(arguments)
