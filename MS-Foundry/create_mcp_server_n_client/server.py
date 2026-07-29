"""
server.py
A minimal MCP server built with FastMCP (the high-level MCP API).
It exposes two simple tools an agent/client can call.
"""

from mcp.server.fastmcp import FastMCP

# Create the MCP server instance and give it a friendly name.
# The name shows up when a client lists servers/tools.
mcp = FastMCP("TravelAgent")


# ------------------------------------------------------------
# Tool 1: Estimate travel time
# ------------------------------------------------------------
# The @mcp.tool() decorator turns this normal Python function
# into an MCP tool that the client can discover and call.
@mcp.tool()
def estimate_travel_time(distance_km: float, mode: str) -> str:
    """Estimate travel time (in hours) for a distance and transport mode."""

    # Average speeds in km/h for each supported mode.
    speeds = {
        "car": 80,
        "train": 120,
        "plane": 800,
    }

    # Guard clause: reject unknown modes early with a friendly message.
    if mode not in speeds:
        return f"Unknown mode '{mode}'. Try one of: {', '.join(speeds)}."

    # Basic physics: time = distance / speed.
    hours = distance_km / speeds[mode]

    # Return a human-readable string; MCP will wrap it as TextContent.
    return f"Estimated travel time by {mode} for {distance_km} km: {hours:.2f} hours."


# ------------------------------------------------------------
# Tool 2: Generate a packing list
# ------------------------------------------------------------
@mcp.tool()
def generate_packing_list(trip_type: str) -> list[str]:
    """Return a packing list based on the type of trip."""

    # Predefined packing lists keyed by trip type.
    lists = {
        "beach":    ["swimsuit", "sunscreen", "towel", "sandals"],
        "business": ["laptop", "charger", "formal wear", "notebook"],
        "hiking":   ["boots", "water bottle", "map", "first aid kit"],
    }

    # Return the list if we know the trip type, otherwise a fallback message.
    return lists.get(
        trip_type,
        [f"No packing list found for trip type '{trip_type}'."],
    )


# ------------------------------------------------------------
# Entry point: start the MCP server over stdio.
# ------------------------------------------------------------
# `transport="stdio"` means the server talks to the client
# through standard input/output (perfect for local demos).
if __name__ == "__main__":
    mcp.run(transport="stdio")
