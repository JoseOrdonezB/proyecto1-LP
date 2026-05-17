from __future__ import annotations

import streamlit as st

from src.codegen import generate_lexer_code
from src.codegen_parser import generate_parser_code
from src.automata import (
    build_combined_nfa,
    dfa_to_dot,
    dfa_transition_table,
    minimize_dfa,
    nfa_to_dfa,
)
from src.parser_yalex import parse_yalex
from src.syntax.parser_yapar import parse_yapar
from src.syntax.lr0 import build_lr0_automaton, build_parsing_table
from src.syntax.lexer_parser_bridge import LexerParserBridge, LexicalError
from src.syntax.visualizer import lr0_to_dot

# ─────────────────────────── CONFIG ────────────────────────────

st.set_page_config(page_title="YAPar", layout="wide")

# ─────────────────────────── ESTILOS ───────────────────────────

st.markdown("""
<style>
    .stApp { background-color: #1e1f26; color: #e5e7eb; }
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
        background-color: #4f8cff; color: white;
        border-radius: 6px; border: none;
    }
    .stButton>button:hover { background-color: #3b6fd8; }
    button[data-baseweb="tab"] { color: #9ca3af; }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
        border-bottom: 2px solid #4f8cff !important;
    }
    .console {
        background-color: #111318;
        border: 1px solid #2f3241;
        border-radius: 6px;
        padding: 12px;
        font-family: monospace;
        font-size: 13px;
        height: 260px;
        overflow-y: auto;
        white-space: pre-wrap;
    }
    .step-row  { margin: 2px 0; }
    .step-shift  { color: #60a5fa; }
    .step-reduce { color: #34d399; }
    .step-accept { color: #a3e635; font-weight: bold; }
    .step-error  { color: #f87171; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────── HELPER ────────────────────────────

def _step_css(action: str) -> str:
    return {
        "SHIFT":  "step-shift",
        "REDUCE": "step-reduce",
        "ACCEPT": "step-accept",
        "ERROR":  "step-error",
    }.get(action, "")


def _records_to_html(records: list) -> str:
    """Convierte lista de dicts a tabla HTML (sin pyarrow/pandas)."""
    if not records:
        return "<p style='color:#9ca3af'>Sin datos.</p>"
    headers = list(records[0].keys())
    th = "".join(f"<th style='padding:6px 12px;border:1px solid #2f3241;background:#252732'>{h}</th>" for h in headers)
    rows_html = ""
    for i, row in enumerate(records):
        bg = "#1a1b22" if i % 2 == 0 else "#1e1f26"
        tds = "".join(f"<td style='padding:5px 12px;border:1px solid #2f3241'>{row.get(h,'')}</td>" for h in headers)
        rows_html += f"<tr style='background:{bg}'>{tds}</tr>"
    return (
        "<div style='overflow-x:auto'>"
        "<table style='border-collapse:collapse;font-family:monospace;font-size:13px;width:100%'>"
        f"<thead><tr>{th}</tr></thead><tbody>{rows_html}</tbody>"
        "</table></div>"
    )

def _dfa_tabla_to_records(tabla) -> list:
    """Maneja tanto list como dict devueltos por dfa_transition_table."""
    if isinstance(tabla, list):
        return tabla
    if isinstance(tabla, dict):
        if not tabla:
            return []
        return [dict(zip(tabla.keys(), row)) for row in zip(*tabla.values())]
    return []


# ─────────────────────────── SIDEBAR ───────────────────────────

st.sidebar.title("Configuración")

yal_file  = st.sidebar.file_uploader("Archivo .yal  (Lexer)", type=["yal", "txt"])
yalp_file = st.sidebar.file_uploader("Archivo .yalp (Parser)", type=["yalp", "txt"])
minimizar = st.sidebar.checkbox("Minimizar AFD", True)

yal_src  = yal_file.read().decode("utf-8")  if yal_file  else ""
yalp_src = yalp_file.read().decode("utf-8") if yalp_file else ""

if st.sidebar.button("Generar analizadores"):
    errors = []

    # ── Lexer ──────────────────────────────────────────────────
    if yal_src:
        try:
            parsed = parse_yalex(yal_src)
            nfa    = build_combined_nfa(parsed.rule_cases)
            dfa    = nfa_to_dfa(nfa)
            if minimizar:
                dfa = minimize_dfa(dfa)
            st.session_state["dfa"]        = dfa
            st.session_state["dfa_dot"]    = dfa_to_dot(dfa)
            st.session_state["dfa_tabla"]  = dfa_transition_table(dfa)
            st.session_state["lexer_code"] = generate_lexer_code(dfa)
        except Exception as e:
            errors.append(f"Lexer: {e}")
    else:
        errors.append("Lexer: no se proporcionó archivo .yal")

    # ── Parser ─────────────────────────────────────────────────
    if yalp_src:
        try:
            grammar   = parse_yapar(yalp_src)
            automaton = build_lr0_automaton(grammar)
            table     = build_parsing_table(automaton)

            st.session_state["grammar"]     = grammar
            st.session_state["automaton"]   = automaton
            st.session_state["table"]       = table
            st.session_state["lr0_dot"]     = lr0_to_dot(automaton)
            st.session_state["parser_code"] = generate_parser_code(
                table,
                automaton.grammar,
                ignored_tokens=grammar.ignored_tokens,
                lexer_code=st.session_state.get("lexer_code", ""),
            )
            if table.conflicts:
                errors.append(
                    "Parser (advertencia LR(0)): "
                    + "; ".join(table.conflicts)
                )
        except Exception as e:
            errors.append(f"Parser: {e}")
    else:
        errors.append("Parser: no se proporcionó archivo .yalp")

    for err in errors:
        st.sidebar.warning(err)
    if not errors:
        st.sidebar.success("Analizadores generados ✓")

# ─────────────────────────── TABS ──────────────────────────────

tab_run, tab_lex_g, tab_lr0_g, tab_tabla, tab_lex_code, tab_par_code = st.tabs([
    "▶ Ejecutar",
    "AFD Léxico",
    "Autómata LR(0)",
    "Tabla AFD",
    "lexer.py",
    "parser.py",
])

# ══ TAB 1 ── EJECUTAR ══════════════════════════════════════════
with tab_run:
    st.subheader("Texto de entrada")
    input_text = st.text_area(
        "", height=180, key="editor",
        placeholder="Escribe o pega el texto a analizar…"
    )

    col_btn, _ = st.columns([1, 6])
    with col_btn:
        ejecutar = st.button("Analizar")

    if ejecutar:
        lexer_code = st.session_state.get("lexer_code")
        table      = st.session_state.get("table")
        grammar    = st.session_state.get("grammar")
        automaton  = st.session_state.get("automaton")

        if not lexer_code or table is None or grammar is None:
            st.warning("Primero genera los analizadores desde la barra lateral.")
        else:
            for k in ("run_tokens", "run_steps", "run_success",
                      "run_error_lex", "run_error_syn"):
                st.session_state.pop(k, None)

            bridge = LexerParserBridge(
                lexer_code=lexer_code,
                table=table,
                grammar=automaton.grammar,
                ignored_tokens=grammar.ignored_tokens,
            )
            try:
                tokens, result = bridge.run(input_text)
                st.session_state["run_tokens"]  = tokens
                st.session_state["run_steps"]   = result.steps
                st.session_state["run_success"] = result.success
                if not result.success:
                    st.session_state["run_error_syn"] = result.error_msg
            except LexicalError as le:
                st.session_state["run_error_lex"] = str(le)

    # Tokens table — lista de dicts, sin pandas
    if "run_tokens" in st.session_state:
        st.markdown("**Tokens generados por el lexer**")
        token_records = [
            {"Token": tok, "Lexema": lex}
            for tok, lex in st.session_state["run_tokens"]
        ]
        st.markdown(_records_to_html(token_records), unsafe_allow_html=True)

    # Console
    st.markdown("### Consola de análisis")
    console_html = ""

    if "run_error_lex" in st.session_state:
        err = st.session_state["run_error_lex"]
        console_html = f"<span class='step-error'>ERROR LÉXICO: {err}</span>"

    elif "run_steps" in st.session_state:
        lines = []
        for step in st.session_state["run_steps"]:
            css = _step_css(step.action)
            lines.append(
                f"<div class='step-row {css}'>"
                f"Paso {step.step_no:>3}  [{step.action:<8}]  {step.detail}"
                f"</div>"
            )
        if "run_error_syn" in st.session_state:
            lines.append(
                f"<div class='step-error'>▶ {st.session_state['run_error_syn']}</div>"
            )
        console_html = "\n".join(lines)

    else:
        console_html = (
            "<span style='color:#9ca3af'>"
            "Sin ejecución. Genera los analizadores y presiona Analizar."
            "</span>"
        )

    st.markdown(f"<div class='console'>{console_html}</div>", unsafe_allow_html=True)

# ══ TAB 2 ── AFD LÉXICO ════════════════════════════════════════
with tab_lex_g:
    if "dfa_dot" in st.session_state:
        st.graphviz_chart(st.session_state["dfa_dot"], use_container_width=True)
    else:
        st.info("Genera el analizador léxico para ver el autómata.")

# ══ TAB 3 ── AUTÓMATA LR(0) ════════════════════════════════════
with tab_lr0_g:
    if "lr0_dot" in st.session_state:
        st.graphviz_chart(st.session_state["lr0_dot"], use_container_width=True)
        if st.session_state.get("table") and st.session_state["table"].conflicts:
            st.warning("Conflictos LR(0): " + "; ".join(st.session_state["table"].conflicts))
    else:
        st.info("Genera el analizador sintáctico para ver el autómata LR(0).")

# ══ TAB 4 ── TABLA AFD ═════════════════════════════════════════
with tab_tabla:
    if "dfa_tabla" in st.session_state:
        # dfa_transition_table devuelve un dict {columna: [valores]}
        # lo convertimos a lista de dicts para st.dataframe sin pandas
        tabla = st.session_state["dfa_tabla"]
        records = _dfa_tabla_to_records(tabla)
        st.markdown(_records_to_html(records), unsafe_allow_html=True)
    else:
        st.info("Genera el analizador léxico para ver la tabla de transición.")

# ══ TAB 5 ── LEXER CODE ════════════════════════════════════════
with tab_lex_code:
    if "lexer_code" in st.session_state:
        st.code(st.session_state["lexer_code"], language="python")
        st.download_button(
            "⬇ Descargar lexer.py",
            data=st.session_state["lexer_code"],
            file_name="lexer.py",
            mime="text/plain",
        )
    else:
        st.info("Genera el analizador léxico para ver el código.")

# ══ TAB 6 ── PARSER CODE ═══════════════════════════════════════
with tab_par_code:
    if "parser_code" in st.session_state:
        st.code(st.session_state["parser_code"], language="python")
        st.download_button(
            "⬇ Descargar parser.py",
            data=st.session_state["parser_code"],
            file_name="theparser.py",
            mime="text/plain",
        )
    else:
        st.info("Genera el analizador sintáctico para ver el código.")