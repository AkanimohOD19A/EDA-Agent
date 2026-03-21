# ⬡ EDA Agent Framework

> **Autonomous Exploratory Data Analysis powered by a multi-agent pipeline and Cohere's free-tier LLM.**
> Upload a CSV. Describe what you care about. Get a full, structured EDA report — no code required.

---
![0321(1).mp4](0321(1).mp4)
---
## Overview

EDA Agent is a lightweight multi-agent framework that automates the entire exploratory data analysis workflow. Instead of a single monolithic LLM prompt, it decomposes EDA into **five specialist agents** that run sequentially — each one building on the findings of the last — before a final agent synthesizes everything into a structured report.

The framework ships in three interfaces:

| Interface | File | Best for                                             |
|---|---|------------------------------------------------------|
| 🌐 Streamlit Web App | `app.py` | Sharing with non-technical users, deploying publicly |
| 💻 CLI Script | `cli.py` | Automation, pipelines, scripting                     |
| ⚡ React Widget | `eda_agent_framework.jsx` | Embedding in a web app or Claude artifact (WIP)      |

All three share a single core engine (`agent_core.py`) — one change propagates everywhere.

---

## Agent Pipeline

Each agent has a tightly scoped responsibility. Outputs are chained so each agent has richer context than the one before it.

```
CSV Upload
    │
    ▼
┌─────────────────────────────────────────────┐
│  LOCAL (no API call)                        │
│  · Type inference per column                │
│  · Null % calculation                       │
│  · Descriptive stats (mean, std, IQR, etc.) │
│  · Pearson correlation matrix               │
│  · IQR-based outlier detection              │
└──────────────────┬──────────────────────────┘
                   │ profile dict
                   ▼
         ┌─────────────────┐
         │ ◈ Data Profiler │  Schema quality, type breakdown, null distributions
         └────────┬────────┘
                  │
                  ▼
      ┌───────────────────────┐
      │ ∑ Statistical Analyst │  Distribution shape, skewness, spread, top categories
      └──────────┬────────────┘
                 │
                 ▼
       ┌──────────────────────┐
       │ ⊛ Pattern Detector   │  Correlation interpretation, multicollinearity flags
       └─────────┬────────────┘
                 │
                 ▼
        ┌─────────────────────┐
        │ ⚡ Anomaly Scout     │  Outlier analysis, data quality flags, modeling impact
        └────────┬────────────┘
                 │
                 ▼
       ┌──────────────────────┐
       │ ✦ Report Synthesizer │  Executive summary → findings → quality → recommendations
       └──────────────────────┘
                 │
                 ▼
           Full EDA Report
         (displayed + saved)
```

> **Why multi-agent?** A single LLM call given a full dataset profile produces generic output. Scoped agents stay focused, produce sharper analysis, and allow each stage to build on prior findings — the synthesizer reads all four upstream outputs before writing the final report.

---

## Quickstart

### 1. Clone or download the files

```
your_project/
├── agent_core.py
├── app.py
├── cli.py
└── requirements.txt
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Get a free Cohere API key

Sign up at [dashboard.cohere.com](https://dashboard.cohere.com) — no credit card required.  
The free trial tier includes **1,000 API calls/month** and access to `command-r-08-2024`.

---

## Usage

### 🌐 Streamlit Web App

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. From the sidebar:
1. Paste your Cohere API key
2. Upload a `.csv` file
3. Optionally type an analysis focus (e.g. *"focus on customer churn indicators"*)
4. Click **▶ Run EDA Pipeline**

Each agent's status updates live as the pipeline runs. Results appear in labelled tabs. A full report is available to download as `.txt`.

---

### 💻 CLI Script

```bash
# Minimal
python cli.py --csv data.csv --key co-xxxxxxxxxxxxxxxx

# With a user prompt for focused analysis
python cli.py --csv data.csv --key co-xxxx --prompt "focus on revenue drivers"

# Save report to a specific file
python cli.py --csv data.csv --key co-xxxx --out my_report.txt

# Quiet mode — only prints the final report (good for piping)
python cli.py --csv data.csv --key co-xxxx --quiet

# Use environment variable for the key (recommended for production)
export COHERE_API_KEY=co-xxxxxxxxxxxxxxxx
python cli.py --csv data.csv
```

**CLI flags:**

| Flag | Description | Required |
|---|---|---|
| `--csv` | Path to input CSV file | ✅ |
| `--key` | Cohere API key | ✅ (or env var) |
| `--prompt` | Optional analysis focus prompt | ❌ |
| `--out` | Output file path for the report | ❌ (auto-named if omitted) |
| `--quiet` | Suppress verbose output, print final report only | ❌ |

If `--out` is not provided, the report is auto-saved as `eda_report_YYYYMMDD_HHMMSS.txt`.

---

### 🔑 API Key — Environment Variable (Recommended)

Rather than passing your key as a flag every time, set it once:

```bash
# Mac / Linux
export COHERE_API_KEY=co-xxxxxxxxxxxxxxxx

