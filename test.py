from src.syntax.parser_yapar import parse_yapar
from src.syntax.lr0 import build_lr0_automaton, print_lr0_automaton

with open("src/data/test.yalp", "r", encoding="utf_8") as file:
    source = file.read()

grammar = parse_yapar(source)
automaton = build_lr0_automaton(grammar)

print_lr0_automaton(automaton)