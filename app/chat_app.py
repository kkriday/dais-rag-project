import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from app.pipeline import answer_query

st.set_page_config(page_title="DAIS Chat", layout="wide")

# ── Document filter labels → doc_id (stem of chunk filenames)
DOC_OPTIONS = {
    "All Documents": None,
    "Home Depot ESG Report":  "2024_Home_Depot_ESG_Report_8.15.24.2_vF.2",
    "Lowe's Annual Report":   "Lowes_2024_Annual_Report_Website_compressed",
    "Mohawk Impact Report":   "Mohawk_2024_Impact_Report_compressed",
}

FRIENDLY = {v: k for k, v in DOC_OPTIONS.items() if v}


# ── Sidebar — document filter
with st.sidebar:
    st.header("Filter by Document")
    selected_label = st.selectbox("Show results from:", list(DOC_OPTIONS.keys()))
    doc_filter = DOC_OPTIONS[selected_label]
    if doc_filter:
        st.info(f"Retrieval restricted to **{selected_label}**")
    st.divider()
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

st.title("DAIS Chat-bot")

if "messages" not in st.session_state:
    st.session_state.messages = []



# ── Render chat history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m["role"] == "assistant" and m.get("sources"):
            with st.expander("Sources"):
                for src in m["sources"]:
                    doc_name = FRIENDLY.get(src.get("doc_id", ""), src.get("doc_id", ""))
                    page     = src.get("page", "?")
                    score    = src.get("score", 0.0)
                    chunk_id = src.get("chunk_id", "")
                    color = "🟢" if score >= 0.7 else ("🟡" if score >= 0.4 else "🔴")
                    st.markdown(f"**{doc_name}** · Page {page} {color}")
                    st.progress(min(float(score), 1.0))
                    st.caption(chunk_id)
                    st.divider()


def _split_questions(prompt: str) -> list[str]:
    """Split a prompt containing multiple numbered questions into individual questions."""
    import re
    parts = re.split(r'\n?\s*\d+\.\s+', prompt.strip())
    questions = [p.strip() for p in parts if p.strip()]
    return questions if len(questions) > 1 else [prompt.strip()]


def _handle_prompt(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    questions = _split_questions(prompt)
    all_sources = []

    with st.chat_message("assistant"):
        if len(questions) == 1:
            with st.spinner("Thinking…"):
                result = answer_query(prompt, doc_filter=doc_filter)
            answer = result["answer"]
            all_sources = result.get("sources", [])
            st.markdown(answer)
        else:
            combined_answer = "Here are the answers to your questions based on the provided documents:\n\n"
            for i, q in enumerate(questions, 1):
                with st.spinner(f"Answering question {i} of {len(questions)}…"):
                    result = answer_query(q, doc_filter=doc_filter)
                combined_answer += f"**{i}. {q}**\n\n{result['answer']}\n\n---\n\n"
                all_sources.extend(result.get("sources", []))
            answer = combined_answer
            st.markdown(answer)

        if all_sources:
            with st.expander("Sources"):
                for src in all_sources:
                    doc_name = FRIENDLY.get(src.get("doc_id", ""), src.get("doc_id", ""))
                    page     = src.get("page", "?")
                    score    = src.get("score", 0.0)
                    chunk_id = src.get("chunk_id", "")
                    color = "🟢" if score >= 0.7 else ("🟡" if score >= 0.4 else "🔴")
                    st.markdown(f"**{doc_name}** · Page {page} {color}")
                    st.progress(min(float(score), 1.0))
                    st.caption(chunk_id)
                    st.divider()

    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": all_sources})


# ── Handle typed input
prompt = st.chat_input("Ask a question about the documents...")
if prompt:
    _handle_prompt(prompt)
