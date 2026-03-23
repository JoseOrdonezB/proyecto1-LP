from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from src.parser_yalex import (
    CharSetNode,
    ConcatNode,
    EmptyNode,
    LiteralNode,
    OptionalNode,
    PlusNode,
    RegexNode,
    RuleCase,
    StarNode,
    UnionNode,
)

EPSILON = None
EOF_SYMBOL = "<<EOF>>"


@dataclass
class NFAState:
    id: int
    transitions: Dict[Optional[str], Set[int]] = field(default_factory=lambda: defaultdict(set))
    accepting_token: Optional[str] = None
    accepting_action: Optional[str] = None
    priority: Optional[int] = None


@dataclass
class NFA:
    states: Dict[int, NFAState]
    start_state: int
    final_states: Set[int]
    alphabet: Set[str]


@dataclass
class DFAState:
    id: int
    nfa_states: FrozenSet[int]
    transitions: Dict[str, int] = field(default_factory=dict)
    accepting_token: Optional[str] = None
    accepting_action: Optional[str] = None
    priority: Optional[int] = None


@dataclass
class DFA:
    states: Dict[int, DFAState]
    start_state: int
    alphabet: Set[str]


class ThompsonBuilder:
    def __init__(self):
        self.states: Dict[int, NFAState] = {}
        self.counter = 0
        self.alphabet: Set[str] = set()

    def new_state(self) -> int:
        sid = self.counter
        self.states[sid] = NFAState(id=sid)
        self.counter += 1
        return sid

    def add_transition(self, src: int, symbol: Optional[str], dst: int) -> None:
        self.states[src].transitions[symbol].add(dst)
        if symbol is not None and symbol != EPSILON:
            self.alphabet.add(symbol)

    def build_from_ast(self, node: RegexNode) -> Tuple[int, int]:
        if isinstance(node, EmptyNode):
            s = self.new_state()
            f = self.new_state()
            self.add_transition(s, EPSILON, f)
            return s, f

        if isinstance(node, LiteralNode):
            s = self.new_state()
            f = self.new_state()
            self.add_transition(s, node.value, f)
            return s, f

        if isinstance(node, CharSetNode):
            s = self.new_state()
            f = self.new_state()
            for ch in sorted(node.chars):
                self.add_transition(s, ch, f)
            return s, f

        if isinstance(node, ConcatNode):
            s1, f1 = self.build_from_ast(node.left)
            s2, f2 = self.build_from_ast(node.right)
            self.add_transition(f1, EPSILON, s2)
            return s1, f2

        if isinstance(node, UnionNode):
            s = self.new_state()
            f = self.new_state()
            s1, f1 = self.build_from_ast(node.left)
            s2, f2 = self.build_from_ast(node.right)
            self.add_transition(s, EPSILON, s1)
            self.add_transition(s, EPSILON, s2)
            self.add_transition(f1, EPSILON, f)
            self.add_transition(f2, EPSILON, f)
            return s, f

        if isinstance(node, StarNode):
            s = self.new_state()
            f = self.new_state()
            sn, fn = self.build_from_ast(node.child)
            self.add_transition(s, EPSILON, sn)
            self.add_transition(s, EPSILON, f)
            self.add_transition(fn, EPSILON, sn)
            self.add_transition(fn, EPSILON, f)
            return s, f

        if isinstance(node, PlusNode):
            first_start, first_end = self.build_from_ast(node.child)
            star_start, star_end = self.build_from_ast(StarNode(node.child))
            self.add_transition(first_end, EPSILON, star_start)
            return first_start, star_end

        if isinstance(node, OptionalNode):
            return self.build_from_ast(UnionNode(node.child, EmptyNode()))

        raise ValueError(f"Nodo regex no soportado: {type(node).__name__}")


def build_combined_nfa(rule_cases: List[RuleCase]) -> NFA:
    builder = ThompsonBuilder()
    global_start = builder.new_state()
    finals: Set[int] = set()

    for idx, case in enumerate(rule_cases):
        start, end = builder.build_from_ast(case.ast)
        builder.add_transition(global_start, EPSILON, start)
        builder.states[end].accepting_token = infer_token_name(case)
        builder.states[end].accepting_action = case.action_src
        builder.states[end].priority = idx
        finals.add(end)

    return NFA(
        states=builder.states,
        start_state=global_start,
        final_states=finals,
        alphabet=builder.alphabet,
    )


