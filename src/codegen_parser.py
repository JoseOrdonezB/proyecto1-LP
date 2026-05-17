"""
codegen_parser.py
Genera el código fuente de un analizador sintáctico independiente en Python.

El archivo generado:
  - Contiene las tablas ACTION y GOTO embebidas como diccionarios.
  - Implementa el algoritmo shift/reduce completo.
  - Expone la clase `Parser` con el método `parse(token_stream)`.
  - Es completamente independiente del generador (no importa nada de src/).

Uso:
    from src.codegen_parser import generate_parser_code
    code = generate_parser_code(table, grammar, ignored_tokens, lexer_code)
    with open("theparser.py", "w") as f:
        f.write(code)
"""

from __future__ import annotations

from typing import Set

from src.syntax.lr0 import EOF_SYMBOL, ParsingTable
from src.syntax.parser_yapar import Grammar


def generate_parser_code(
    table: ParsingTable,
    grammar: Grammar,
    ignored_tokens: Set[str] | None = None,
    lexer_code: str = "",
) -> str:
    """
    Genera el código fuente Python de un parser independiente.

    Parameters
    ----------
    table          : ParsingTable con ACTION y GOTO
    grammar        : Grammar (aumentada) — se usa para comentarios
    ignored_tokens : tokens que el parser debe ignorar
    lexer_code     : código fuente del lexer generado (se incrusta al final)
    """
    ignored = ignored_tokens or set()

    action_repr = _dict_to_code(table.action, indent=4)
    goto_repr   = _dict_to_code(table.goto,   indent=4)
    ignored_repr = repr(ignored)

    productions_comment = "\n".join(
        f"    #   {p}" for p in grammar.productions
    )

    conflicts_section = ""
    if table.conflicts:
        conflict_lines = "\n".join(f"    #   {c}" for c in table.conflicts)
        conflicts_section = f"""
# ── Conflictos detectados ──────────────────────────────────────────────
{conflict_lines}
"""

    lexer_section = ""
    if lexer_code.strip():
        lexer_section = f"""
# ══════════════════════════════════════════════════════════════════════
#  LEXER GENERADO (independiente)
# ══════════════════════════════════════════════════════════════════════

{lexer_code}
"""

    code = f'''#!/usr/bin/env python3
"""
Parser generado automáticamente por YAPar.
Gramática de inicio: {grammar.start_symbol!r}

Producciones:
{productions_comment}
{conflicts_section}
Este archivo es autónomo: no depende del generador YAPar.
Para usarlo:

    # Con el lexer integrado:
    lexer  = Lexer(input_text)
    tokens = lexer.tokenize()

    parser = Parser()
    result = parser.parse(tokens)
    print(result)
"""

from __future__ import annotations
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

# ──────────────────────────────────────────────────────────────────────
#  Tablas ACTION / GOTO
# ──────────────────────────────────────────────────────────────────────

EOF_SYMBOL = {EOF_SYMBOL!r}

ACTION: Dict[Tuple[int, str], str] = {{
{action_repr}
}}

GOTO: Dict[Tuple[int, str], int] = {{
{goto_repr}
}}

IGNORED_TOKENS = {ignored_repr}

# ──────────────────────────────────────────────────────────────────────
#  Resultado del parser
# ──────────────────────────────────────────────────────────────────────

class ParseResult:
    def __init__(self, success: bool, steps: list, error_msg: str = ""):
        self.success   = success
        self.steps     = steps          # list of dict with step info
        self.error_msg = error_msg

    def __repr__(self) -> str:
        status = "ACEPTADO ✓" if self.success else f"RECHAZADO ✗  {{self.error_msg}}"
        return f"ParseResult({{status}}, {{len(self.steps)}} pasos)"

# ──────────────────────────────────────────────────────────────────────
#  Motor shift/reduce
# ──────────────────────────────────────────────────────────────────────

class Parser:
    """
    Analizador sintáctico LR(0) independiente.

    Uso:
        parser = Parser()
        result = parser.parse(token_stream)

    token_stream : iterable de (tipo_token: str, lexema: str)
    """

    def parse(
        self,
        token_stream: Iterable[Tuple[str, str]],
        verbose: bool = False,
    ) -> ParseResult:
        steps: list = []

        # Filtrar ignorados y añadir EOF
        tokens = self._prepare(token_stream)
        tok_iter: Iterator[Tuple[str, str]] = iter(tokens)

        state_stack:  List[int] = [0]
        symbol_stack: List[str] = ["$"]
        step_no = 0

        current = next(tok_iter, None)

        while True:
            state   = state_stack[-1]
            tok_type = current[0] if current else EOF_SYMBOL
            lexeme   = current[1] if current else ""

            action = ACTION.get((state, tok_type))

            step_no += 1
            stack_repr = " ".join(str(s) for s in state_stack)
            sym_repr   = " ".join(symbol_stack)

            # ── ERROR ──────────────────────────────────────────
            if action is None:
                expected = self._expected(state)
                detail = (
                    f"No hay acción para estado {{state}} "
                    f"con token '{{tok_type}}' (lexema: '{{lexeme}}'). "
                    f"Esperados: {{expected}}"
                )
                step = dict(
                    step_no=step_no,
                    stack=f"[{{stack_repr}}] [{{sym_repr}}]",
                    input=tok_type,
                    action="ERROR",
                    detail=detail,
                )
                steps.append(step)
                if verbose:
                    print(f"Paso {{step_no:>3}}  ERROR  {{detail}}")
                return ParseResult(False, steps, detail)

            # ── ACCEPT ─────────────────────────────────────────
            if action == "acc":
                step = dict(
                    step_no=step_no,
                    stack=f"[{{stack_repr}}] [{{sym_repr}}]",
                    input=tok_type,
                    action="ACCEPT",
                    detail="Cadena aceptada ✓",
                )
                steps.append(step)
                if verbose:
                    print(f"Paso {{step_no:>3}}  ACCEPT")
                return ParseResult(True, steps)

            # ── SHIFT ──────────────────────────────────────────
            if action.startswith("s"):
                next_state = int(action[1:])
                step = dict(
                    step_no=step_no,
                    stack=f"[{{stack_repr}}] [{{sym_repr}}]",
                    input=tok_type,
                    action="SHIFT",
                    detail=f"shift → estado {{next_state}}  ('{{lexeme}}')",
                )
                steps.append(step)
                if verbose:
                    print(f"Paso {{step_no:>3}}  SHIFT   {{tok_type}} → estado {{next_state}}")
                state_stack.append(next_state)
                symbol_stack.append(tok_type)
                current = next(tok_iter, None)
                continue

            # ── REDUCE ─────────────────────────────────────────
            if action.startswith("r("):
                rule_str = action[2:-1]
                left, rhs_str = rule_str.split("->", 1)
                left = left.strip()
                rhs  = rhs_str.strip().split()

                pop_count = 0 if rhs == ["\\u03b5"] else len(rhs)

                for _ in range(pop_count):
                    state_stack.pop()
                    symbol_stack.pop()

                top = state_stack[-1]
                goto_state = GOTO.get((top, left))

                if goto_state is None:
                    detail = f"GOTO indefinido para estado {{top}} con '{{left}}'"
                    step = dict(
                        step_no=step_no,
                        stack=f"[{{stack_repr}}] [{{sym_repr}}]",
                        input=tok_type,
                        action="ERROR",
                        detail=detail,
                    )
                    steps.append(step)
                    return ParseResult(False, steps, detail)

                rhs_disp = " ".join(rhs) if rhs != ["\\u03b5"] else "\\u03b5"
                step = dict(
                    step_no=step_no,
                    stack=f"[{{stack_repr}}] [{{sym_repr}}]",
                    input=tok_type,
                    action="REDUCE",
                    detail=f"reduce {{left}} → {{rhs_disp}}  (pop {{pop_count}}, goto {{goto_state}})",
                )
                steps.append(step)
                if verbose:
                    print(f"Paso {{step_no:>3}}  REDUCE  {{left}} → {{rhs_disp}}")
                state_stack.append(goto_state)
                symbol_stack.append(left)
                continue

            # Acción desconocida
            return ParseResult(False, steps, f"Acción desconocida: '{{action}}'")

    # ----------------------------------------------------------
    @staticmethod
    def _prepare(
        stream: Iterable[Tuple[str, str]]
    ) -> List[Tuple[str, str]]:
        result = [
            (tok, lex)
            for tok, lex in stream
            if tok not in IGNORED_TOKENS
        ]
        result.append((EOF_SYMBOL, ""))
        return result

    @staticmethod
    def _expected(state: int) -> str:
        return ", ".join(
            sorted(t for (s, t) in ACTION if s == state)
        ) or "(ninguno)"


# ──────────────────────────────────────────────────────────────────────
#  Punto de entrada (demo)
# ──────────────────────────────────────────────────────────────────────

def main():
    import sys

    if len(sys.argv) < 2:
        print("Uso: python theparser.py <archivo_entrada.txt>")
        sys.exit(1)

    input_path = sys.argv[1]
    with open(input_path, encoding="utf-8") as f:
        text = f.read()

    # Tokenizar con el lexer embebido
    try:
        lexer  = Lexer(text)          # noqa: F821  (definida abajo)
        tokens = lexer.tokenize()
    except Exception as exc:
        print(f"Error léxico: {{exc}}")
        sys.exit(2)

    print("Tokens:")
    for tok, lex in tokens:
        print(f"  {{tok:<20}} {{lex!r}}")

    print()
    parser = Parser()
    result = parser.parse(tokens, verbose=True)
    print()
    print(result)

    if not result.success:
        sys.exit(3)


if __name__ == "__main__":
    main()
{lexer_section}
'''
    return code



def _dict_to_code(d: dict, indent: int = 4) -> str:
    """Convierte un dict a una representación de código Python indentada."""
    if not d:
        return ""
    pad = " " * indent
    lines = []
    for k, v in sorted(d.items(), key=lambda x: (str(x[0][0]), str(x[0][1]))):
        lines.append(f"{pad}{k!r}: {v!r},")
    return "\n".join(lines)
