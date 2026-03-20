"""
agent_core.py
─────────────
Shared EDA agent logic used by both app.py (Streamlit) and cli.py.
Each agent is a function that calls Cohere and returns a string result.
"""

import io
import math
import cohere
import pandas as pd


# ── Cohere client factory ──────────────────────────────────────────
def get_client(api_key: str) -> cohere.Client:
    return cohere.Client(api_key)


# ── Data profiling (local, no API) ────────────────────────────────
def profile_dataframe(df: pd.DataFrame) -> dict:
    """Build a statistical profile from a DataFrame."""
    total_rows, total_cols = df.shape
    columns = []

    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        null_pct = round(null_count / total_rows * 100, 1)

        # Infer type
        try:
            numeric = pd.to_numeric(series, errors="coerce")
            if numeric.notna().sum() / len(series) > 0.85:
                col_type = "numeric"
            else:
                col_type = "categorical"
        except Exception:
            col_type = "categorical"

        # Compute stats
        if col_type == "numeric":
            n = numeric.dropna()
            q1, q3 = n.quantile(0.25), n.quantile(0.75)
            iqr = q3 - q1
            outliers = int(((n < q1 - 1.5 * iqr) | (n > q3 + 1.5 * iqr)).sum())
            stats = {
                "count": int(n.count()),
                "mean": round(float(n.mean()), 3),
                "median": round(float(n.median()), 3),
                "std": round(float(n.std()), 3),
                "min": round(float(n.min()), 3),
                "max": round(float(n.max()), 3),
                "q1": round(float(q1), 3),
                "q3": round(float(q3), 3),
                "iqr": round(float(iqr), 3),
                "outliers": outliers,
            }
        else:
            vc = series.dropna().value_counts()
            stats = {
                "unique": int(series.nunique()),
                "nulls": null_count,
                "top_values": [
                    {"value": str(k), "count": int(v)}
                    for k, v in vc.head(5).items()
                ],
            }

        columns.append({
            "name": col,
            "type": col_type,
            "null_count": null_count,
            "null_pct": null_pct,
            "stats": stats,
        })

    # Correlations
    numeric_df = df.select_dtypes(include="number")
    correlations = []
    if numeric_df.shape[1] >= 2:
        corr = numeric_df.corr()
        cols = list(corr.columns)
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                r = corr.iloc[i, j]
                if not math.isnan(r):
                    correlations.append({
                        "col1": cols[i],
                        "col2": cols[j],
                        "r": round(r, 3),
                    })
        correlations.sort(key=lambda x: abs(x["r"]), reverse=True)
        correlations = correlations[:12]

    return {
        "total_rows": total_rows,
        "total_cols": total_cols,
        "columns": columns,
        "correlations": correlations,
    }


# ── Individual agents ─────────────────────────────────────────────
def agent_profiler(client: cohere.Client, profile: dict, user_prompt: str = "") -> str:
    schema = [
        {"name": c["name"], "type": c["type"], "null_pct": f"{c['null_pct']}%"}
        for c in profile["columns"]
    ]
    message = (
        f"Dataset: {profile['total_rows']} rows × {profile['total_cols']} columns\n"
        f"Schema: {schema}\n\n"
        f"User focus: {user_prompt or 'General EDA'}\n\n"
        "Analyze data structure, column types, null distributions, and quality issues."
    )
    response = client.chat(
        model="command-r-08-2024",
        preamble=(
            "You are a data profiling agent. Analyze dataset structure and give a sharp, "
            "technical summary: schema quality, column types, null distributions, and concerns. "
            "Use bullet points. Be specific."
        ),
        message=message,
        max_tokens=600,
        temperature=0.3,
    )
    return response.text


def agent_statistician(client: cohere.Client, profile: dict, user_prompt: str = "") -> str:
    numeric_stats = [
        {"col": c["name"], **c["stats"]}
        for c in profile["columns"] if c["type"] == "numeric"
    ]
    cat_stats = [
        {"col": c["name"], "unique": c["stats"]["unique"], "top": c["stats"]["top_values"][:3]}
        for c in profile["columns"] if c["type"] == "categorical"
    ]
    message = (
        f"Numeric columns:\n{numeric_stats}\n\n"
        f"Categorical columns:\n{cat_stats}\n\n"
        f"User focus: {user_prompt or 'General EDA'}\n\n"
        "Provide a statistical interpretation of these distributions."
    )
    response = client.chat(
        model="command-r-08-2024",
        preamble=(
            "You are a statistical analysis agent. Interpret descriptive statistics — "
            "distributions, skewness, spread, and key numeric/categorical patterns. "
            "Be analytical and concise."
        ),
        message=message,
        max_tokens=600,
        temperature=0.3,
    )
    return response.text


