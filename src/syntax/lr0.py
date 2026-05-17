from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Set, Tuple

from src.syntax.parser_yapar import Grammar, Production


@dataclass(frozen=True)
class LR0Item:
    production: Production
    dot: int = 0

    def symbol_after_dot(self) -> str | None:
        if self.dot < len(self.production.right):
            return self.production.right[self.dot]
        return None

    def advance_dot(self) -> "LR0Item":
        return LR0Item(self.production, self.dot + 1)

    def is_complete(self) -> bool:
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
        transitions=transitions
    )


def print_lr0_automaton(automaton: LR0Automaton) -> None:
    for state_id in sorted(automaton.states):
        print(automaton.states[state_id])
        print()