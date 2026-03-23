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

    code = f"""
class Lexer:

    def __init__(self, text):
        self.text = text
        self.pos = 0

    TRANSITIONS = {transitions}

    ACCEPTING = {accepting}

    START_STATE = {dfa.start_state}

    def next_token(self):

        if self.pos >= len(self.text):
            return None

        state = self.START_STATE
        start = self.pos
        last_accept = None
        last_pos = self.pos

        while self.pos < len(self.text):

            char = self.text[self.pos]

            if char not in self.TRANSITIONS[state]:
                break

            state = self.TRANSITIONS[state][char]
            self.pos += 1

            if state in self.ACCEPTING:
                last_accept = state
                last_pos = self.pos

        if last_accept is None:
            raise Exception(f"Error léxico en posición {{self.pos}}")

        lexeme = self.text[start:last_pos]
        self.pos = last_pos

        token_info = self.ACCEPTING[last_accept]

        token = token_info["token"]
        if token:
            token = token.strip("{{}} ").strip()

        if token == "WHITESPACE" or token == "EOL":
            return self.next_token()

        return token, lexeme
"""

    return code