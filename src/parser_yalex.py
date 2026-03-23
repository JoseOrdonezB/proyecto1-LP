from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import copy

# ============================================================
# AST de expresiones regulares
# ============================================================

class RegexNode:
    pass


@dataclass
class EmptyNode(RegexNode):
    pass


@dataclass
class LiteralNode(RegexNode):
    value: str


@dataclass
class CharSetNode(RegexNode):
    chars: Set[str]


@dataclass
class ConcatNode(RegexNode):
    left: RegexNode
    right: RegexNode


@dataclass
class UnionNode(RegexNode):
    left: RegexNode
    right: RegexNode


@dataclass
class StarNode(RegexNode):
    child: RegexNode


@dataclass
class PlusNode(RegexNode):
    child: RegexNode


@dataclass
class OptionalNode(RegexNode):
    child: RegexNode


# ============================================================
# Estructuras del archivo YALex
# ============================================================

@dataclass
class RuleCase:
    regex_src: str
    action_src: str
    ast: Optional[RegexNode] = None
    priority: int = 0


@dataclass
class YALexSpec:
    raw_source: str
    clean_source: str
    header: str = ""
    trailer: str = ""
    lets: Dict[str, str] = field(default_factory=dict)
    lets_ast: Dict[str, RegexNode] = field(default_factory=dict)
    rule_name: str = "tokens"
    rule_args: List[str] = field(default_factory=list)
    rule_cases: List[RuleCase] = field(default_factory=list)


# ============================================================
# Utilidades base
# ============================================================

ASCII_UNIVERSE: Set[str] = {chr(i) for i in range(32, 127)}
ASCII_UNIVERSE.update({"\n", "\t", "\r"})


class YALexError(Exception):
    pass


ESCAPE_MAP = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "s": " ",
    "\\": "\\",
    "'": "'",
    '"': '"',
}


