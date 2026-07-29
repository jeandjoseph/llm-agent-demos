"""
agent.py
A very small "agent" script that uses MCPClient to talk to server.py
and call two of its tools.
"""

import asyncio
from client import MCPClient


async def main():
    # `async with` guarantees the server subprocess is started
    # before use and shut down cleanly afterwards.
    async with MCPClient("server.py") as client:

        # ---- Call tool 1: estimate_travel_time ----
        print("\n--- estimate_travel_time ---")
        result1 = await client.run_tool(
            "estimate_travel_time",
            distance_km=350,
            mode="car",
        )
        print(result1)

        # ---- Call tool 2: generate_packing_list ----
        print("\n--- generate_packing_list ---")
        result2 = await client.run_tool(
            "generate_packing_list",
            trip_type="hiking",
        )
        print(result2)


# Standard Python entry point.
if __name__ == "__main__":
    asyncio.run(main())
