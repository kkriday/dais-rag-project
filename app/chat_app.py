import sys
from pathlib import Path

# Add project root to Python path so `import app...` works under Streamlit
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from app.pipeline import answer_query

st.set_page_config(page_title="DAIS Chat", layout="wide")
st.title("DAIS Chat (M03 Prototype)")

if "messages" not in st.session_state:
    st.session_state.messages = []

# render history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input("Ask a question about the documents...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    result = answer_query(prompt)
    answer = result["answer"]
    sources = result.get("sources", [])

    with st.chat_message("assistant"):
        st.markdown(answer)
        if sources:
            with st.expander("Sources"):
                st.json(sources)

    st.session_state.messages.append({"role": "assistant", "content": answer})
