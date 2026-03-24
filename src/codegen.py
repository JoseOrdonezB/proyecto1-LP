def generate_lexer_code(dfa):
    transitions = {}
    accepting = {}

    for sid, state in dfa.states.items():
        transitions[sid] = state.transitions
        if state.accepting_token:
            accepting[sid] = {
                "token": state.accepting_token,
                "action": state.accepting_action
            }

    code = f'''class Lexer:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.length = len(text)

    TRANSITIONS = {transitions}
    ACCEPTING = {accepting}
    START_STATE = {dfa.start_state}

    def next_token(self):
        while True:
            if self.pos >= self.length:
                return None

            state = self.START_STATE
            start = self.pos
            last_accept = None
            last_pos = self.pos

            while self.pos < self.length:
                char = self.text[self.pos]

                # --- Manejo de strings ---
                if char == '"':
                    start_str = self.pos
                    self.pos += 1
                    while self.pos < self.length:
                        c = self.text[self.pos]
                        if c == '"' and self.text[self.pos-1] != '\\\\':
                            self.pos += 1
                            lexeme = self.text[start_str:self.pos]
                            return "STRING", lexeme
                        self.pos += 1
                    line = self.text[:start_str].count("\\n") + 1
                    raise Exception(f"Error léxico: cadena no cerrada en línea {{line}}, posición {{start_str}}")

                # --- DFA normal ---
                state_trans = self.TRANSITIONS.get(state, {{}})
                if char in state_trans:
                    state = state_trans[char]
                    self.pos += 1
                    if state in self.ACCEPTING:
                        last_accept = state
                        last_pos = self.pos
                else:
                    break

            if last_accept is None:
                line = self.text[:self.pos].count("\\n") + 1
                error_char = self.text[self.pos] if self.pos < self.length else "EOF"
                raise Exception(f"Error léxico en línea {{line}}, posición {{self.pos}}: '{{error_char}}'")

            lexeme = self.text[start:last_pos]
            self.pos = last_pos

            token_info = self.ACCEPTING[last_accept]
            token = token_info["token"]
            if token:
                token = token.replace("return", "").replace(";", "").strip()
                token = token.strip("{{}} ").strip()

            if token in ["WHITESPACE", "EOL"]:
                continue

            return token, lexeme

    def tokenize(self):
        tokens = []
        while True:
            tok = self.next_token()
            if tok is None:
                break
            tokens.append(tok)
        return tokens
'''
    return code