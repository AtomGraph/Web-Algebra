import logging
from mcp.server.stdio import stdio_server
import asyncio
from .server import server

logger = logging.getLogger(__name__)


async def serve():
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        logger.info("Starting server with stdio")
        await server.run(read_stream, write_stream, options)


if __name__ == "__main__":
    asyncio.run(serve())
