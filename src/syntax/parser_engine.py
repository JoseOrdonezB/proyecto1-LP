"""
parser_engine.py
Motor shift/reduce que consume tokens de cualquier lexer compatible
y ejecuta el análisis sintáctico guiado por las tablas ACTION/GOTO.

Uso:
    engine = ParserEngine(table, grammar, ignored_tokens)
    result = engine.parse(token_stream)   # token_stream: iterable de (tipo, lexema)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator, List, Optional, Set, Tuple

from src.syntax.lr0 import EOF_SYMBOL, ParsingTable
from src.syntax.parser_yapar import Grammar



STEP_SHIFT   = "SHIFT"
STEP_REDUCE  = "REDUCE"
STEP_ACCEPT  = "ACCEPT"
STEP_ERROR   = "ERROR"


@dataclass
class ParseStep:
    """Registro de un paso del algoritmo shift/reduce."""
    step_no:    int
    stack:      str          # representación del stack de estados
    input_sym:  str          # símbolo actual de entrada
    action:     str          # SHIFT / REDUCE / ACCEPT / ERROR
    detail:     str          # descripción legible


@dataclass
class ParseResult:
    success:    bool
    steps:      List[ParseStep] = field(default_factory=list)
    error_msg:  Optional[str]   = None



class ParserEngine:
    """
    Implementa el algoritmo shift/reduce sobre las tablas ACTION/GOTO.

    Parameters
    ----------
    table          : ParsingTable generada por build_parsing_table()
    grammar        : Grammar (ya aumentada, tal como la usa la tabla)
    ignored_tokens : conjunto de nombres de token que el parser debe saltar
    on_step        : callback opcional (ParseStep) → None  (para UI en tiempo real)
    """

    def __init__(
        self,
        table: ParsingTable,
        grammar: Grammar,
        ignored_tokens: Set[str] | None = None,
        on_step: Optional[Callable[[ParseStep], None]] = None,
    ):
        self.table = table
        self.grammar = grammar
        self.ignored_tokens: Set[str] = ignored_tokens or set()
        self.on_step = on_step

    def parse(self, token_stream: Iterable[Tuple[str, str]]) -> ParseResult:
        """
        Ejecuta el análisis sintáctico completo.

        token_stream: iterable de (tipo_token, lexema)
                      Puede ser la salida de Lexer.tokenize() o un generador.
        """
        steps: List[ParseStep] = []
        step_no = 0

        # Filtrar tokens ignorados y añadir EOF al final
        tokens = self._filter_tokens(token_stream)
        token_iter = iter(tokens)

        # Stack de estados (solo números de estado)
        state_stack: List[int] = [0]
        # Stack paralelo de símbolos (para traza legible)
        symbol_stack: List[str] = ["$"]

        current_token: Optional[Tuple[str, str]] = self._advance(token_iter)

        while True:
            state = state_stack[-1]
            tok_type = current_token[0] if current_token else EOF_SYMBOL
            lexeme   = current_token[1] if current_token else ""

            action = self.table.action.get((state, tok_type))

            # ── Traza ──────────────────────────────────────────
            stack_repr   = " ".join(str(s) for s in state_stack)
            symbols_repr = " ".join(symbol_stack)
            step_no += 1

            if action is None:
                # Error sintáctico
                detail = (
                    f"No hay acción para estado {state} con token '{tok_type}'"
                    f" (lexema: '{lexeme}'). "
                    f"Tokens esperados: {self._expected_tokens(state)}"
                )
                step = ParseStep(
                    step_no=step_no,
                    stack=f"[{stack_repr}]  símbolos: [{symbols_repr}]",
                    input_sym=tok_type,
                    action=STEP_ERROR,
                    detail=detail,
                )
                steps.append(step)
                if self.on_step:
                    self.on_step(step)
                return ParseResult(
                    success=False,
                    steps=steps,
                    error_msg=f"Error sintáctico en '{lexeme}' ({tok_type}): {detail}",
                )

            # ── ACCEPT ─────────────────────────────────────────
            if action == "acc":
                step = ParseStep(
                    step_no=step_no,
                    stack=f"[{stack_repr}]  símbolos: [{symbols_repr}]",
                    input_sym=tok_type,
                    action=STEP_ACCEPT,
                    detail="Cadena aceptada ✓",
                )
                steps.append(step)
                if self.on_step:
                    self.on_step(step)
                return ParseResult(success=True, steps=steps)

            # ── SHIFT ──────────────────────────────────────────
            if action.startswith("s"):
                next_state = int(action[1:])
                step = ParseStep(
                    step_no=step_no,
                    stack=f"[{stack_repr}]  símbolos: [{symbols_repr}]",
                    input_sym=tok_type,
                    action=STEP_SHIFT,
                    detail=f"shift  →  estado {next_state}  ('{lexeme}')",
                )
                steps.append(step)
                if self.on_step:
                    self.on_step(step)

                state_stack.append(next_state)
                symbol_stack.append(tok_type)
                current_token = self._advance(token_iter)
                continue

            # ── REDUCE ─────────────────────────────────────────
            if action.startswith("r("):
                # Formato: r(left -> sym1 sym2 ...)
                rule_str = action[2:-1]          # strip r( and )
                left, rhs_str = rule_str.split("->", 1)
                left = left.strip()
                rhs  = rhs_str.strip().split()

                pop_count = len(rhs)

                # Producciones épsilon tienen rhs == ['ε']
                if rhs == ["ε"]:
                    pop_count = 0

                for _ in range(pop_count):
                    state_stack.pop()
                    symbol_stack.pop()

                # GOTO después de reducir
                top_state = state_stack[-1]
                goto_state = self.table.goto.get((top_state, left))

                if goto_state is None:
                    detail = (
                        f"GOTO indefinido para estado {top_state} "
                        f"con no-terminal '{left}'"
                    )
                    step = ParseStep(
                        step_no=step_no,
                        stack=f"[{stack_repr}]  símbolos: [{symbols_repr}]",
                        input_sym=tok_type,
                        action=STEP_ERROR,
                        detail=detail,
                    )
                    steps.append(step)
                    if self.on_step:
                        self.on_step(step)
                    return ParseResult(
                        success=False, steps=steps, error_msg=detail
                    )

                rhs_display = " ".join(rhs) if rhs != ["ε"] else "ε"
                step = ParseStep(
                    step_no=step_no,
                    stack=f"[{stack_repr}]  símbolos: [{symbols_repr}]",
                    input_sym=tok_type,
                    action=STEP_REDUCE,
                    detail=(
                        f"reduce  {left} → {rhs_display}  "
                        f"(pop {pop_count}, goto estado {goto_state})"
                    ),
                )
                steps.append(step)
                if self.on_step:
                    self.on_step(step)

                state_stack.append(goto_state)
                symbol_stack.append(left)
                continue

            # Acción desconocida (no debería ocurrir)
            return ParseResult(
                success=False,
                steps=steps,
                error_msg=f"Acción desconocida en tabla: '{action}'",
            )


    def _filter_tokens(
        self, stream: Iterable[Tuple[str, str]]
    ) -> List[Tuple[str, str]]:
        """Filtra tokens ignorados y añade (EOF_SYMBOL, '') al final."""
        result = []
        for tok_type, lexeme in stream:
            if tok_type not in self.ignored_tokens:
                result.append((tok_type, lexeme))
        result.append((EOF_SYMBOL, ""))
        return result

    @staticmethod
    def _advance(
        token_iter: Iterator[Tuple[str, str]]
    ) -> Optional[Tuple[str, str]]:
        return next(token_iter, None)

    def _expected_tokens(self, state: int) -> str:
        """Devuelve los tokens esperados en un estado (para mensajes de error)."""
        expected = [
            terminal
            for (s, terminal) in self.table.action
            if s == state
        ]
        return ", ".join(sorted(expected)) or "(ninguno)"
