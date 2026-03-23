OPERADORES = {'|', '*', '+', '?', '(', ')', '.'}

def es_simbolo(c):
    return c not in OPERADORES

def limpiar_regex(regex):
    return regex.replace(" ", "")

def obtener_operando(resultado):
    if resultado[-1] == ')':
        contador = 0
        for i in range(len(resultado) - 1, -1, -1):

            if resultado[i] == ')':
                contador += 1

            elif resultado[i] == '(':
                contador -= 1

            if contador == 0:
                return resultado[i:], resultado[:i]

    else:
        return resultado[-1], resultado[:-1]

def expandir_operadores(regex):
    resultado = ""
    i = 0

    while i < len(regex):

        c = regex[i]

        if c == '+':
            operando, resto = obtener_operando(resultado)

            resultado = resto + f"{operando}.{operando}*"

        elif c == '?':
            operando, resto = obtener_operando(resultado)

            resultado = resto + f"({operando}|ε)"

        else:
            resultado += c

        i += 1

    return resultado

def insertar_concatenacion(regex):
    resultado = ""

    for i in range(len(regex)):
        c1 = regex[i]
        resultado += c1

        if i + 1 < len(regex):
            c2 = regex[i + 1]

            if (
                (es_simbolo(c1) and es_simbolo(c2)) or
                (es_simbolo(c1) and c2 == '(') or
                (c1 == ')' and es_simbolo(c2)) or
                (c1 == ')' and c2 == '(') or
                (c1 in {'*'} and es_simbolo(c2)) or
                (c1 in {'*'} and c2 == '(')
            ):
                resultado += '.'

    return resultado

def obtener_alfabeto(regex):
    alfabeto = set()

    for c in regex:
        if es_simbolo(c) and c not in {'ε', '#'}:
            alfabeto.add(c)

    return sorted(alfabeto)

def preparar_regex(regex):
    regex = limpiar_regex(regex)

    regex = expandir_operadores(regex)

    regex = insertar_concatenacion(regex)

    regex = f"({regex}).#"

    alfabeto = obtener_alfabeto(regex)

    return regex, alfabeto