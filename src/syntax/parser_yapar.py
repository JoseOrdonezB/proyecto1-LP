from __future__ import annotations

from dataclasses import dataclass, field
from shutil import ignore_patterns
from typing import Dict, List, Set, Tuple


class YAParError(Exception):
    pass


@dataclass(frozen=True)
class Production:
    left: str
    right: Tuple[str, ...]

    def __str__(self) -> str:
        return f"{self.left} -> {' '.join(self.right)}"


@dataclass
class Grammar:
    start_symbol: str
    terminals: Set[str]
    nonterminals: Set[str]
    productions: List[Production]
    ignored_tokens: Set[str] = field(default_factory=set)
    productions_by_left: Dict[str, List[Production]] = field(default_factory=dict)

    def __post_init__(self):
        self.productions_by_left = {}

        for production in self.productions:
            self.productions_by_left.setdefault(production.left, []).append(production)

    def get_productions(self, nonterminal: str) -> List[Production]:
        return self.productions_by_left.get(nonterminal, [])

    def augmented(self) -> "Grammar":
        new_start = self.start_symbol + "'"
        augmented_production = Production(new_start, (self.start_symbol,))

        return Grammar(
            start_symbol=new_start,
            terminals=self.terminals,
            nonterminals=self.nonterminals | {new_start},
            productions=[augmented_production] + self.productions
        )


def remove_comments(source: str) -> str:
    lines = []

    for line in source.splitlines():
        if "/*" in line:
            line = line.split("/*", 1)[0]

        if "//" in line:
            line = line.split("//", 1)[0]

        lines.append(line)

    return "\n".join(lines)


def parse_yapar(source: str) -> Grammar:
    clean_source = remove_comments(source)

    terminals: Set[str] = set()
    productions: List[Production] = []

    sections = clean_source.split("%%")

    if len(sections) < 2:
        raise YAParError("El archivo YAPar debe contener '%%' antes de las producciones.")

    declarations = sections[0]
    grammar_rules = sections[1]

    terminals, ignored_tokens = parse_tokens(declarations)
    productions = parse_productions(grammar_rules)

    if not productions:
        raise YAParError("No se encontraron producciones en el archivo YAPar.")

    start_symbol = productions[0].left
    nonterminals = {production.left for production in productions}

    return Grammar(
        start_symbol=start_symbol,
        terminals=terminals,
        nonterminals=nonterminals,
        productions=productions
    )


def parse_tokens(declarations: str) -> Set[str]:
    tokens: Set[str] = set()
    ignored_tokens: Set[str] = set()

    for line in declarations.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith("%token"):
            parts = line.split()
            tokens.update(parts[1:])

        elif line.startswith("IGNORE"):
            part = line.split()
            ignored_tokens.update(parts[1:])

    return tokens, ignored_tokens


def parse_productions(grammar_rules: str) -> List[Production]:
    productions: List[Production] = []

    current_left = None
    current_right_parts: List[str] = []

    for raw_line in grammar_rules.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if ":" in line:
            left, right = line.split(":", 1)
            current_left = left.strip()
            current_right_parts = [right.strip()]

            if ";" in right:
                block = " ".join(current_right_parts)
                productions.extend(parse_production_block(current_left, block))
                current_left = None
                current_right_parts = []

        elif current_left is not None:
            current_right_parts.append(line)

            if ";" in line:
                block = " ".join(current_right_parts)
                productions.extend(parse_production_block(current_left, block))
                current_left = None
                current_right_parts = []

    if current_left is not None:
        raise YAParError(f"Producción sin cerrar con ';' para: {current_left}")

    return productions


def parse_production_block(left: str, block: str) -> List[Production]:
    productions: List[Production] = []

    block = block.replace(";", "")
    alternatives = block.split("|")

    for alternative in alternatives:
        symbols = alternative.strip().split()

        if not symbols:
            symbols = ("ε",)
        else:
            symbols = tuple(symbols)

        productions.append(Production(left, symbols))

    return productions