from __future__ import annotations

import traceback
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

st.set_page_config(page_title="Generador de Analizador Léxico", layout="wide")

st.title("🔎 Generador de Analizador Léxico")
st.caption("Carga un archivo .yal, genera el DFA y prueba el lexer.")

# ---------------- UI ----------------

archivo = st.file_uploader("Sube un archivo .yal", type=["yal", "txt"])
minimizar = st.checkbox("Minimizar AFD", value=True)

contenido = None

if archivo:
    contenido = archivo.read().decode("utf-8")
    st.subheader("📄 Contenido del archivo")
    st.code(contenido, language="ocaml")

# ---------------- GENERAR ----------------

if st.button("⚙️ Generar analizador"):

    if not contenido:
        st.warning("Sube un archivo primero.")
        st.stop()

    try:
        parsed = parse_yalex(contenido)

        if not parsed.rule_cases:
            st.error("No hay reglas.")
            st.stop()

        # Pipeline completo
        nfa = build_combined_nfa(parsed.rule_cases)
        dfa = nfa_to_dfa(nfa)

        if minimizar:
            dfa = minimize_dfa(dfa)

        # Outputs
        tabla = dfa_transition_table(dfa)
        dot = dfa_to_dot(dfa)
        lexer_code = generate_lexer_code(dfa)

        # Guardar en sesión
        st.session_state["dfa"] = dfa
        st.session_state["tabla"] = tabla
        st.session_state["dot"] = dot
        st.session_state["lexer_code"] = lexer_code

        st.success("✔️ Analizador generado correctamente")

    except Exception as e:
        st.error(f"Error: {e}")
        st.code(traceback.format_exc())

# ---------------- MOSTRAR RESULTADOS ----------------

if "dfa" in st.session_state:

    tabla = st.session_state["tabla"]
    dot = st.session_state["dot"]
    lexer_code = st.session_state["lexer_code"]

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Tabla AFD", "Grafo", "Lexer generado", "Probar lexer"]
    )

    # -------- TABLA --------
    with tab1:
        st.subheader("Tabla de transiciones")
        st.dataframe(pd.DataFrame(tabla), use_container_width=True)

    # -------- GRAFO --------
    with tab2:
        st.subheader("Grafo del DFA")
        st.graphviz_chart(dot, use_container_width=True)

    # -------- LEXER --------
    with tab3:
        st.subheader("Código generado")
        st.code(lexer_code, language="python")

        st.download_button(
            "⬇️ Descargar lexer.py",
            data=lexer_code,
            file_name="lexer.py"
        )

    # -------- PROBAR LEXER --------
    with tab4:
        st.subheader("Probar analizador léxico")

        input_text = st.text_area("Texto de entrada")

        if st.button("▶️ Analizar"):

            try:
                # Ejecutar código dinámico
                local_env = {}
                exec(lexer_code, local_env)

                Lexer = local_env["Lexer"]
                lexer = Lexer(input_text)

                tokens = []

                while True:
                    token = lexer.next_token()
                    if token is None:
                        break
                    tokens.append(token)

                if tokens:
                    df = pd.DataFrame(tokens, columns=["Token", "Lexema"])
                    st.success("Tokens reconocidos:")
                    st.table(df)
                else:
                    st.info("No se generaron tokens")

            except Exception as e:
                st.error(f"Error léxico: {e}")