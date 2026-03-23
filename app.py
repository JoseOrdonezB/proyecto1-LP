from __future__ import annotations

import json
import traceback

import pandas as pd
import streamlit as st
import graphviz  # noqa: F401

from src.automata import (
    build_combined_nfa,
    dfa_to_dot,
    dfa_transition_table,
    minimize_dfa,
    nfa_to_dfa,
)
from src.parser_yalex import parse_yalex

st.set_page_config(page_title="Generador de Analizador Léxico", layout="wide")

st.title("🔎 Generador de Analizador Léxico")
st.caption(
    "Procesa un archivo YALex, construye el AFN por Thompson y lo convierte a AFD."
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
        token = getattr(state, "accepting_token", None)
        action = getattr(state, "accepting_action", None)
        if token is not None or action is not None:
            accepting.append(state_id)
    return accepting


archivo = st.file_uploader("Sube un archivo .yal o .txt", type=["yal", "txt"])
minimizar = st.checkbox("Minimizar AFD", value=True)

contenido = None
if archivo is not None:
    contenido = archivo.read().decode("utf-8")
    with st.expander("Ver contenido del archivo", expanded=False):
        st.code(contenido, language="ocaml")

if st.button("⚙️ Generar base del analizador"):
    if contenido is None:
        st.warning("Primero sube un archivo YALex.")
        st.stop()

    try:
        parsed = parse_yalex(contenido)

        if not parsed.lets:
            st.error("El archivo no contiene definiciones let.")
            st.stop()

        if not parsed.rule_cases:
            st.error("El archivo no contiene una sección rule válida.")
            st.stop()

        nfa = build_combined_nfa(parsed.rule_cases)
        dfa = nfa_to_dfa(nfa)

        if minimizar:
            dfa = minimize_dfa(dfa)

        tabla = dfa_transition_table(dfa)
        dot_source = dfa_to_dot(dfa)

        st.session_state["parsed"] = parsed
        st.session_state["dfa"] = dfa
        st.session_state["tabla"] = tabla
        st.session_state["dot_source"] = dot_source

        st.success("Archivo procesado correctamente.")

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")
        st.code(traceback.format_exc())

if "dfa" in st.session_state:
    parsed = st.session_state["parsed"]
    dfa = st.session_state["dfa"]
    tabla = st.session_state["tabla"]
    dot_source = st.session_state["dot_source"]

    accepting_states = get_accepting_states(dfa)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Resumen", "Definiciones y reglas", "Tabla AFD", "Grafo", "DOT"]
    )

    with tab1:
        st.subheader("Resumen del archivo")
        c1, c2, c3 = st.columns(3)
        c1.metric("Definiciones let", len(parsed.lets))
        c2.metric("Casos en rule", len(parsed.rule_cases))
        c3.metric("Estados AFD", len(dfa.states))

        st.markdown("### Regla principal")
        st.write(f"**Nombre:** {parsed.rule_name}")
        st.write(
            f"**Args:** {', '.join(parsed.rule_args) if parsed.rule_args else 'Sin argumentos'}"
        )

        st.markdown("### Estados de aceptación")
        st.write(accepting_states if accepting_states else ["Ninguno"])

        st.markdown("### Alfabeto")
        st.write(sorted([repr(symbol) for symbol in dfa.alphabet]))

        if parsed.header.strip():
            st.markdown("### Header")
            st.code(parsed.header)

        if parsed.trailer.strip():
            st.markdown("### Trailer")
            st.code(parsed.trailer)

    with tab2:
        st.subheader("Definiciones")
        defs_data = [
            {"Nombre": nombre, "Expresión": expr}
            for nombre, expr in parsed.lets.items()
        ]
        st.dataframe(pd.DataFrame(defs_data), use_container_width=True)

        st.subheader("Casos de la regla")
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

        with st.expander("Ver atributos reales de un RuleCase", expanded=False):
            if parsed.rule_cases:
                sample_case = parsed.rule_cases[0]
                attrs = {
                    attr: str(getattr(sample_case, attr))
                    for attr in dir(sample_case)
                    if not attr.startswith("_") and not callable(getattr(sample_case, attr))
                }
                st.json(attrs)

    with tab3:
        st.subheader("Tabla de transiciones del AFD")

        if isinstance(tabla, pd.DataFrame):
            st.dataframe(tabla, use_container_width=True)
        else:
            st.dataframe(pd.DataFrame(tabla), use_container_width=True)

        transitions_json = {}
        for state_id, state in dfa.states.items():
            for symbol, target in state.transitions.items():
                transitions_json[f"{state_id}::{symbol}"] = target

        afd_json = {
            "states": [str(state_id) for state_id in dfa.states.keys()],
            "alphabet": [str(symbol) for symbol in sorted(dfa.alphabet)],
            "transitions": transitions_json,
            "start_state": str(dfa.start_state),
            "accept_states": [str(state_id) for state_id in accepting_states],
        }

        st.download_button(
            label="⬇️ Descargar AFD en JSON",
            data=json.dumps(afd_json, indent=2, ensure_ascii=False),
            file_name="afd.json",
            mime="application/json",
        )

    with tab4:
        st.subheader("Grafo del AFD")
        st.graphviz_chart(dot_source, use_container_width=True)

    with tab5:
        st.subheader("Código DOT")
        st.code(dot_source, language="dot")