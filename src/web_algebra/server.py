from importlib.metadata import version
import logging
from mcp import types
from mcp.server import Server
from mcp.shared.exceptions import MCPError
from web_algebra.main import LinkedDataHubSettings, list_operation_subclasses, register
import web_algebra.operations
from web_algebra.operation import Operation
from web_algebra.mcp_tool import MCPTool

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# certificate from CERT_PEM_PATH / CERT_PASSWORD, read by the settings
settings = LinkedDataHubSettings()

register(list_operation_subclasses(web_algebra.operations, Operation))


def mcp_tools() -> dict:
    """The operations exposed as MCP tools, by name."""
    return {
        cls.name(): cls
        for cls in Operation.list_operations()
        if issubclass(cls, MCPTool)
    }


async def list_tools(ctx, params) -> types.ListToolsResult:
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name=cls.name(),
                description=cls.description(),
                input_schema=cls.inputSchema(),
            )
            for cls in mcp_tools().values()
        ]
    )


async def call_tool(ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
    # by name or deprecated alias (formal-semantics.md §4, Names)
    tool_class = Operation.get(params.name)
    if tool_class is None or not issubclass(tool_class, MCPTool):
        raise MCPError(types.INVALID_PARAMS, f"Unknown tool: {params.name}")

    try:
        content = tool_class(settings=settings).mcp_run(params.arguments or {})
    except Exception as e:
        # an operation's error is the tool's result, which the model can see
        logger.exception("Tool %s failed", params.name)
        return types.CallToolResult(
            content=[types.TextContent(text=f"{type(e).__name__}: {e}")],
            is_error=True,
        )
    return types.CallToolResult(content=list(content))


server = Server(
    "web-algebra",
    version=version("web-algebra"),
    on_list_tools=list_tools,
    on_call_tool=call_tool,
)

# streamable HTTP transport at /mcp
app = server.streamable_http_app(streamable_http_path="/mcp")
