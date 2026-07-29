"""
agent.py
------------------------------------------------------------
Microsoft Foundry agent that uses an MCP server as its tool backend.

Big picture:
  - The MCP server (server.py) exposes two tools.
  - The Foundry agent (LLM) decides which tool to call.
  - Our MCP client executes the tool call and returns the output.
  - The Foundry agent uses that output to finish its answer.

Keep this file paired with server.py and client.py in the same folder.
------------------------------------------------------------
"""

# =====================================
# STEP 1: Imports
# =====================================
import os
import json
import asyncio
from dotenv import load_dotenv

# Our own MCP client wrapper around server.py
from client import MCPClient

# Azure Foundry SDK
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FunctionTool, PromptAgentDefinition

# Types used to feed tool outputs back to the model
from openai.types.responses.response_input_param import (
    FunctionCallOutput,
    ResponseInputParam,
)


# =====================================
# STEP 2: Load Configuration
# =====================================

# Clear the console for a clean demo screen.
os.system("cls" if os.name == "nt" else "clear")

# Load values from the .env file (PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME).
load_dotenv()

# Read Azure AI Foundry project endpoint and model deployment name.
project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")


# =====================================
# STEP 3: Helper - convert MCP tools into Foundry FunctionTool definitions
# =====================================
def mcp_tools_to_function_tools(mcp_tools) -> list[FunctionTool]:
    """
    MCP servers advertise tools with a name, description and JSON schema.
    Foundry expects the same 3 things wrapped in FunctionTool.
    This helper bridges the two, so we do not hardcode tool metadata.
    """
    function_tools = []
    for t in mcp_tools:
        function_tools.append(
            FunctionTool(
                name=t.name,
                description=t.description or f"MCP tool: {t.name}",
                # inputSchema from MCP maps directly to parameters in Foundry.
                parameters=t.inputSchema or {"type": "object", "properties": {}},
            )
        )
    return function_tools


# =====================================
# STEP 4: Main async flow
# =====================================
async def main():
    # Load the sample user prompts we want the agent to answer.
    with open("user_prompt.json", "r") as f:
        prompts = json.load(f)

    # -------------------------------------------
    # Open the MCP client (this launches server.py)
    # -------------------------------------------
    async with MCPClient("server.py") as mcp_client:

        # ---- Step 4a: Discover MCP tools ----
        mcp_tool_list = await mcp_client.session.list_tools()
        mcp_tools = mcp_tool_list.tools
        print("\n[MCP] Tools discovered from server:")
        for t in mcp_tools:
            print(f"   - {t.name}: {t.description}")

        # ---- Step 4b: Convert them into Foundry FunctionTools ----
        foundry_tools = mcp_tools_to_function_tools(mcp_tools)

        # -------------------------------------------
        # Open Foundry connections in one 'with' block
        # -------------------------------------------
        with (
            DefaultAzureCredential() as credential,
            AIProjectClient(
                endpoint=project_endpoint,
                credential=credential,
            ) as project_client,
            project_client.get_openai_client() as openai_client,
        ):

            # =====================================
            # STEP 5: Create the Foundry agent
            # =====================================
            print("\n[Foundry] Creating agent 'travel-assistant' ...")
            agent = project_client.agents.create_version(
                agent_name="travel-assistant",
                definition=PromptAgentDefinition(
                    model=model_deployment,
                    instructions=(
                        "You are a helpful travel assistant. "
                        "Use the provided tools to answer the user. "
                        "Call estimate_travel_time for distance and mode questions. "
                        "Call generate_packing_list for packing questions. "
                        "Return a short, clear final answer."
                    ),
                    tools=foundry_tools,
                ),
            )
            print(f"[Foundry] Agent created: {agent.name} (v{agent.version})")

            # =====================================
            # STEP 6: Process each user prompt
            # =====================================
            for item in prompts:
                request_id = item["request_id"]
                user_prompt = item["user_prompt"]

                print("\n############################################")
                print(f" Request #{request_id}")
                print("############################################")
                print(f"[User] {user_prompt}")

                # Start a fresh input list for this conversation.
                # (Keep this list OUTSIDE the tool loop below so it
                # accumulates every message and every tool output.)
                input_list: ResponseInputParam = [
                    {"role": "user", "content": user_prompt}
                ]

                # =====================================
                # STEP 7: Multi-turn loop
                # Keep talking to the model until it stops
                # asking for tool calls and returns a final answer.
                # =====================================
                while True:
                    # Ask the agent to respond given the current conversation.
                    response = openai_client.responses.create(
                        input=input_list,
                        extra_body={
                            "agent_reference": {
                                "name": agent.name,
                                "type": "agent_reference",
                                "version": agent.version,
                            }
                        },
                    )

                    # Collect any tool calls the model requested.
                    tool_calls = [
                        o for o in response.output if o.type == "function_call"
                    ]

                    # If there are no tool calls, the model gave us the final answer.
                    if not tool_calls:
                        print(f"[Agent] {response.output_text}")
                        break

                    # -------------------------------------
                    # STEP 8: Handle every tool call in this turn
                    # -------------------------------------
                    for call in tool_calls:
                        tool_name = call.name
                        tool_args = json.loads(call.arguments)

                        print(f"\n[Agent -> Tool] {tool_name}({tool_args})")

                        # Route the tool call through the MCP client.
                        tool_result = await mcp_client.run_tool(
                            tool_name, **tool_args
                        )

                        print(f"[Tool -> Agent] {tool_result}")

                        # Append the model's own tool call to the history.
                        input_list.append(call)

                        # Append the tool output so the model can use it.
                        input_list.append(
                            FunctionCallOutput(
                                type="function_call_output",
                                call_id=call.call_id,
                                output=str(tool_result),
                            )
                        )

                    # Loop again: the model will now use the tool output
                    # to produce the final answer (or ask for another tool).

            # =====================================
            # STEP 10: Clean up the agent
            # =====================================
            print("\n[Foundry] Deleting agent ...")
            project_client.agents.delete_version(
                agent_name=agent.name,
                agent_version=agent.version,
            )
            print("[Foundry] Agent deleted.")


# Standard Python entry point.
if __name__ == "__main__":
    asyncio.run(main())
