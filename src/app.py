import sys
import os
import random
import io
import streamlit as st
import pandas as pd
import time
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from streamlit_local_storage import LocalStorage
try:
    import plotly.express as px
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="QueryMate · AI SQL Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "**QueryMate** — Ask your database in plain English, powered by Gemini AI."},
)

load_dotenv()

# Custom CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

.app-header {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 55%, #9333ea 100%);
    padding: 1rem 2.4rem 1.4rem; border-radius: 16px; margin-bottom: 1.4rem;
    box-shadow: 0 8px 32px rgba(99,102,241,0.35);
}
.app-header h1 { color:#fff; font-size:2rem; font-weight:700; margin:0; letter-spacing:-0.5px; }
.app-header p  { color:rgba(255,255,255,0.82); margin:0.35rem 0; font-size:0.96rem; }

.welcome-box { text-align:center; padding:3rem 2rem; color:#6b7280; }
.welcome-box h2 { font-size:1.6rem; margin-bottom:0.1rem; }
.welcome-box code { background:#1e2130; padding:2px 9px; border-radius:6px; color:#a5b4fc; font-size:0.86rem; }

.hist-chip { padding:5px 9px; border-radius:8px; margin-bottom:3px; font-size:0.78rem; line-height:1.4; border-left:3px solid; }
</style>
""", unsafe_allow_html=True)

# Backend Imports 
try:
    from llm_query import (
        generate_sql, logging as log_query,
        add_to_conversation, clear_conversation as backend_clear,
    )
    from vector_store import collection, store_successful_query, check_duplication, get_collection_count
    from utilities import validate_sql, get_engine, detect_chart_type
    BACKEND_READY = True
    BACKEND_ERROR = None
except Exception as _exc:
    BACKEND_READY = False
    BACKEND_ERROR = str(_exc)

# Session State
localS = LocalStorage()

def _init_state():
    qm_messages = localS.getItem("qm_messages")
    qm_conv_log = localS.getItem("qm_conv_log")

    defaults = {
        "messages": qm_messages if isinstance(qm_messages, list) else [],
        "conv_log": qm_conv_log if isinstance(qm_conv_log, list) else [],
        "n_queries": 0,
        "n_success": 0,
        "n_failed": 0,
        "n_rag": 0,
        "total_examples": 0,
        "times_ms": [],
        "started": datetime.now().strftime("%H:%M"),
        # Settings
        "show_charts": True,
        "store_memory": True,
        "row_limit": 10,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# Helper
def _clear_all():
    for k in ("messages", "conv_log", "times_ms"):
        st.session_state[k] = []
    for k in ("n_queries", "n_success", "n_failed", "n_rag", "total_examples"):
        st.session_state[k] = 0
        
    localS.deleteItem("qm_messages", key="del_msgs")
    localS.deleteItem("qm_conv_log", key="del_log")
    
    if BACKEND_READY:
        backend_clear()

# Visualization 
_PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(15,17,23,0.6)",
    font=dict(color="#e2e8f0", family="Inter"),
    margin=dict(t=50, r=20, b=50, l=20),
    xaxis=dict(gridcolor="#2d3154"),
    yaxis=dict(gridcolor="#2d3154"),
)
_ACCENT = "#6366f1"

def render_chart(df: pd.DataFrame, chart_type: str, config: dict):
    """Render Plotly chart; falls back gracefully if plotly not installed."""

    if chart_type == "metric":
        val   = df.iloc[0, 0]
        label = df.columns[0].replace("_", " ").title()
        fmt   = f"{val:,.0f}" if isinstance(val, float) and val == int(val) else (
                f"{val:,.2f}" if isinstance(val, float) else str(val))
        st.metric(label=label, value=fmt)
        return

    if chart_type == "bar":
        fig = px.bar(df, x=config["x"], y=config["y"],
                     title=config.get("title",""), color_discrete_sequence=[_ACCENT])

    elif chart_type == "hbar":
        df_s = df.sort_values(config["x"], ascending=True)
        fig  = px.bar(df_s, x=config["x"], y=config["y"], orientation="h",
                      title=config.get("title",""), color_discrete_sequence=[_ACCENT])

    elif chart_type == "line":
        fig = px.line(df, x=config["x"], y=config["y"], markers=True,
                      title=config.get("title",""), color_discrete_sequence=[_ACCENT])
        fig.update_traces(line_width=2.5)
    else:
        return

    fig.update_layout(**_PLOTLY_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)


# Process Pipeline
load_messages = [
    "🤖 Processing your question…",
    "🧠 Consulting the database oracle…",
    "✨ Calculating the numbers…",
    "🔮 AI Thinking…",
]


def _process(question: str) -> dict:
    result = {
        "sql": None, "df": None, "status": None, "error": None,
        "retrieved_count": 0, "rag_used": False,
        "exec_ms": 0, "rows": 0, "stored": False,
        "chart_type": "none", "chart_config": {},
    }

    with st.status(random.choice(load_messages), expanded=True) as sw:
        # 1. Generate SQL
        st.write("🔍 Searching memory for similar examples…")
        sql, examples, log = generate_sql(question)
        result["retrieved_count"] = log.get("retrieved_count", 0)
        result["rag_used"] = log.get("rag_used", False)

        st.write(
            f"✅ Found {result['retrieved_count']} example(s)"
            if result["retrieved_count"] else "📖 No cached examples — using static few-shots"
        )

        if sql is None:
            result["status"] = "failed"
            result["error"] = log.get("error", "LLM failed to generate SQL")
            sw.update(label="❌ SQL generation failed", state="error")
            return result

        result["sql"] = sql
        st.write("✨ SQL generated successfully")

        # 2. Validate
        valid, err = validate_sql(sql)
        if not valid:
            result.update(status="failed", error=err)
            log["status"] = "failed"; log["error"] = err; log_query(log)
            sw.update(label="❌ SQL validation failed", state="error")
            return result

        # 3. Execute
        st.write("⚡ Running query against the database…")
        try:
            engine = get_engine()
            with engine.connect() as conn:
                t0 = time.time()
                conn.execute(text("SET statement_timeout = '5s'"))
                df = pd.read_sql(text(sql), conn)
                exec_ms = round((time.time() - t0) * 1000, 2)

            result.update(df=df, rows=len(df), exec_ms=exec_ms, status="success")
            log["status"] = "success"; log_query(log)
            add_to_conversation(question, sql, len(df))

            # 4. Store unique
            if st.session_state.store_memory and check_duplication(sql, examples):
                store_successful_query(question, sql, len(df), exec_ms)
                result["stored"] = True

            # 5. Detect chart
            ct, cc = detect_chart_type(df, sql)
            result["chart_type"]   = ct
            result["chart_config"] = cc

            sw.update(label=f"✅ Done — {len(df)} row(s) returned", state="complete")

        except Exception as exc:
            es = str(exc)
            msg = (
                "Query timed out (>5s). Try adding date filters or LIMIT."
                if "statement timeout" in es else
                f"Schema error: {es}" if "does not exist" in es.lower() else
                f"Execution error: {es}"
            )
            result.update(status="failed", error=msg)
            log["status"] = "failed"; log["error"] = msg; log_query(log)
            sw.update(label="❌ Query execution failed", state="error")

    return result


# Render Assistant Bubble
def _render_assistant_msg(msg: dict):
    if msg["status"] == "success":
        if msg.get("sql"):
            with st.expander("📝 View Generated SQL", expanded=False):
                st.code(msg["sql"], language="sql")

        df = msg.get("df")
        chart_type = msg.get("chart_type", "none")
        chart_config = msg.get("chart_config", {})

        if df is not None and not df.empty:
            df_disp = df.head(st.session_state.row_limit)
            st.success(f"✅ {msg['rows']} row(s) returned"
                       + (f"  *(showing first {st.session_state.row_limit})*"
                          if len(df) > st.session_state.row_limit else ""))

            if st.session_state.show_charts and chart_type not in ("none", "table"):
                tab_chart, tab_table = st.tabs(["📊 Chart", "📋 Table"])
                with tab_chart:
                    render_chart(df_disp, chart_type, chart_config)
                with tab_table:
                    st.dataframe(df_disp, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_disp, use_container_width=True, hide_index=True)

            ts = datetime.now().strftime("%Y%m%d_%H%M")
            key_base = str(msg.get("exec_ms", id(msg)))
            _, e1, _ = st.columns([3, 3, 3])

            e1.download_button(
                "📥 CSV", df.to_csv(index=False),
                file_name=f"querymate_{ts}.csv", mime="text/csv",
                use_container_width=True, key=f"csv_{key_base}",
            )

        elif df is not None:
            st.warning("⚠️ Query ran successfully but returned no results.")

    else:
        st.error(f"❌ {msg.get('error', 'Something went wrong.')}")
        if msg.get("sql"):
            with st.expander("📝 Generated SQL (failed)", expanded=False):
                st.code(msg["sql"], language="sql")
        st.info("💡 Try rephrasing or be more specific about the table/column you need.")


# Sidebar
with st.sidebar:
    st.markdown("### 🤖 QueryMate")
    st.caption("Natural Language → SQL")
    st.divider()

    st.markdown("**⚙️ Controls**")
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        _clear_all()
        st.rerun()

    st.divider()

    # Session stats
    st.markdown("**📊 Session Stats**")
    n, ok = st.session_state.n_queries, st.session_state.n_success
    rate  = f"{round(ok/n*100)}%" if n else "—"
    avg_t = (f"{round(sum(st.session_state.times_ms)/len(st.session_state.times_ms)/1000,1)}s"
             if st.session_state.times_ms else "—")
    rag_r = f"{round(st.session_state.n_rag/n*100)}%" if n else "—"

    c1, c2 = st.columns(2)
    c1.metric("Queries", n);     
    c2.metric("Success", rate)
    c1.metric("RAG Usage", rag_r); 
    c2.metric("Avg Time", avg_t)
    st.divider()


    # History
    entries = st.session_state.conv_log
    if entries:
        st.markdown(f"**💬 History ({len(entries)} turns)**")
        for i, e in enumerate(entries[-5:], 1):
            ok_e = e["status"] == "success"
            color = "#10b981" if ok_e else "#ef4444"
            bg = "rgba(16,185,129,0.08)" if ok_e else "rgba(239,68,68,0.08)"
            q_s = e["question"][:34] + "…" if len(e["question"]) > 34 else e["question"]
            st.markdown(
                f"<div class='hist-chip' style='border-color:{color};background:{bg};'>"
                f"{'✅' if ok_e else '❌'} <b>Q{i}</b> {q_s}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No queries yet — start asking!")

    st.divider()

    with st.expander("❓ Help & Examples"):
        st.markdown("""
            **How to use:**
            - Type a question, press **Enter**
            - Click suggestion chips for follow-ups
            - Type `clear` to reset

            **Try these:**
            - `How many customers are there?`
            - `Top 5 product categories by orders`
            - `Total revenue in 2024`
            - `Orders per month in 2024`
            - `Customers from São Paulo`
            - `Orders with 5-star reviews`
        """)


    st.caption(f"Session started {st.session_state.started}")


# Main Area
st.markdown("""
<div class="app-header">
  <h1>🤖 QueryMate</h1>
  <p>Ask e-commerce database anything in plain English — powered by Gemini AI</p>
</div>
""", unsafe_allow_html=True)

if not BACKEND_READY:
    st.error(f"⚠️ Backend failed to load: `{BACKEND_ERROR}`")
    st.info("Run from project root: `streamlit run src/app.py`")
    st.stop()



# Chat display
if not st.session_state.messages:
    st.markdown("""
        <div class="welcome-box">
            <h2>Welcome to QueryMate!</h2>
            <p>Ask any question about the e-commerce database below.</p><br>
            <p>
                Try: <code>How many customers are there?</code> &nbsp;·&nbsp;
                <code>Top 5 product categories</code> &nbsp;·&nbsp;
                <code>Revenue by state</code>
            </p>
        </div>
    """, unsafe_allow_html=True)
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
            if msg["role"] == "user":
                st.markdown(f"**{msg['content']}**")
            else:
                _render_assistant_msg(msg)


# Input
if user_input := st.chat_input("Ask anything about your data…"):
    question = user_input.strip()
else:
    question = None

if question:
    if question.lower() in {"clear", "reset", "new", "start over"}:
        _clear_all(); 
        st.rerun()
    else:
        st.session_state.messages.append({"role": "user", "content": question})
        res = _process(question)

        st.session_state.n_queries += 1
        if res["status"] == "success": 
            st.session_state.n_success += 1
        else:                          
            st.session_state.n_failed  += 1
        if res["rag_used"]:            
            st.session_state.n_rag     += 1
        st.session_state.total_examples += res.get("retrieved_count", 0)
        if res.get("exec_ms"):         
            st.session_state.times_ms.append(res["exec_ms"])

        st.session_state.conv_log.append({
            "question": question,
            "sql": res.get("sql"),
            "status": res.get("status"),
            "rows": res.get("rows", 0),
            "ms": res.get("exec_ms", 0),
            "ts": datetime.now().strftime("%H:%M"),
        })
        st.session_state.messages.append({"role": "assistant", **res})
        
        localS.setItem("qm_messages", st.session_state.messages, key="set_messages")
        localS.setItem("qm_conv_log", st.session_state.conv_log, key="set_conv")
        
        st.rerun()
