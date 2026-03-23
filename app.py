from __future__ import annotations

import pandas as pd
import streamlit as st

from src.codegen import generate_lexer_code
from src.automata import (
    build_combined_nfa,
    dfa_to_dot,
    dfa_transition_table,
    minimize_dfa,
    nfa_to_dfa,
)
from src.parser_yalex import parse_yalex

# ---------------- CONFIG ----------------

st.set_page_config(layout="wide")

# ---------------- ESTILOS ----------------

st.markdown("""
<style>
    .stApp {
        background-color: #1e1f26;
        color: #e5e7eb;
    }

    section[data-testid="stSidebar"] {
        background-color: #252732;
        border-right: 1px solid #2f3241;
    }

    textarea {
        background-color: #1e1f26 !important;
        color: #e5e7eb !important;
        border: 1px solid #2f3241 !important;
        border-radius: 6px;
        font-family: monospace;
    }

    .stButton>button {
        background-color: #4f8cff;
        color: white;
        border-radius: 6px;
        border: none;
    }

    .stButton>button:hover {
        background-color: #3b6fd8;
    }

    /* Tabs - un solo color */
    button[data-baseweb="tab"] {
        color: #9ca3af;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
        border-bottom: 2px solid #4f8cff !important;
    }

    /* Consola */
    .console {
        background-color: #111318;
        border: 1px solid #2f3241;
        border-radius: 6px;
        padding: 12px;
        font-family: monospace;
        font-size: 13px;
        height: 200px;
        overflow-y: auto;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------

st.sidebar.title("Configuración")

archivo = st.sidebar.file_uploader("Archivo .yal", type=["yal", "txt"])
minimizar = st.sidebar.checkbox("Minimizar AFD", True)

contenido = ""
if archivo:
    contenido = archivo.read().decode("utf-8")

if st.sidebar.button("Generar analizador"):
    try:
        parsed = parse_yalex(contenido)

        nfa = build_combined_nfa(parsed.rule_cases)
        dfa = nfa_to_dfa(nfa)

        if minimizar:
            dfa = minimize_dfa(dfa)

        st.session_state["dfa"] = dfa
        st.session_state["dot"] = dfa_to_dot(dfa)
        st.session_state["tabla"] = dfa_transition_table(dfa)
        st.session_state["lexer_code"] = generate_lexer_code(dfa)

        st.sidebar.success("Generado correctamente")

    except Exception as e:
        st.sidebar.error(str(e))

# ---------------- MAIN LAYOUT ----------------

col_main = st.container()

with col_main:

    # -------- TABS SUPERIORES --------
    tab_editor, tab_grafo, tab_tabla, tab_codigo = st.tabs([
        "input.txt",
        "automata.png",
        "automata.xlsx",
        "lexer.py"
    ])

    # -------- EDITOR --------
    with tab_editor:

        input_text = st.text_area(
            "",
            height=300,
            key="editor"
        )

        col_btn1, col_btn2 = st.columns([1, 6])

        with col_btn1:
            ejecutar = st.button("Ejecutar")

        if ejecutar:
            try:
                local_env = {}
                exec(st.session_state["lexer_code"], local_env)

                Lexer = local_env["Lexer"]
                lexer = Lexer(input_text)

                tokens = []

                while True:
                    token = lexer.next_token()
                    if token is None:
                        break
                    tokens.append(token)

                st.session_state["output"] = tokens
                st.session_state["error"] = None

            except Exception as e:
                st.session_state["error"] = str(e)
                st.session_state["output"] = None

    # -------- GRAFO --------
    with tab_grafo:
        if "dot" in st.session_state:
            st.graphviz_chart(st.session_state["dot"], use_container_width=True)

    # -------- TABLA --------
    with tab_tabla:
        if "tabla" in st.session_state:
            st.dataframe(pd.DataFrame(st.session_state["tabla"]), use_container_width=True)

    # -------- CODIGO --------
    with tab_codigo:
        if "lexer_code" in st.session_state:
            st.code(st.session_state["lexer_code"], language="python")

# ---------------- CONSOLA INFERIOR ----------------

st.markdown("### Consola")

console_content = ""

if "error" in st.session_state and st.session_state["error"]:
    console_content = f"<span style='color:#ff6b6b'>{st.session_state['error']}</span>"

elif "output" in st.session_state and st.session_state["output"]:
    lines = []
    for token, lexema in st.session_state["output"]:
        lines.append(f"<span style='color:#22c55e'>{token}</span>  →  {lexema}")
    console_content = "<br>".join(lines)

else:
    console_content = "<span style='color:#9ca3af'>Sin ejecución</span>"

st.markdown(
    f"<div class='console'>{console_content}</div>",
    unsafe_allow_html=True
)