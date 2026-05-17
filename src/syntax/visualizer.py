from __future__ import annotations

from src.syntax.lr0 import LR0Automaton


def escape_label(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("<", "\\<")
        .replace(">", "\\>")
        .replace("|", "\\|")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )


def lr0_to_dot(automaton: LR0Automaton) -> str:
    lines = [
        "digraph LR0 {",
        "  rankdir=LR;",
        "  node [shape=box];",
        "  start [shape=point];",
        f"  start -> I{automaton.start_state};",
    ]

    # Nodos
    for state_id, state in sorted(automaton.states.items()):
        item_lines = [f"I{state_id}"]

        for item in sorted(state.items, key=str):
            item_lines.append(str(item))

        label = escape_label("\\n".join(item_lines))
        lines.append(f'  I{state_id} [label="{label}"];')

    # Aristas
    for state_id, state in sorted(automaton.states.items()):
        for symbol, target_id in sorted(state.transitions.items()):
            label = escape_label(symbol)
            lines.append(f'  I{state_id} -> I{target_id} [label="{label}"];')

    lines.append("}")
    return "\n".join(lines)


def save_lr0_dot(automaton: LR0Automaton, path: str) -> None:
    dot = lr0_to_dot(automaton)

    with open(path, "w", encoding="utf-8") as file:
        file.write(dot)