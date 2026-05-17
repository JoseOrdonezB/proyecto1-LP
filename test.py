from src.syntax.parser_yapar import parse_yapar
from src.syntax.lr0 import build_lr0_automaton, print_lr0_automaton, build_parsing_table, print_parsing_table
from src.syntax.visualizer import save_lr0_dot

with open("src/data/test.yalp", "r", encoding="utf_8") as file:
    source = file.read()

grammar = parse_yapar(source)
automaton = build_lr0_automaton(grammar)
table = build_parsing_table(automaton)

print_lr0_automaton(automaton)
print_parsing_table(table)

save_lr0_dot(automaton, "automaton.dot")