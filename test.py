from src.syntax.parser_yapar import parse_yapar

with open("src/data/test.yalp", "r", encoding="utf_8") as file:
    source = file.read()

grammar = parse_yapar(source)

print("Símbolo inicial:", grammar.start_symbol)
print("Terminales:", grammar.terminals)
print("No terminales:", grammar.nonterminals)
print("\nProducciones:")

for production in grammar.productions:
    print(production)