def agent_pattern(client: cohere.Client, profile: dict, user_prompt: str = "") -> str:
    message = (
        f"Correlation matrix (Pearson r, top pairs):\n{profile['correlations']}\n\n"
        f"All columns: {[c['name'] for c in profile['columns']]}\n\n"
        f"User focus: {user_prompt or 'General EDA'}\n\n"
        "Analyze patterns, correlations, and relationships between variables."
    )
    response = client.chat(
        model="command-r-08-2024",
        preamble=(
            "You are a pattern detection agent. Interpret correlation coefficients — "
            "explain practical meaning, flag strong/weak relationships, and note "
            "potential multicollinearity or interesting interactions."
        ),
        message=message,
        max_tokens=500,
        temperature=0.3,
    )
    return response.text


def agent_anomaly(client: cohere.Client, profile: dict, user_prompt: str = "") -> str:
    outlier_info = [
        {
            "col": c["name"],
            "outliers": c["stats"]["outliers"],
            "iqr": c["stats"]["iqr"],
            "range": [c["stats"]["min"], c["stats"]["max"]],
            "pct": f"{round(c['stats']['outliers'] / profile['total_rows'] * 100, 1)}%",
        }
        for c in profile["columns"]
        if c["type"] == "numeric" and c["stats"].get("outliers", 0) > 0
    ] or [{"note": "No IQR outliers detected in numeric columns"}]

    message = (
        f"Outlier analysis (IQR method):\n{outlier_info}\n\n"
        f"Total rows: {profile['total_rows']}\n"
        f"User focus: {user_prompt or 'General EDA'}\n\n"
        "Flag data quality issues and assess the impact of outliers."
    )
    response = client.chat(
        model="command-r-08-2024",
        preamble=(
            "You are an anomaly detection agent. Analyze outlier data detected via the IQR method. "
            "Flag data quality issues, explain potential causes, and assess impact on modeling."
        ),
        message=message,
        max_tokens=500,
        temperature=0.3,
    )
    return response.text


def agent_synthesizer(
    client: cohere.Client,
    profiler_out: str,
    statistician_out: str,
    pattern_out: str,
    anomaly_out: str,
    user_prompt: str = "",
) -> str:
    message = (
        f"PROFILE AGENT:\n{profiler_out}\n\n"
        f"STATISTICS AGENT:\n{statistician_out}\n\n"
        f"PATTERN AGENT:\n{pattern_out}\n\n"
        f"ANOMALY AGENT:\n{anomaly_out}\n\n"
        f"User original focus: {user_prompt or 'General EDA'}\n\n"
        "Write the final EDA report."
    )
    response = client.chat(
        model="command-r-08-2024",
        preamble=(
            "You are a senior data scientist writing a final EDA report. "
            "Structure it as: 1) Executive Summary 2) Key Findings 3) Data Quality "
            "4) Feature Insights 5) Modeling Recommendations. Be concise and actionable."
        ),
        message=message,
        max_tokens=800,
        temperature=0.3,
    )
    return response.text


# ── Full pipeline ─────────────────────────────────────────────────
def run_pipeline(api_key: str, df: pd.DataFrame, user_prompt: str = "", on_step=None):
    """
    Run the full EDA agent pipeline.
    on_step(step_name, status, result) is called at each stage — useful for UI updates.
    Returns a dict of all agent outputs.
    """
    client = get_client(api_key)
    profile = profile_dataframe(df)
    results = {"profile": profile}

    steps = [
        ("profiler",     lambda: agent_profiler(client, profile, user_prompt)),
        ("statistician", lambda: agent_statistician(client, profile, user_prompt)),
        ("pattern",      lambda: agent_pattern(client, profile, user_prompt)),
        ("anomaly",      lambda: agent_anomaly(client, profile, user_prompt)),
    ]

    for name, fn in steps:
        if on_step:
            on_step(name, "running", None)
        result = fn()
        results[name] = result
        if on_step:
            on_step(name, "done", result)

    if on_step:
        on_step("synthesizer", "running", None)
    results["synthesizer"] = agent_synthesizer(
        client,
        results["profiler"],
        results["statistician"],
        results["pattern"],
        results["anomaly"],
        user_prompt,
    )
    if on_step:
        on_step("synthesizer", "done", results["synthesizer"])

    return results