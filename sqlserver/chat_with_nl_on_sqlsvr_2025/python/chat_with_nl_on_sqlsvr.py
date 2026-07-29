# application_caller.py
# End-to-end runner:
#   1. Bootstraps OpenTelemetry BEFORE any agent imports
#   2. Runs a chat loop calling the three-agent pipeline

import os
import sys
from dotenv import load_dotenv

# --- STEP 1: Load env and start tracing FIRST ---
load_dotenv()

import OpenTelemetryBootstrap as otel



OTLP_TRACES_ENDPOINT=os.getenv("OTLP_TRACES_ENDPOINT")
print(f"Access the OTEL portal here: {OTLP_TRACES_ENDPOINT}")


telemetry_cfg = otel.TelemetryConfig(
    service_name=os.getenv("OTLP_SERVICE_NAME"),
    service_version=os.getenv("OTLP_SERVICE_VERSION"),
    environment=os.getenv("OTLP_SERVICE_ENVIRONMENT"),
    otlp_endpoint=os.getenv("OTLP_SERVICE_ENDPOINT"),
)

telemetry = otel.OpenTelemetryBootstrap(telemetry_cfg)
telemetry.setup()   # <-- tracing is live from this point

# --- STEP 2: Import agents AFTER tracing is initialized ---
import AgentBootstrap


def main() -> int:
    """Interactive chat loop that calls the three-agent pipeline."""
    print("\n=== LangChain SQL Agent (type 'exit' to quit) ===\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input or user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        result = AgentBootstrap.run_three_agent_pipeline(user_input)

        print(f"\n[Classification] {result['classification']}")
        print(f"[SQL]            {result['sql']}")
        print(f"\n{result['final_answer']}\n")

    # Flush all pending spans before exit
    telemetry.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# Can you help me find the five best-sounding headsets?
# How many product categories do we have?
# Would you recommend that I buy the EchoBuds Pro? If so, tell me about customer feedback.
# Would you recommend the EchoBuds Pro? If yes, I would appreciate your feedback.