def decode_escaped(text: str) -> str:
    result: List[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            i += 1
            esc = text[i]
            result.append(ESCAPE_MAP.get(esc, esc))
        else:
            result.append(ch)
        i += 1
    return "".join(result)


def strip_comments(text: str) -> str:
    result: List[str] = []
    i = 0
    depth = 0
    while i < len(text):
        if i + 1 < len(text) and text[i:i+2] == "(*":
            depth += 1
            i += 2
            continue
        if depth > 0 and i + 1 < len(text) and text[i:i+2] == "*)":
            depth -= 1
            i += 2
            continue
        if depth == 0:
            result.append(text[i])
        i += 1
    if depth != 0:
        raise YALexError("Comentario sin cerrar con '*)'.")
    return "".join(result)


def skip_ws(text: str, i: int) -> int:
    while i < len(text) and text[i].isspace():
        i += 1
    return i


# ============================================================
# Parser de regex para YALex
# ============================================================

class RegexParser:
    def __init__(self, text: str, definitions: Dict[str, RegexNode] | None = None):
        self.text = text.strip()
        self.i = 0
        self.definitions = definitions or {}

    def parse(self) -> RegexNode:
        node = self.parse_union()
        self.i = self.skip_local_ws(self.i)
        if self.i != len(self.text):
            raise YALexError(f"Sobra texto en regex: {self.text[self.i:]}")
        return node

    def skip_local_ws(self, i: int) -> int:
        while i < len(self.text) and self.text[i].isspace():
            i += 1
        return i

    def parse_union(self) -> RegexNode:
        node = self.parse_concat()
        while True:
            self.i = self.skip_local_ws(self.i)
            if self.i < len(self.text) and self.text[self.i] == "|":
                self.i += 1
                rhs = self.parse_concat()
                node = UnionNode(node, rhs)
            else:
                break
        return node

    def parse_concat(self) -> RegexNode:
        parts: List[RegexNode] = []
        while True:
            self.i = self.skip_local_ws(self.i)
            if self.i >= len(self.text) or self.text[self.i] in ")|":
                break
            parts.append(self.parse_postfix())

        if not parts:
            raise YALexError("Concatenación vacía inválida")

        node = parts[0]
        for nxt in parts[1:]:
            node = ConcatNode(node, nxt)
        return node

    def parse_postfix(self) -> RegexNode:
        node = self.parse_primary()
        while True:
            self.i = self.skip_local_ws(self.i)
            if self.i >= len(self.text):
                break
            ch = self.text[self.i]
            if ch == "*":
                self.i += 1
                node = StarNode(node)
            elif ch == "+":
                self.i += 1
                node = PlusNode(node)
            elif ch == "?":
                self.i += 1
                node = OptionalNode(node)
            else:
                break
        return node

    def parse_primary(self) -> RegexNode:
        self.i = self.skip_local_ws(self.i)
        if self.i >= len(self.text):
            raise YALexError("Expresión inesperadamente vacía")

        ch = self.text[self.i]

        if ch == "(":
            self.i += 1
            node = self.parse_union()
            if self.i >= len(self.text) or self.text[self.i] != ")":
                raise YALexError("Falta ')'")
            self.i += 1
            return node

        if ch == "_":
            self.i += 1
            return CharSetNode(set(ASCII_UNIVERSE) - {"\n"})

        # FIX EOF seguro
        if self.text.startswith("eof", self.i) and (
            self.i + 3 == len(self.text) or not self.text[self.i + 3].isalnum()
        ):
            self.i += 3
            return LiteralNode("<<EOF>>")

        if ch == "'":
            return LiteralNode(self.read_single_quoted())

        if ch == '"':
            return self.string_to_concat(self.read_double_quoted())

        if ch == "[":
            return self.parse_charset_expr()

        if ch.isalpha() or ch == "_":
            ident = self.read_identifier()
            if ident not in self.definitions:
                raise YALexError(f"Identificador no definido: {ident}")
            return copy.deepcopy(self.definitions[ident])  # FIX CRÍTICO

        raise YALexError(f"Símbolo inválido: {ch}")

    def read_identifier(self) -> str:
        start = self.i
        while self.i < len(self.text) and (
            self.text[self.i].isalnum() or self.text[self.i] == "_"
        ):
            self.i += 1
        return self.text[start:self.i]

    def read_single_quoted(self) -> str:
        self.i += 1
        value = []
        while self.i < len(self.text):
            ch = self.text[self.i]
            if ch == "\\" and self.i + 1 < len(self.text):
                value.append("\\" + self.text[self.i + 1])
                self.i += 2
                continue
            if ch == "'":
                self.i += 1
                decoded = decode_escaped("".join(value))
                if len(decoded) != 1:
                    raise YALexError("Literal inválido")
                return decoded
            value.append(ch)
            self.i += 1
        raise YALexError("Literal sin cerrar")

    def read_double_quoted(self) -> str:
        self.i += 1
        value = []
        while self.i < len(self.text):
            ch = self.text[self.i]
            if ch == "\\" and self.i + 1 < len(self.text):
                value.append("\\" + self.text[self.i + 1])
                self.i += 2
                continue
            if ch == '"':
                self.i += 1
                return decode_escaped("".join(value))
            value.append(ch)
            self.i += 1
        raise YALexError("String sin cerrar")

    def string_to_concat(self, text: str) -> RegexNode:
        nodes = [LiteralNode(ch) for ch in text]
        node = nodes[0]
        for nxt in nodes[1:]:
            node = ConcatNode(node, nxt)
        return node

    def parse_charset_expr(self) -> RegexNode:
        left = self.parse_charset()
        self.i = self.skip_local_ws(self.i)
        if self.i < len(self.text) and self.text[self.i] == "#":
            self.i += 1
            right = self.parse_charset()
            result = left.chars - right.chars

            if not result:
                raise YALexError("Charset vacío después de diferencia (#)")

            return CharSetNode(result)
        return left

    def parse_charset(self) -> CharSetNode:
        self.i += 1
        chars: Set[str] = set()

        while self.i < len(self.text):
            self.i = self.skip_local_ws(self.i)

            if self.i < len(self.text) and self.text[self.i] == "]":
                self.i += 1
                if not chars:
                    raise YALexError("Charset vacío")
                return CharSetNode(chars)

            left_chars = self.read_charset_atom()
            self.i = self.skip_local_ws(self.i)

            # RANGO
            if (
                len(left_chars) == 1 and
                self.i < len(self.text) and
                self.text[self.i] == "-"
            ):
                self.i += 1
                self.i = self.skip_local_ws(self.i)

                right_chars = self.read_charset_atom()

                if len(right_chars) != 1:
                    raise YALexError("Rango inválido en charset")

                start = ord(next(iter(left_chars)))
                end = ord(next(iter(right_chars)))

                if start > end:
                    start, end = end, start

                chars.update(chr(c) for c in range(start, end + 1))
            else:
                chars.update(left_chars)

        raise YALexError("Charset sin cerrar")

    def read_charset_atom(self) -> Set[str]:
        if self.i >= len(self.text):
            raise YALexError("Character-set incompleto.")

        ch = self.text[self.i]
        if ch == "'":
            return {self.read_single_quoted()}
        if ch == '"':
            return set(self.read_double_quoted())
        if ch == "\\" and self.i + 1 < len(self.text):
            raw = self.text[self.i : self.i + 2]
            self.i += 2
            return {decode_escaped(raw)}

        self.i += 1
        return {ch}


# ============================================================
# Parser del archivo YALex
# ============================================================

def extract_braced_block(text: str, start_idx: int) -> Tuple[str, int]:
    if start_idx >= len(text) or text[start_idx] != "{":
        raise YALexError("Se esperaba '{'.")
    depth = 0
    i = start_idx
    content: List[str] = []
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
            if depth > 1:
                content.append(ch)
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return "".join(content), i + 1
            content.append(ch)
        else:
            content.append(ch)
        i += 1
    raise YALexError("Bloque con llaves sin cerrar.")


def parse_rule_cases(rule_body: str) -> List[RuleCase]:
    cases: List[RuleCase] = []
    i = 0
    while i < len(rule_body):
        i = skip_ws(rule_body, i)
        if i >= len(rule_body):
            break
        if rule_body[i] == "|":
            i += 1
            i = skip_ws(rule_body, i)

        regex_start = i
        brace_idx = None
        nesting = 0
        in_sq = False
        in_dq = False
        while i < len(rule_body):
            ch = rule_body[i]
            prev = rule_body[i - 1] if i > 0 else ""
            if ch == "'" and not in_dq and prev != "\\":
                in_sq = not in_sq
            elif ch == '"' and not in_sq and prev != "\\":
                in_dq = not in_dq
            elif not in_sq and not in_dq:
                if ch == "(" :
                    nesting += 1
                elif ch == ")" and nesting > 0:
                    nesting -= 1
                elif ch == "{" and nesting == 0:
                    brace_idx = i
                    break
            i += 1

        if brace_idx is None:
            break

        regex_src = rule_body[regex_start:brace_idx].strip()
        action_src, i = extract_braced_block(rule_body, brace_idx)
        if not regex_src:
            raise YALexError("Regex vacía en regla")

        cases.append(RuleCase(
            regex_src=regex_src,
            action_src=action_src.strip()
        ))

    if not cases:
        raise YALexError("No se encontraron reglas dentro de 'rule'.")
    return cases


def parse_yalex(source: str) -> YALexSpec:
    clean = strip_comments(source)
    spec = YALexSpec(raw_source=source, clean_source=clean)

    i = skip_ws(clean, 0)
    if i < len(clean) and clean[i] == "{":
        spec.header, i = extract_braced_block(clean, i)

    rule_idx = clean.find("rule", i)
    if rule_idx == -1:
        raise YALexError("No se encontró la sección rule.")

    lets_block = clean[i:rule_idx]
    for raw_line in lets_block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not line.startswith("let "):
            raise YALexError(f"Línea inválida antes de rule: {line}")
        body = line[4:].strip()
        if "=" not in body:
            raise YALexError(f"Definición let inválida: {line}")
        ident, expr = body.split("=", 1)
        ident = ident.strip()
        expr = expr.strip()
        if not ident or not expr:
            raise YALexError("Definición let inválida.")
        spec.lets[ident] = expr

    i = rule_idx + 4
    i = skip_ws(clean, i)

    start_rule_name = i
    while i < len(clean) and (clean[i].isalnum() or clean[i] == "_"):
        i += 1
    spec.rule_name = clean[start_rule_name:i]
    i = skip_ws(clean, i)

    if i < len(clean) and clean[i] == "[":
        args_raw, i = extract_square_block(clean, i)
        spec.rule_args = [arg.strip() for arg in args_raw.split() if arg.strip()]
        i = skip_ws(clean, i)

    if i >= len(clean) or clean[i] != "=":
        raise YALexError("La regla principal debe incluir '='.")
    i += 1

    # NO asumir trailer automáticamente
    rule_body = clean[i:].strip()
    spec.trailer = ""

    spec.rule_cases = parse_rule_cases(rule_body)

    definitions_ast: Dict[str, RegexNode] = {}
    for ident, expr in spec.lets.items():
        definitions_ast[ident] = RegexParser(expr, definitions_ast).parse()
    spec.lets_ast = definitions_ast

    for idx, case in enumerate(spec.rule_cases):
        case.ast = RegexParser(case.regex_src, definitions_ast).parse()
        case.priority = idx

    return spec


def extract_square_block(text: str, start_idx: int) -> Tuple[str, int]:
    if text[start_idx] != "[":
        raise YALexError("Se esperaba '['.")
    i = start_idx + 1
    content: List[str] = []
    while i < len(text):
        if text[i] == "]":
            return "".join(content), i + 1
        content.append(text[i])
        i += 1
    raise YALexError("Bloque de argumentos sin cerrar con ']'.")


def find_trailing_brace_block(text: str, start_idx: int) -> Optional[int]:
    i = len(text) - 1
    while i >= start_idx and text[i].isspace():
        i -= 1
    if i < start_idx or text[i] != "}":
        return None

    depth = 0
    while i >= start_idx:
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            depth -= 1
            if depth == 0:
                return i
        i -= 1
    return None

# ============================================================
# Helpers para depuración / UI
# ============================================================

def ast_to_readable(node: RegexNode) -> str:
    if isinstance(node, EmptyNode):
        return "ε"
    if isinstance(node, LiteralNode):
        return repr(node.value)
    if isinstance(node, CharSetNode):
        sample = sorted(node.chars)
        preview = "".join(sample[:10])
        extra = "..." if len(sample) > 10 else ""
        return f"[{preview}{extra}]"
    if isinstance(node, ConcatNode):
        return f"({ast_to_readable(node.left)} · {ast_to_readable(node.right)})"
    if isinstance(node, UnionNode):
        return f"({ast_to_readable(node.left)} | {ast_to_readable(node.right)})"
    if isinstance(node, StarNode):
        return f"({ast_to_readable(node.child)})*"
    if isinstance(node, PlusNode):
        return f"({ast_to_readable(node.child)})+"
    if isinstance(node, OptionalNode):
        return f"({ast_to_readable(node.child)})?"
    return str(node)
