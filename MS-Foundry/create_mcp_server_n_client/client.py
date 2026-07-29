"""
client.py
A tiny reusable MCP client that:
  1. Spawns the server as a subprocess over stdio.
  2. Handshakes with it (initialize).
  3. Lists available tools.
  4. Lets you call any tool by name with keyword arguments.
"""

from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """Small async context manager wrapping an MCP stdio session."""

    def __init__(self, server_script: str = "server.py"):
        # Path to the server file we want to launch.
        self.server_script = server_script

        # AsyncExitStack lets us cleanly close every async resource we open,
        # in the reverse order they were opened. This avoids the classic
        # "cancel scope in a different task" error you get if you close
        # things manually in the wrong order.
        self.exit_stack = AsyncExitStack()

        # Will hold the active MCP session once __aenter__ has run.
        self.session: ClientSession | None = None

    # -----------------------------
    # Enter: start server + session
    # -----------------------------
    async def __aenter__(self):
        # Tell MCP how to launch the server subprocess.
        params = StdioServerParameters(
            command="python",         # interpreter to run
            args=[self.server_script] # script to execute
        )

        # Start the stdio transport (launches the subprocess and
        # returns the (read_stream, write_stream) pair).
        read_stream, write_stream = await self.exit_stack.enter_async_context(
            stdio_client(params)
        )

        # Create the MCP client session on top of that transport.
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        # Perform the MCP handshake (capabilities exchange).
        await self.session.initialize()

        # Ask the server what tools it exposes and print them.
        tools = await self.session.list_tools()
        print("Available tools:", [t.name for t in tools.tools])

        return self

    # ----------------------------------
    # Exit: close everything cleanly
    # ----------------------------------
    async def __aexit__(self, exc_type, exc, tb):
        # Close the session and the subprocess in the right order.
        await self.exit_stack.aclose()
        print("Closed cleanly.")

    # ---------------------------------
    # Call a tool and return plain text
    # ---------------------------------
    async def run_tool(self, name: str, **kwargs):
        """Call the tool `name` with keyword args and return readable output."""

        # call_tool returns a CallToolResult with a list of content items.
        result = await self.session.call_tool(name, kwargs)

        # For a simple demo, join any text content into one string.
        # If a tool returns non-text content, fall back to str().
        if result.content:
            return "\n".join(
                getattr(item, "text", str(item)) for item in result.content
            )

        # No content at all: return the raw result so nothing is hidden.
        return result
