from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Set, Tuple, List

from src.syntax.parser_yapar import Grammar, Production


EOF_SYMBOL = "$"
EPSILON_SYMBOL = "ε"

@dataclass(frozen=True)
class LR0Item:
    production: Production
    dot: int = 0

    def symbol_after_dot(self) -> str | None:
        if self.production.right == (EPSILON_SYMBOL,):
            return None
        if self.dot < len(self.production.right):
            return self.production.right[self.dot]
        return None

    def advance_dot(self) -> "LR0Item":
        return LR0Item(self.production, self.dot + 1)

    def is_complete(self) -> bool:
        if self.production.right == (EPSILON_SYMBOL,):
            return True
        return self.dot >= len(self.production.right)

    def __str__(self) -> str:
        right = list(self.production.right)
        right.insert(self.dot, "·")
        return f"{self.production.left} -> {' '.join(right)}"


@dataclass
class LR0State:
    id: int
    items: FrozenSet[LR0Item]
    transitions: Dict[str, int] = field(default_factory=dict)

    def __str__(self) -> str:
        lines = [f"I{self.id}:"]

        for item in sorted(self.items, key=str):
            lines.append(f"  {item}")

        if self.transitions:
            lines.append("  Transiciones:")
            for symbol, target in sorted(self.transitions.items()):
                lines.append(f"    {symbol} -> I{target}")

        return "\n".join(lines)

@dataclass
class LR0Automaton:
    states: Dict[int, LR0State]
    start_state: int
    transitions: Dict[Tuple[int, str], int]
    grammar: Grammar

@dataclass
class ParsingTable:
    action: Dict[Tuple[int, str], str]
    goto: Dict[Tuple[int, str], int]
    conflicts: List[str] = field(default_factory=list)

def closure(items: Set[LR0Item], grammar: Grammar) -> FrozenSet[LR0Item]:
    result = set(items)
    changed = True

    while changed:
        changed = False
        new_items: Set[LR0Item] = set()

        for item in result:
            symbol = item.symbol_after_dot()

            if symbol in grammar.nonterminals:
                for production in grammar.get_productions(symbol):
                    new_item = LR0Item(production, 0)

                    if new_item not in result:
                        new_items.add(new_item)

        if new_items:
            result.update(new_items)
            changed = True

    return frozenset(result)

def goto(items: FrozenSet[LR0Item], symbol: str, grammar: Grammar) -> FrozenSet[LR0Item]:
    moved_items: Set[LR0Item] = set()

    for item in items:
        if item.symbol_after_dot() == symbol:
            moved_items.add(item.advance_dot())

    if not moved_items:
        return frozenset()

    return closure(moved_items, grammar)

def build_lr0_automaton(grammar: Grammar) -> LR0Automaton:
    augmented_grammar = grammar.augmented()

    start_production = augmented_grammar.productions[0]
    start_item = LR0Item(start_production, 0)
    start_items = closure({start_item}, augmented_grammar)

    states: Dict[int, LR0State] = {
        0: LR0State(id=0, items=start_items)
    }

    state_map: Dict[FrozenSet[LR0Item], int] = {
        start_items: 0
    }

    transitions: Dict[Tuple[int, str], int] = {}
    queue = deque([start_items])

    symbols = sorted(augmented_grammar.terminals | augmented_grammar.nonterminals)

    while queue:
        current_items = queue.popleft()
        current_id = state_map[current_items]

        for symbol in symbols:
            next_items = goto(current_items, symbol, augmented_grammar)

            if not next_items:
                continue

            if next_items not in state_map:
                new_id = len(state_map)
                state_map[next_items] = new_id
                states[new_id] = LR0State(id=new_id, items=next_items)
                queue.append(next_items)

            target_id = state_map[next_items]
            states[current_id].transitions[symbol] = target_id
            transitions[(current_id, symbol)] = target_id

    return LR0Automaton(
        states=states,
        start_state=0,
        transitions=transitions,
        grammar=augmented_grammar
    )

