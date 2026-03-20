"""
app.py  —  EDA Agent · Streamlit UI
────────────────────────────────────
Run locally :  streamlit run app.py
Deploy free :  push to GitHub → connect at share.streamlit.io
"""

import io
import streamlit as st
import pandas as pd
from agent_core import run_pipeline, profile_dataframe

# ── Page config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="EDA Agent",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    code, pre, .stCode { font-family: 'IBM Plex Mono', monospace !important; }
    .agent-box {
        background: #0d1225; border: 1px solid #1e2a4a;
        border-radius: 8px; padding: 16px 20px; margin-bottom: 12px;
    }
    .agent-box h4 { margin: 0 0 8px 0; font-family: 'IBM Plex Mono', monospace; }
    .metric-row { display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 16px; }
    .metric-card {
        background: #0a0e1c; border: 1px solid #1a2040;
        border-radius: 6px; padding: 10px 18px; text-align: center; min-width: 100px;
    }
    .metric-val { font-size: 22px; font-weight: 700; font-family: 'IBM Plex Mono', monospace; }
    .metric-lbl { font-size: 10px; color: #4a6080; letter-spacing: 1px; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⬡ EDA Agent")
    st.markdown("*Multi-step autonomous analysis powered by Cohere*")
    st.divider()

    api_key = st.text_input(
        "Cohere API Key",
        type="password",
        placeholder="paste your key here...",
        help="Free key at dashboard.cohere.com",
    )

    st.markdown("**Upload Dataset**")
    uploaded = st.file_uploader("Choose a CSV file", type=["csv"])

    user_prompt = st.text_area(
        "Analysis focus (optional)",
        placeholder="e.g. Focus on customer churn indicators and revenue drivers",
        height=90,
    )

    run_btn = st.button("▶ Run EDA Pipeline", use_container_width=True, type="primary")

    st.divider()
    st.markdown("""
**Agent Pipeline**
1. ◈ Data Profiler
2. ∑ Statistical Analyst
3. ⊛ Pattern Detector
4. ⚡ Anomaly Scout
5. ✦ Report Synthesizer
    """)
    st.divider()
    st.caption("Deploy free → [share.streamlit.io](https://share.streamlit.io)")


# ── Main area ──────────────────────────────────────────────────────
st.title("Exploratory Data Analysis Agent")
st.caption("Upload a CSV, optionally describe what to focus on, then run the pipeline.")

if not uploaded:
    st.info("👈 Upload a CSV file from the sidebar to get started.")
    st.stop()

# Load and preview
df = pd.read_csv(uploaded)
st.markdown(f"**{uploaded.name}** — `{df.shape[0]:,}` rows × `{df.shape[1]}` columns")

with st.expander("Preview data (first 5 rows)", expanded=False):
    st.dataframe(df.head(), use_container_width=True)

# Profile (always shown, computed locally)
profile = profile_dataframe(df)

# Schema table
st.markdown("### Column Schema")
schema_rows = []
for c in profile["columns"]:
    s = c["stats"]
    if c["type"] == "numeric":
        key_stat = f"mean={s['mean']}, std={s['std']}, outliers={s['outliers']}"
    else:
        key_stat = f"{s['unique']} unique values"
    schema_rows.append({
        "Column": c["name"],
        "Type": c["type"],
        "Null %": f"{c['null_pct']}%",
        "Key Stat": key_stat,
    })
st.dataframe(schema_rows, use_container_width=True, hide_index=True)

# Correlations
if profile["correlations"]:
    with st.expander("Top Correlations (Pearson r)", expanded=False):
        corr_rows = [
            {"Column A": r["col1"], "Column B": r["col2"], "r": r["r"]}
            for r in profile["correlations"]
        ]
        st.dataframe(corr_rows, use_container_width=True, hide_index=True)

st.divider()

# ── Run pipeline ───────────────────────────────────────────────────
if run_btn:
    if not api_key:
        st.error("⚠ Enter your Cohere API key in the sidebar.")
        st.stop()

    st.markdown("### Agent Pipeline — Running")

    # Status placeholders for each agent
    AGENTS = [
        ("profiler",     "◈ Data Profiler"),
        ("statistician", "∑ Statistical Analyst"),
        ("pattern",      "⊛ Pattern Detector"),
        ("anomaly",      "⚡ Anomaly Scout"),
        ("synthesizer",  "✦ Report Synthesizer"),
    ]

    placeholders = {}
    for agent_id, label in AGENTS:
        placeholders[agent_id] = st.empty()
        placeholders[agent_id].info(f"**{label}** — waiting...")

    results = {}
    progress = st.progress(0)
    step_count = len(AGENTS)

    def on_step(name, status, result):
        label = dict(AGENTS)[name]
        if status == "running":
            placeholders[name].warning(f"**{label}** — 🔄 running...")
        elif status == "done":
            placeholders[name].success(f"**{label}** — ✓ complete")
            results[name] = result
            done = sum(1 for a, _ in AGENTS if a in results)
            progress.progress(done / step_count)

    try:
        all_results = run_pipeline(api_key, df, user_prompt, on_step=on_step)
        progress.progress(1.0)
        st.session_state["results"] = all_results
        st.session_state["ran"] = True
    except Exception as e:
        st.error(f"Pipeline error: {e}")
        st.stop()

# ── Show results ───────────────────────────────────────────────────
if st.session_state.get("ran"):
    r = st.session_state["results"]
    st.divider()
    st.markdown("### Analysis Results")

    tab_labels = ["◈ Profiler", "∑ Statistician", "⊛ Patterns", "⚡ Anomalies", "✦ Final Report"]
    tabs = st.tabs(tab_labels)
    result_keys = ["profiler", "statistician", "pattern", "anomaly", "synthesizer"]

    for tab, key in zip(tabs, result_keys):
        with tab:
            if key in r:
                st.markdown(r[key])
            else:
                st.info("No result yet.")

    # Download report
    st.divider()
    report_text = "\n\n".join([
        f"# EDA REPORT\n\n",
        f"## 1. Data Profile\n{r.get('profiler','')}",
        f"## 2. Statistical Analysis\n{r.get('statistician','')}",
        f"## 3. Pattern Detection\n{r.get('pattern','')}",
        f"## 4. Anomaly Detection\n{r.get('anomaly','')}",
        f"## 5. Final Report\n{r.get('synthesizer','')}",
    ])
    st.download_button(
        "⬇ Download Full Report (.txt)",
        data=report_text,
        file_name="eda_report.txt",
        mime="text/plain",
    )