def infer_token_name(case: RuleCase) -> str:
    action = case.action_src.strip().replace("\n", " ")
    if action:
        return action[:60]
    return case.regex_src


def epsilon_closure(nfa: NFA, state_ids: Set[int]) -> Set[int]:
    closure = set(state_ids)
    stack = list(state_ids)
    while stack:
        state_id = stack.pop()
        for nxt in nfa.states[state_id].transitions.get(EPSILON, set()):
            if nxt not in closure:
                closure.add(nxt)
                stack.append(nxt)
    return closure



def move(nfa: NFA, state_ids: Set[int], symbol: str) -> Set[int]:
    reached: Set[int] = set()
    for sid in state_ids:
        reached.update(nfa.states[sid].transitions.get(symbol, set()))
    return reached



def pick_accepting_metadata(nfa: NFA, state_ids: Set[int]) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    candidates = []
    for sid in state_ids:
        state = nfa.states[sid]
        if state.accepting_token is not None:
            candidates.append((state.priority if state.priority is not None else 10**9, sid, state))
    if not candidates:
        return None, None, None
    candidates.sort(key=lambda item: item[0])
    chosen = candidates[0][2]
    return chosen.accepting_token, chosen.accepting_action, chosen.priority



def nfa_to_dfa(nfa: NFA) -> DFA:
    start_closure = frozenset(epsilon_closure(nfa, {nfa.start_state}))
    dfa_states: Dict[int, DFAState] = {}
    state_map: Dict[FrozenSet[int], int] = {start_closure: 0}
    queue = deque([start_closure])

    token, action, priority = pick_accepting_metadata(nfa, set(start_closure))
    dfa_states[0] = DFAState(
        id=0,
        nfa_states=start_closure,
        accepting_token=token,
        accepting_action=action,
        priority=priority,
    )

    while queue:
        current_set = queue.popleft()
        current_id = state_map[current_set]

        for symbol in sorted(sym for sym in nfa.alphabet if sym is not None):
            reached = move(nfa, set(current_set), symbol)
            if not reached:
                continue
            closure = frozenset(epsilon_closure(nfa, reached))
            if closure not in state_map:
                new_id = len(state_map)
                state_map[closure] = new_id
                token, action, priority = pick_accepting_metadata(nfa, set(closure))
                dfa_states[new_id] = DFAState(
                    id=new_id,
                    nfa_states=closure,
                    accepting_token=token,
                    accepting_action=action,
                    priority=priority,
                )
                queue.append(closure)
            dfa_states[current_id].transitions[symbol] = state_map[closure]

    return DFA(states=dfa_states, start_state=0, alphabet=set(nfa.alphabet))



def minimize_dfa(dfa: DFA) -> DFA:
    accepting_groups: Dict[Tuple[Optional[str], Optional[int]], Set[int]] = defaultdict(set)
    non_accepting: Set[int] = set()

    for sid, state in dfa.states.items():
        if state.accepting_token is None:
            non_accepting.add(sid)
        else:
            accepting_groups[(state.accepting_token, state.priority)].add(sid)

    partitions: List[Set[int]] = []
    if non_accepting:
        partitions.append(non_accepting)
    partitions.extend(group for group in accepting_groups.values() if group)

    if not partitions:
        return dfa

    changed = True
    alphabet = sorted(sym for sym in dfa.alphabet if sym is not None)

    while changed:
        changed = False
        new_partitions: List[Set[int]] = []
        for group in partitions:
            signatures: Dict[Tuple, Set[int]] = defaultdict(set)
            for sid in group:
                state = dfa.states[sid]
                signature = []
                for sym in alphabet:
                    target = state.transitions.get(sym)
                    target_partition = find_partition_index(partitions, target)
                    signature.append((sym, target_partition))
                signature.append(("acc", state.accepting_token, state.priority))
                signatures[tuple(signature)].add(sid)

            if len(signatures) == 1:
                new_partitions.append(group)
            else:
                changed = True
                new_partitions.extend(signatures.values())
        partitions = new_partitions

    representative_map: Dict[int, int] = {}
    minimized_states: Dict[int, DFAState] = {}

    for new_id, group in enumerate(partitions):
        rep = min(group)
        rep_state = dfa.states[rep]
        minimized_states[new_id] = DFAState(
            id=new_id,
            nfa_states=rep_state.nfa_states,
            accepting_token=rep_state.accepting_token,
            accepting_action=rep_state.accepting_action,
            priority=rep_state.priority,
        )
        for old_sid in group:
            representative_map[old_sid] = new_id

    for new_id, group in enumerate(partitions):
        rep = min(group)
        rep_state = dfa.states[rep]
        for sym, old_target in rep_state.transitions.items():
            minimized_states[new_id].transitions[sym] = representative_map[old_target]

    return DFA(
        states=minimized_states,
        start_state=representative_map[dfa.start_state],
        alphabet=set(dfa.alphabet),
    )



