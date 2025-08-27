from typing import Sequence, List, Type
import logging
import os
from mcp import Tool
from mcp.server import Server
from mcp.types import TextContent, ImageContent, EmbeddedResource, Resource
from pydantic import AnyUrl
from web_algebra.main import LinkedDataHubSettings, list_operation_subclasses
import web_algebra.operations
from web_algebra.operation import Operation
from web_algebra.mcp_tool import MCPTool
import web_algebra.operations.sparql.select
from starlette.applications import Starlette
from starlette.routing import Mount
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

server = Server("web-algebra", "1.0.0")

# Initialize settings from environment variables
cert_pem_path = os.getenv("CERT_PEM_PATH")
cert_password = os.getenv("CERT_PASSWORD")

settings = LinkedDataHubSettings(
    cert_pem_path=cert_pem_path, cert_password=cert_password
)


def register(classes: List[Type[Operation]]):
    for cls in classes:
        Operation.register(cls)


register(list_operation_subclasses(web_algebra.operations, Operation))


@server.list_tools()
async def list_tools() -> list[Tool]:
    tools = []

    for tool_class in Operation.list_operations():
        # Only expose operations that implement MCPTool interface
        if issubclass(tool_class, MCPTool):
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
    tool_class = Operation.get(name)
    tool = tool_class(settings=settings)

    # Ensure the operation implements MCPTool interface
    if not isinstance(tool, MCPTool):
        raise ValueError(f"Operation {name} does not implement MCPTool interface")

    return tool.mcp_run(arguments)


@server.list_resources()
async def list_resources() -> Sequence[EmbeddedResource]:
    resources = []

    select = web_algebra.operations.sparql.select.SELECT(settings=settings)
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
        # text = binding["text"]["value"]
        resources.append(
            Resource(
                uri=AnyUrl(query),
                name=title,
                # description=text,
                mimeType="application/sparql-query",
            )
        )

    return resources


def create_app() -> Starlette:
    """Create Starlette app that wraps the MCP server"""

    # Create the session manager
    session_manager = StreamableHTTPSessionManager(
        app=server,
        json_response=False,
    )

    # Create an ASGI application that uses the session manager
    app = Starlette(
        debug=True,
        routes=[Mount("/mcp", app=session_manager.handle_request)],
        lifespan=lambda app: session_manager.run(),
    )

    return app


app = create_app()
