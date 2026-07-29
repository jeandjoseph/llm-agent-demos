"""
agent.py
------------------------------------------------------------
A very simple MCP agent demo.

Goal: show the audience, step by step, how an agent:
  1. Reads a user prompt in natural language
  2. Discovers tools from an MCP server
  3. Picks the right tool for the job (tool selection)
  4. Extracts the arguments it needs
  5. Calls the tool through MCP
  6. Prints the result

To keep the demo transparent, tool selection is done with a
tiny keyword rule (no LLM). This is exactly what an LLM would
do internally, just in plain Python so learners can see every
decision.
------------------------------------------------------------
"""

import asyncio
import json
import re
from client import MCPClient


# ============================================================
# Step 3 helper: pick a tool based on keywords in the prompt
# ============================================================
def select_tool(user_prompt: str, available_tools: list[str]) -> str | None:
    """Return the tool name that best matches the user's request."""

    # Lowercase once so keyword matching is case-insensitive.
    text = user_prompt.lower()

    # Rule 1: words that suggest a travel-time question.
    travel_keywords = ["travel", "fly", "flying", "drive", "train", "km", "distance"]
    if any(word in text for word in travel_keywords):
        if "estimate_travel_time" in available_tools:
            return "estimate_travel_time"

    # Rule 2: words that suggest a packing list request.
    packing_keywords = ["pack", "packing", "trip", "hiking", "beach", "business"]
    if any(word in text for word in packing_keywords):
        if "generate_packing_list" in available_tools:
            return "generate_packing_list"

    # No match found.
    return None


# ============================================================
# Step 4 helper: pull arguments out of the natural language prompt
# ============================================================
def extract_arguments(tool_name: str, user_prompt: str) -> dict:
    """Extract keyword arguments the chosen tool needs."""

    text = user_prompt.lower()

    # -------- Arguments for estimate_travel_time --------
    if tool_name == "estimate_travel_time":
        # Find a number followed by 'km' (e.g. "350 km", "1545 km").
        distance_match = re.search(r"(\d+(?:\.\d+)?)\s*km", text)
        distance_km = float(distance_match.group(1)) if distance_match else 100.0

        # Detect transportation mode from a small vocabulary.
        if "train" in text:
            mode = "train"
        elif "plane" in text or "fly" in text or "flying" in text:
            mode = "plane"
        else:
            mode = "car"

        return {"distance_km": distance_km, "mode": mode}

    # -------- Arguments for generate_packing_list --------
    if tool_name == "generate_packing_list":
        if "hiking" in text:
            trip_type = "hiking"
        elif "beach" in text:
            trip_type = "beach"
        else:
            trip_type = "business"

        return {"trip_type": trip_type}

    # Fallback: no known tool, so no arguments.
    return {}


# ============================================================
# Main loop: run the 6-step flow for every prompt in the file
# ============================================================
async def main():
    # Load the sample user prompts.
    with open("user_prompt.json", "r") as f:
        prompts = json.load(f)

    # Start the MCP client (this also launches server.py as a subprocess).
    async with MCPClient("server.py") as client:

        # Ask the server which tools it exposes.
        # This is what makes MCP powerful: the agent does not hardcode tools,
        # it discovers them at runtime.
        tool_list = await client.session.list_tools()
        available_tools = [t.name for t in tool_list.tools]

        print("\n============================================")
        print(" Tools discovered from MCP server:")
        for t in tool_list.tools:
            print(f"   - {t.name}: {t.description}")
        print("============================================\n")

        # Process each user prompt in turn.
        for item in prompts:
            request_id = item["request_id"]
            user_prompt = item["user_prompt"]

            print("############################################")
            print(f"Request #{request_id}")
            print("############################################")

            # ---- Step 1: show the raw user prompt ----
            print(f"\n[Step 1] User prompt:\n   \"{user_prompt}\"")

            # ---- Step 2: remind ourselves what tools exist ----
            print(f"\n[Step 2] Available tools on server: {available_tools}")

            # ---- Step 3: choose the right tool ----
            chosen_tool = select_tool(user_prompt, available_tools)
            print(f"\n[Step 3] Tool selected by agent: {chosen_tool}")

            # If no tool matches, skip this request gracefully.
            if chosen_tool is None:
                print("   No matching tool. Skipping.\n")
                continue

            # ---- Step 4: extract the arguments the tool needs ----
            args = extract_arguments(chosen_tool, user_prompt)
            print(f"\n[Step 4] Arguments extracted from prompt: {args}")

            # ---- Step 5: call the tool through MCP ----
            print(f"\n[Step 5] Calling MCP tool '{chosen_tool}' ...")
            result = await client.run_tool(chosen_tool, **args)

            # ---- Step 6: display the tool's response ----
            print(f"\n[Step 6] Tool result:\n   {result}\n")


# Standard Python entry point.
if __name__ == "__main__":
    asyncio.run(main())