def set_action(
    table: ParsingTable,
    state_id: int,
    terminal: str,
    value: str
) -> None:
    key = (state_id, terminal)

    if key in table.action and table.action[key] != value:
        current = table.action[key]
        if terminal == "ELSE":
            if current.startswith("s") and value.startswith("r("):
                return
            if current.startswith("r(") and value.startswith("s"):
                table.action[key] = value
                return

        table.conflicts.append(
            f"Conflicto ACTION[{state_id}, {terminal}]: "
            f"{table.action[key]} vs {value}"
        )
        return

    table.action[key] = value

def first_sets(grammar: Grammar) -> Dict[str, Set[str]]:
    first: Dict[str, Set[str]] = {}

    for terminal in grammar.terminals:
        first[terminal] = {terminal}

    first[EOF_SYMBOL] = {EOF_SYMBOL}
    first[EPSILON_SYMBOL] = {EPSILON_SYMBOL}

    for nonterminal in grammar.nonterminals:
        first.setdefault(nonterminal, set())

    changed = True
    while changed:
        changed = False

        for production in grammar.productions:
            before = len(first[production.left])
            first[production.left].update(first_of_sequence(production.right, first))
            if len(first[production.left]) != before:
                changed = True

    return first


def first_of_sequence(
    symbols: Tuple[str, ...],
    first: Dict[str, Set[str]]
) -> Set[str]:
    if not symbols or symbols == (EPSILON_SYMBOL,):
        return {EPSILON_SYMBOL}

    result: Set[str] = set()

    for symbol in symbols:
        symbol_first = first.get(symbol, {symbol})
        result.update(symbol_first - {EPSILON_SYMBOL})

        if EPSILON_SYMBOL not in symbol_first:
            break
    else:
        result.add(EPSILON_SYMBOL)

    return result


def follow_sets(grammar: Grammar) -> Dict[str, Set[str]]:
    first = first_sets(grammar)
    follow: Dict[str, Set[str]] = {
        nonterminal: set()
        for nonterminal in grammar.nonterminals
    }
    follow[grammar.start_symbol].add(EOF_SYMBOL)

    changed = True
    while changed:
        changed = False

        for production in grammar.productions:
            rhs = production.right

            for index, symbol in enumerate(rhs):
                if symbol not in grammar.nonterminals:
                    continue

                beta = rhs[index + 1:]
                beta_first = first_of_sequence(beta, first)

                before = len(follow[symbol])
                follow[symbol].update(beta_first - {EPSILON_SYMBOL})

                if EPSILON_SYMBOL in beta_first:
                    follow[symbol].update(follow[production.left])

                if len(follow[symbol]) != before:
                    changed = True

    return follow

def build_parsing_table(automaton: LR0Automaton) -> ParsingTable:
    grammar = automaton.grammar
    follow = follow_sets(grammar)

    table = ParsingTable(
        action={},
        goto={},
        conflicts=[]
    )

    terminals = set(grammar.terminals)
    terminals.add(EOF_SYMBOL)

    for state_id, state in automaton.states.items():

        for symbol, target_state in state.transitions.items():
            if symbol in grammar.terminals:
                set_action(table, state_id, symbol, f"s{target_state}")

            elif symbol in grammar.nonterminals:
                table.goto[(state_id, symbol)] = target_state

        for item in state.items:
            if not item.is_complete():
                continue

            production = item.production

            if production.left == grammar.start_symbol:
                set_action(table, state_id, EOF_SYMBOL, "acc")
            else:
                reduce_value = f"r({production.left} -> {' '.join(production.right)})"

                for terminal in follow.get(production.left, terminals):
                    set_action(table, state_id, terminal, reduce_value)

    return table

def print_lr0_automaton(automaton: LR0Automaton) -> None:
    for state_id in sorted(automaton.states):
        print(automaton.states[state_id])
        print()

def print_parsing_table(table: ParsingTable) -> None:
    print("ACTION:")
    for (state, terminal), action in sorted(table.action.items()):
        print(f"  ACTION[{state}, {terminal}] = {action}")

    print("\nGOTO:")
    for (state, nonterminal), target in sorted(table.goto.items()):
        print(f"  GOTO[{state}, {nonterminal}] = {target}")

    if table.conflicts:
        print("\nCONFLICTOS:")
        for conflict in table.conflicts:
            print(f"  {conflict}")