def find_partition_index(partitions: List[Set[int]], state_id: Optional[int]) -> Optional[int]:
    if state_id is None:
        return None
    for idx, group in enumerate(partitions):
        if state_id in group:
            return idx
    return None



def dfa_transition_table(dfa: DFA) -> List[Dict[str, str]]:
    symbols = sorted(sym for sym in dfa.alphabet if sym is not None)
    rows: List[Dict[str, str]] = []
    for sid in sorted(dfa.states):
        state = dfa.states[sid]
        row: Dict[str, str] = {
            "estado": f"q{sid}",
            "aceptacion": "Sí" if state.accepting_token else "No",
            "token": state.accepting_token or "-",
        }
        for sym in symbols:
            target = state.transitions.get(sym)
            row[repr(sym)] = f"q{target}" if target is not None else "-"
        rows.append(row)
    return rows



def dfa_to_dot(dfa: DFA) -> str:
    lines = [
        "digraph DFA {",
        "  rankdir=LR;",
        '  node [shape=circle];',
        '  start [shape=point];',
        f"  start -> q{dfa.start_state};",
    ]

    for sid, state in sorted(dfa.states.items()):
        if state.accepting_token:
            label = f"q{sid}\\n{escape_label(state.accepting_token)}"
            lines.append(f'  q{sid} [shape=doublecircle, label="{label}"];')
        else:
            lines.append(f'  q{sid} [label="q{sid}"];')

    for sid, state in sorted(dfa.states.items()):
        grouped: Dict[int, List[str]] = defaultdict(list)
        for sym, target in sorted(state.transitions.items(), key=lambda item: (item[1], item[0])):
            grouped[target].append(sym)
        for target, symbols in grouped.items():
            label = ", ".join(escape_label(sym) for sym in symbols[:8])
            if len(symbols) > 8:
                label += ", ..."
            lines.append(f'  q{sid} -> q{target} [label="{label}"];')

    lines.append("}")
    return "\n".join(lines)

def build_dfa_from_single_regex(regex: str):
    from src.regex import preparar_regex
    from src.afd_directo import construir_afd_directo

    regex_preparada, alfabeto = preparar_regex(regex)
    afd = construir_afd_directo(regex_preparada, alfabeto)

    # 🔥 CONVERTIR A FORMATO PROYECTO

    states = {}
    
    for i, estado in enumerate(afd["estados"]):
        states[i] = DFAState(
            id=i,
            nfa_states=frozenset(estado),
            transitions={},
            accepting_token="TOKEN" if estado in afd["aceptacion"] else None,
            accepting_action="TOKEN" if estado in afd["aceptacion"] else None,
            priority=0
        )

    # mapear estados
    estado_id_map = {estado: i for i, estado in enumerate(afd["estados"])}

    # transiciones
    for estado, trans in afd["transiciones"].items():
        sid = estado_id_map[estado]
        for simbolo, destino in trans.items():
            states[sid].transitions[simbolo] = estado_id_map[destino]

    return DFA(
        states=states,
        start_state=estado_id_map[afd["estado_inicial"]],
        alphabet=set(alfabeto)
    )


def escape_label(value: str) -> str:
    if value == "\n":
        return r"\\n"
    if value == "\t":
        return r"\\t"
    return value.replace('"', r'\"')
