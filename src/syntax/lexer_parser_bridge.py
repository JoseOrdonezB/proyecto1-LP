"""
lexer_parser_bridge.py
Integración entre el lexer generado (src/codegen.py) y el motor
shift/reduce (src/syntax/parser_engine.py).

Dado:
  - El código fuente generado del lexer (string Python ejecutable)
  - La tabla de parsing + gramática
  - El texto de entrada a analizar

Ejecuta el análisis léxico + sintáctico y retorna el resultado completo.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Set, Tuple

from src.syntax.lr0 import ParsingTable
from src.syntax.parser_engine import ParseResult, ParseStep, ParserEngine
from src.syntax.parser_yapar import Grammar


class LexicalError(Exception):
    pass


class LexerParserBridge:
    """
    Une el lexer generado con el motor sintáctico.

    Parameters
    ----------
    lexer_code     : código Python del lexer generado por codegen.py
    table          : ParsingTable (ACTION/GOTO)
    grammar        : Grammar (aumentada)
    ignored_tokens : tokens a ignorar durante el parsing (p.ej. WS)
    on_step        : callback por cada paso del parser (para UI en vivo)
    """

    def __init__(
        self,
        lexer_code: str,
        table: ParsingTable,
        grammar: Grammar,
        ignored_tokens: Set[str] | None = None,
        on_step: Optional[Callable[[ParseStep], None]] = None,
    ):
        self.lexer_code     = lexer_code
        self.table          = table
        self.grammar        = grammar
        self.ignored_tokens = ignored_tokens or set()
        self.on_step        = on_step

    def run(self, input_text: str) -> Tuple[List[Tuple[str, str]], ParseResult]:
        """
        Ejecuta el flujo completo sobre input_text.

        Returns
        -------
        (tokens, result)
            tokens : lista de (tipo, lexema) producida por el lexer
            result : ParseResult del análisis sintáctico
        """
        tokens = self._tokenize(input_text)
        engine = ParserEngine(
            table=self.table,
            grammar=self.grammar,
            ignored_tokens=self.ignored_tokens,
            on_step=self.on_step,
        )
        result = engine.parse(iter(tokens))
        return tokens, result

    def _tokenize(self, text: str) -> List[Tuple[str, str]]:
        """
        Ejecuta el lexer generado en un namespace aislado y devuelve
        la lista de tokens.  Convierte excepciones del lexer en LexicalError.
        """
        local_env: dict = {}
        try:
            exec(self.lexer_code, local_env)  # noqa: S102
        except Exception as exc:
            raise LexicalError(f"Error al cargar el lexer generado: {exc}") from exc

        Lexer = local_env.get("Lexer")
        if Lexer is None:
            raise LexicalError("El código del lexer no define la clase 'Lexer'.")

        try:
            lexer = Lexer(text)
            return lexer.tokenize()
        except Exception as exc:
            raise LexicalError(str(exc)) from exc
