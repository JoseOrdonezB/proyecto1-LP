from __future__ import annotations

import json
import traceback

import pandas as pd
import streamlit as st
import graphviz  # noqa: F401

from src.codegen import generate_lexer_code  

from src.automata import (
    build_combined_nfa,
    dfa_to_dot,
    dfa_transition_table,
    minimize_dfa,
    nfa_to_dfa,
    build_dfa_from_single_regex  
)
from src.parser_yalex import parse_yalex

st.set_page_config(page_title="Generador de Analizador Léxico", layout="wide")

st.title("🔎 Generador de Analizador Léxico")
st.caption(
    "Procesa un archivo YALex, construye el AFN por Thompson o método directo y genera un lexer."
)


def get_case_regex(case) -> str:
    for attr in ["regex", "pattern", "expr", "raw_regex", "regex_src", "source"]:
        if hasattr(case, attr):
            value = getattr(case, attr)
            if value is not None:
                return str(value)
    return str(case)


def get_case_action(case) -> str:
    for attr in ["action_src", "action", "code", "raw_action"]:
        if hasattr(case, attr):
            value = getattr(case, attr)
            if value is not None:
                return str(value).strip()
    return ""


def get_accepting_states(dfa):
    accepting = []
    for state_id, state in dfa.states.items():
        if state.accepting_token is not None:
            accepting.append(state_id)
    return accepting



archivo = st.file_uploader("Sube un archivo .yal o .txt", type=["yal", "txt"])

minimizar = st.checkbox("Minimizar AFD", value=True)

modo_lab = st.checkbox(
    "Usar método directo (solo 1 regex)",
    value=False
)

contenido = None

if archivo is not None:
    contenido = archivo.read().decode("utf-8")

    with st.expander("Ver contenido del archivo"):
        st.code(contenido, language="ocaml")



if st.button("⚙️ Generar analizador"):

    if contenido is None:
        st.warning("Sube un archivo primero.")
        st.stop()

    try:
        parsed = parse_yalex(contenido)

        if not parsed.lets:
            st.warning("No hay definiciones let (esto es válido).")

        if not parsed.rule_cases:
            st.error("No hay reglas.")
            st.stop()


        if modo_lab and len(parsed.rule_cases) == 1:
            st.info("Modo AFD directo")
            regex = parsed.rule_cases[0].regex_src
            dfa = build_dfa_from_single_regex(regex)
        else:
            st.info("Modo estándar: Thompson + subset")

            nfa = build_combined_nfa(parsed.rule_cases)
            dfa = nfa_to_dfa(nfa)

            if minimizar:
                dfa = minimize_dfa(dfa)


        codigo_lexer = generate_lexer_code(dfa)


        tabla = dfa_transition_table(dfa)
        dot_source = dfa_to_dot(dfa)

        st.session_state["parsed"] = parsed
        st.session_state["dfa"] = dfa
        st.session_state["tabla"] = tabla
        st.session_state["dot"] = dot_source
        st.session_state["lexer_code"] = codigo_lexer

        st.success("Analizador generado correctamente.")

    except Exception as e:
        st.error(f"Error: {e}")
        st.code(traceback.format_exc())



if "dfa" in st.session_state:

    parsed = st.session_state["parsed"]
    dfa = st.session_state["dfa"]
    tabla = st.session_state["tabla"]
    dot = st.session_state["dot"]
    lexer_code = st.session_state["lexer_code"]

    accepting_states = get_accepting_states(dfa)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["Resumen", "Reglas", "Tabla AFD", "Grafo", "DOT", "Lexer generado"]
    )


    with tab1:
        st.subheader("Resumen")

        c1, c2, c3 = st.columns(3)
        c1.metric("lets", len(parsed.lets))
        c2.metric("reglas", len(parsed.rule_cases))
        c3.metric("estados", len(dfa.states))

        st.write("Estados de aceptación:", accepting_states)


    with tab2:
        st.subheader("Reglas")

        reglas_data = []
        for i, case in enumerate(parsed.rule_cases, start=1):
            reglas_data.append(
                {
                    "Prioridad": i,
                    "Regex": get_case_regex(case),
                    "Acción": get_case_action(case),
                }
            )

        st.dataframe(pd.DataFrame(reglas_data), use_container_width=True)

    with tab3:
        st.subheader("Tabla AFD")
        st.dataframe(pd.DataFrame(tabla), use_container_width=True)


    with tab4:
        st.subheader("Grafo")
        st.graphviz_chart(dot, use_container_width=True)


    with tab5:
        st.subheader("DOT")
        st.code(dot, language="dot")


    with tab6:
        st.subheader("Código del lexer generado")

        st.code(lexer_code, language="python")

        st.download_button(
            "⬇️ Descargar lexer.py",
            data=lexer_code,
            file_name="lexer.py"
        )