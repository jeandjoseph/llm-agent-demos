import streamlit as st
import os
import atexit
from datetime import datetime
from dotenv import load_dotenv

# --- STEP 1: Load env and start tracing BEFORE any agent imports ---
load_dotenv()

import OpenTelemetryBootstrap as otel

telemetry_cfg = otel.TelemetryConfig(
    service_name="langchain-sql-demo",
    service_version="1.0.0",
    environment="local",
    otlp_endpoint=os.getenv("OTLP_ENDPOINT", "http://localhost:4318/v1/traces"),
)

telemetry = otel.OpenTelemetryBootstrap(telemetry_cfg)
telemetry.setup()   # tracing is live

# --- STEP 2: Import agents AFTER tracing is initialized ---
import AgentBootstrap


# ============================================================
# Streamlit UI Setup
# ============================================================

st.set_page_config(
    page_title="LangChain SQL Agent",
    page_icon="🧠",
    layout="wide",
)

# --- Custom CSS for a beautiful UI ---
st.markdown("""
<style>
.chat-container {
    max-width: 900px;
    margin-left: auto;
    margin-right: auto;
}
.user-msg {
    background-color: #DCF8C6;
    padding: 12px 16px;
    border-radius: 12px;
    margin-bottom: 10px;
    text-align: right;
    font-size: 1.05rem;
}
.agent-msg {
    background-color: #F1F0F0;
    padding: 12px 16px;
    border-radius: 12px;
    margin-bottom: 20px;
    text-align: left;
    font-size: 1.05rem;
}
.timestamp {
    font-size: 0.8rem;
    color: #777;
    margin-bottom: 4px;
    text-align: right;
}
.section-title {
    font-size: 1.2rem;
    font-weight: 600;
    margin-top: 15px;
}
</style>
""", unsafe_allow_html=True)

st.title("🧠 LangChain SQL Agent Demo")
st.caption("Powered by LangChain • SQL Server • OpenTelemetry")
st.markdown("---")

# ============================================================
# Session State for History
# ============================================================

if "history" not in st.session_state:
    st.session_state.history = []  # list of dicts: {user, classification, sql, answer, timestamp}

# Cache last query + result
@st.cache_data(show_spinner=False)
def run_cached_query(user_query: str):
    """Runs the pipeline and caches the result."""
    return AgentBootstrap.run_three_agent_pipeline(user_query)


# ============================================================
# Input Form
# ============================================================

with st.form("query_form", clear_on_submit=True):
    user_query = st.text_area(
        "Ask a question:",
        placeholder="e.g., Can you help me find the five best-sounding headsets?",
        height=100,
    )
    submitted = st.form_submit_button("Run Query 🚀")

# ============================================================
# Run Pipeline + Save History
# ============================================================

if submitted and user_query.strip():
    with st.spinner("Running the three-agent pipeline..."):
        result = run_cached_query(user_query.strip())

    # Save to history with timestamp
    st.session_state.history.append({
        "user": user_query,
        "classification": result["classification"],
        "sql": result["sql"],
        "answer": result["final_answer"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

# ============================================================
# Display Chat History (DESCENDING ORDER)
# ============================================================

st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

for entry in reversed(st.session_state.history):  # newest first
    # Timestamp
    st.markdown(
        f"<div class='timestamp'>{entry['timestamp']}</div>",
        unsafe_allow_html=True
    )

    # User bubble
    st.markdown(
        f"<div class='user-msg'>{entry['user']}</div>",
        unsafe_allow_html=True
    )

    # Agent bubble
    agent_html = f"""
    <div class='agent-msg'>
        <div class='section-title'>🔍 Classification</div>
        <pre>{entry['classification']}</pre>

        <div class='section-title'>🧩 SQL Generated</div>
        <pre>{entry['sql']}</pre>

        <div class='section-title'>💡 Final Answer</div>
        {entry['answer']}
    </div>
    """
    st.markdown(agent_html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption("Traces are being sent to your OpenTelemetry collector.")

# ============================================================
# Graceful Telemetry Shutdown
# ============================================================

@atexit.register
def shutdown_tracing():
    try:
        telemetry.shutdown()
    except Exception:
        pass