# Windows (Command Prompt)
set COHERE_API_KEY=co-xxxxxxxxxxxxxxxx

# Windows (PowerShell)
$env:COHERE_API_KEY="co-xxxxxxxxxxxxxxxx"
```

For Streamlit Cloud deployment, add it as a **Secret** (see Deployment section below).

---

## What Gets Computed Locally vs. Sent to the API

To keep token usage minimal and avoid sending raw data rows to an external API, all statistical computation happens locally in Python:

| Computed locally | Sent to Cohere |
|---|---|
| Column type inference | Column names, types, null % |
| Null counts & percentages | Aggregated descriptive stats |
| Mean, median, std, min, max | Correlation pairs (top 12) |
| Q1, Q3, IQR, outlier counts | IQR outlier summaries |
| Pearson correlation matrix | Prior agents' text outputs |
| Top value frequencies | User's optional prompt |

**No raw rows are ever sent to the API.** Only summary statistics and agent text outputs are passed between steps.

---

## Report Structure

The final synthesized report follows this structure:

```
1. Executive Summary       — one-paragraph overview of the dataset
2. Key Findings            — most important patterns and signals
3. Data Quality Assessment — nulls, outliers, type issues, concerns
4. Feature Insights        — column-level highlights, distributions, correlations
5. Modeling Recommendations — suggested preprocessing steps, feature engineering, caveats
```

---

## Deploying Publicly (Free)

### Streamlit Community Cloud

The easiest way to give external users a shareable URL — no server, no Docker, no cost.

**Steps:**

1. Push your four files to a **public GitHub repository**
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click **New app** → select your repo → set `app.py` as the main file
4. Under **Advanced settings → Secrets**, add:
   ```toml
   COHERE_API_KEY = "co-xxxxxxxxxxxxxxxx"
   ```
   *(Optional — if you want to pre-fill the key. Otherwise users paste their own.)*
5. Click **Deploy**

Your app will be live at `https://yourname-eda-agent.streamlit.app` within ~2 minutes.

> **Recommended pattern for public sharing:** leave the API key field empty in the app — users bring their own Cohere key. This means zero API cost on your end regardless of how many people use it.

---

## Model

This framework uses **`command-r-08-2024`** — Cohere's current free-tier chat model, replacing the retired `command-r`.

| Model | Speed | Quality | Free tier |
|---|---|---|---|
| `command-r-08-2024` | Fast | Good | ✅ |
| `command-r-plus-08-2024` | Slower | Better reasoning | ✅ |

To switch models, change the `model=` value in each agent function inside `agent_core.py`:

```python
response = client.chat(
    model="command-r-plus-08-2024",  # ← swap here
    ...
)
```

---

## Extending the Framework

The pipeline is designed to be easy to extend. To add a new agent:

**1. Add an agent function to `agent_core.py`:**

```python
def agent_feature_engineer(client, profile, user_prompt=""):
    message = f"Columns: {[c['name'] for c in profile['columns']]}\n..."
    response = client.chat(
        model="command-r-08-2024",
        preamble="You are a feature engineering agent...",
        message=message,
        max_tokens=500,
        temperature=0.3,
    )
    return response.text
```

**2. Add it to the pipeline in `run_pipeline()`:**

```python
steps = [
    ("profiler",          lambda: agent_profiler(...)),
    ("statistician",      lambda: agent_statistician(...)),
    ("pattern",           lambda: agent_pattern(...)),
    ("anomaly",           lambda: agent_anomaly(...)),
    ("feature_engineer",  lambda: agent_feature_engineer(client, profile, user_prompt)),  # ← new
]
```

**3. Reference it in `app.py` tabs and `cli.py` sections** — both pick up from the results dict automatically.

---

## Requirements

```
cohere>=5.0.0
pandas>=2.0.0
streamlit>=1.35.0
```

Python **3.9+** recommended.

---

## Project Structure

```
eda_agent/
├── agent_core.py            # Core pipeline: stats engine + all agent functions
├── app.py                   # Streamlit web UI
├── cli.py                   # Command-line interface
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

---

## License

MIT — free to use, modify, and deploy.

---

*Built with [Cohere](https://cohere.com) · [Streamlit](https://streamlit.io) · Python*